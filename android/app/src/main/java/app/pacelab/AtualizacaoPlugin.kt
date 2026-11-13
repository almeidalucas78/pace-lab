package app.pacelab

import android.app.PendingIntent
import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.content.IntentFilter
import android.content.pm.PackageInstaller
import android.net.Uri
import android.provider.Settings
import androidx.core.content.ContextCompat
import androidx.core.content.IntentCompat
import com.getcapacitor.JSObject
import com.getcapacitor.Plugin
import com.getcapacitor.PluginCall
import com.getcapacitor.PluginMethod
import com.getcapacitor.annotation.CapacitorPlugin
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.cancel
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import java.io.File
import java.net.HttpURLConnection
import java.net.URL
import java.security.MessageDigest

/**
 * Atualiza o app sem cabo (fase 7, etapa 4b): baixa o APK publicado no PC (`treino publicar-app`,
 * rota /api/app/apk) e entrega ao instalador do Android por uma sessão do PackageInstaller.
 * O Android sempre pede a confirmação do usuário; a primeira vez também pede a permissão
 * "instalar apps desconhecidos" para o Pace Lab.
 */
@CapacitorPlugin(name = "Atualizacao")
class AtualizacaoPlugin : Plugin() {
    private val escopo = CoroutineScope(SupervisorJob() + Dispatchers.Main)

    private val receptor = object : BroadcastReceiver() {
        override fun onReceive(context: Context, intent: Intent) {
            val status = intent.getIntExtra(PackageInstaller.EXTRA_STATUS, PackageInstaller.STATUS_FAILURE)
            when (status) {
                PackageInstaller.STATUS_PENDING_USER_ACTION -> {
                    val confirmar = IntentCompat.getParcelableExtra(intent, Intent.EXTRA_INTENT, Intent::class.java)
                    if (confirmar != null) {
                        confirmar.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
                        context.startActivity(confirmar)
                    }
                    avisar("confirmar", null)
                }
                PackageInstaller.STATUS_SUCCESS -> avisar("instalado", null)
                else -> avisar("falhou", intent.getStringExtra(PackageInstaller.EXTRA_STATUS_MESSAGE) ?: "status $status")
            }
        }
    }

    override fun load() {
        ContextCompat.registerReceiver(context, receptor, IntentFilter(ACAO), ContextCompat.RECEIVER_NOT_EXPORTED)
    }

    override fun handleOnDestroy() {
        runCatching { context.unregisterReceiver(receptor) }
        escopo.cancel()
    }

    private fun avisar(status: String, mensagem: String?) {
        val ev = JSObject()
        ev.put("status", status)
        if (mensagem != null) ev.put("mensagem", mensagem)
        notifyListeners("instalacao", ev)
    }

    @PluginMethod
    fun podeInstalar(call: PluginCall) {
        val r = JSObject()
        r.put("permitido", context.packageManager.canRequestPackageInstalls())
        call.resolve(r)
    }

    /** Abre a tela do Android "instalar apps desconhecidos" já no Pace Lab. */
    @PluginMethod
    fun abrirPermissao(call: PluginCall) {
        val intent = Intent(Settings.ACTION_MANAGE_UNKNOWN_APP_SOURCES, Uri.parse("package:${context.packageName}"))
        activity.startActivity(intent)
        call.resolve()
    }

    /** Baixa o APK (url, token, sha256) e inicia a instalação. Resolve quando o instalador foi chamado. */
    @PluginMethod
    fun instalar(call: PluginCall) {
        val url = call.getString("url") ?: return call.reject("url obrigatória")
        val token = call.getString("token") ?: ""
        val sha256 = call.getString("sha256")
        escopo.launch {
            try {
                val apk = withContext(Dispatchers.IO) { baixar(url, token) }
                if (sha256 != null && withContext(Dispatchers.IO) { hash(apk) } != sha256.lowercase()) {
                    apk.delete()
                    return@launch call.reject("download incompleto ou corrompido; tente de novo", "HASH")
                }
                withContext(Dispatchers.IO) { entregarAoInstalador(apk) }
                call.resolve()
            } catch (e: Exception) {
                call.reject(e.message ?: e.toString(), "ERRO", e)
            }
        }
    }

    private fun baixar(url: String, token: String): File {
        val conexao = URL(url).openConnection() as HttpURLConnection
        conexao.setRequestProperty("Authorization", "Bearer $token")
        conexao.connectTimeout = 15_000
        conexao.readTimeout = 60_000
        try {
            if (conexao.responseCode != 200) throw IllegalStateException("o PC respondeu ${conexao.responseCode}")
            val total = conexao.contentLengthLong
            val destino = File(context.cacheDir, "atualizacao.apk")
            conexao.inputStream.use { entrada ->
                destino.outputStream().use { saida ->
                    val buf = ByteArray(64 * 1024)
                    var lidos = 0L
                    var ultimoPct = -1
                    while (true) {
                        val n = entrada.read(buf)
                        if (n < 0) break
                        saida.write(buf, 0, n)
                        lidos += n
                        if (total > 0) {
                            val pct = (100 * lidos / total).toInt()
                            if (pct != ultimoPct && pct % 5 == 0) {
                                ultimoPct = pct
                                val ev = JSObject()
                                ev.put("pct", pct)
                                notifyListeners("progresso", ev)
                            }
                        }
                    }
                }
            }
            return destino
        } finally {
            conexao.disconnect()
        }
    }

    private fun hash(f: File): String {
        val md = MessageDigest.getInstance("SHA-256")
        f.inputStream().use { entrada ->
            val buf = ByteArray(64 * 1024)
            while (true) {
                val n = entrada.read(buf)
                if (n < 0) break
                md.update(buf, 0, n)
            }
        }
        return md.digest().joinToString("") { "%02x".format(it) }
    }

    /** Sessão do PackageInstaller, como no exemplo InstallApkSessionApi do AOSP. */
    private fun entregarAoInstalador(apk: File) {
        val instalador = context.packageManager.packageInstaller
        val params = PackageInstaller.SessionParams(PackageInstaller.SessionParams.MODE_FULL_INSTALL)
        params.setAppPackageName(context.packageName)
        val id = instalador.createSession(params)
        instalador.openSession(id).use { sessao ->
            apk.inputStream().use { entrada ->
                sessao.openWrite("pace-lab.apk", 0, apk.length()).use { saida ->
                    entrada.copyTo(saida, 64 * 1024)
                    sessao.fsync(saida)
                }
            }
            // PendingIntent mutável: o Android anexa o status e a tela de confirmação (necessário a partir do Android 12)
            val retorno = Intent(ACAO).setPackage(context.packageName)
            val pi = PendingIntent.getBroadcast(context, id, retorno,
                PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_MUTABLE)
            sessao.commit(pi.intentSender)
        }
        apk.delete()
    }

    companion object {
        private const val ACAO = "app.pacelab.ATUALIZACAO_INSTALADA"
    }
}
