package app.pacelab

import android.content.Context
import android.security.keystore.KeyGenParameterSpec
import android.security.keystore.KeyProperties
import android.util.Base64
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
import java.security.KeyStore
import javax.crypto.Cipher
import javax.crypto.KeyGenerator
import javax.crypto.SecretKey
import javax.crypto.spec.GCMParameterSpec

/**
 * Cofre dos tokens de login (fase 9, etapa 8; ADR 0015): texto cifrado com AES-GCM por uma chave que fica no
 * Android Keystore e nunca sai dele. Só o texto cifrado vai para as preferências do app.
 * Se a chave sumir (backup restaurado em outro aparelho, por exemplo), a leitura devolve vazio e o app pede login.
 */
@CapacitorPlugin(name = "Cofre")
class CofrePlugin : Plugin() {
    private val escopo = CoroutineScope(SupervisorJob() + Dispatchers.Main)

    override fun handleOnDestroy() {
        escopo.cancel()
    }

    private val preferencias by lazy { context.getSharedPreferences(ARQUIVO, Context.MODE_PRIVATE) }

    private fun chave(): SecretKey {
        val ks = KeyStore.getInstance(PROVEDOR).apply { load(null) }
        (ks.getKey(APELIDO, null) as? SecretKey)?.let { return it }
        val gerador = KeyGenerator.getInstance(KeyProperties.KEY_ALGORITHM_AES, PROVEDOR)
        gerador.init(
            KeyGenParameterSpec.Builder(APELIDO, KeyProperties.PURPOSE_ENCRYPT or KeyProperties.PURPOSE_DECRYPT)
                .setBlockModes(KeyProperties.BLOCK_MODE_GCM)
                .setEncryptionPaddings(KeyProperties.ENCRYPTION_PADDING_NONE)
                .setKeySize(256)
                .build()
        )
        return gerador.generateKey()
    }

    private fun cifrar(texto: String): String {
        val c = Cipher.getInstance(TRANSFORMACAO)
        c.init(Cipher.ENCRYPT_MODE, chave()) // o Keystore escolhe um IV novo a cada vez
        val cifrado = c.doFinal(texto.toByteArray(Charsets.UTF_8))
        return Base64.encodeToString(c.iv, Base64.NO_WRAP) + ":" + Base64.encodeToString(cifrado, Base64.NO_WRAP)
    }

    private fun decifrar(guardado: String): String? = runCatching {
        val (iv, cifrado) = guardado.split(":", limit = 2).map { Base64.decode(it, Base64.NO_WRAP) }
        val c = Cipher.getInstance(TRANSFORMACAO)
        c.init(Cipher.DECRYPT_MODE, chave(), GCMParameterSpec(128, iv))
        String(c.doFinal(cifrado), Charsets.UTF_8)
    }.getOrNull()

    private fun nome(call: PluginCall): String? = call.getString("chave")?.takeIf { it.matches(Regex("^[a-z0-9.-]{1,40}$")) }

    /** Operações do Keystore podem demorar: rodam fora da thread principal (docs do Android Keystore). */
    private fun emSegundoPlano(call: PluginCall, bloco: () -> JSObject?) {
        escopo.launch {
            try {
                val r = withContext(Dispatchers.IO) { bloco() }
                if (r == null) call.resolve() else call.resolve(r)
            } catch (e: Exception) {
                call.reject(e.message ?: "erro no cofre")
            }
        }
    }

    @PluginMethod
    fun ler(call: PluginCall) {
        val n = nome(call) ?: return call.reject("chave inválida")
        emSegundoPlano(call) {
            val guardado = preferencias.getString(n, null)
            val valor = guardado?.let { decifrar(it) }
            if (guardado != null && valor == null) preferencias.edit().remove(n).apply()
            JSObject().put("valor", valor)
        }
    }

    @PluginMethod
    fun gravar(call: PluginCall) {
        val n = nome(call) ?: return call.reject("chave inválida")
        val valor = call.getString("valor") ?: return call.reject("valor obrigatório")
        emSegundoPlano(call) {
            preferencias.edit().putString(n, cifrar(valor)).commit()
            null
        }
    }

    @PluginMethod
    fun apagar(call: PluginCall) {
        val n = nome(call) ?: return call.reject("chave inválida")
        emSegundoPlano(call) {
            preferencias.edit().remove(n).commit()
            null
        }
    }

    companion object {
        private const val PROVEDOR = "AndroidKeyStore"
        private const val APELIDO = "pacelab-cofre"
        private const val ARQUIVO = "pacelab-cofre"
        private const val TRANSFORMACAO = "AES/GCM/NoPadding"
    }
}
