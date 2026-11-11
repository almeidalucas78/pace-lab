package app.pacelab

import com.getcapacitor.JSArray
import com.getcapacitor.JSObject
import com.getcapacitor.Plugin
import com.getcapacitor.PluginCall
import com.getcapacitor.PluginMethod
import com.getcapacitor.annotation.CapacitorPlugin
import com.samsung.android.sdk.health.data.HealthDataService
import com.samsung.android.sdk.health.data.HealthDataStore
import com.samsung.android.sdk.health.data.data.HealthDataPoint
import com.samsung.android.sdk.health.data.data.entries.ExerciseSession
import com.samsung.android.sdk.health.data.error.HealthDataException
import com.samsung.android.sdk.health.data.error.ResolvablePlatformException
import com.samsung.android.sdk.health.data.permission.AccessType
import com.samsung.android.sdk.health.data.permission.Permission
import com.samsung.android.sdk.health.data.request.DataType
import com.samsung.android.sdk.health.data.request.DataTypes
import com.samsung.android.sdk.health.data.request.InstantTimeFilter
import com.samsung.android.sdk.health.data.request.Ordering
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.cancel
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import java.time.Instant

/**
 * Lê os treinos do Samsung Health pelo Samsung Health Data SDK (modo desenvolvedor, ADR 0013).
 * Devolve no formato que a API recebe em POST /api/saude/treinos (treino/ingest/treinos_app.py):
 * resumo, registros (FC, velocidade, cadência, potência) e percurso (GPS), horários em ms.
 */
@CapacitorPlugin(name = "SamsungHealth")
class SamsungHealthPlugin : Plugin() {
    private val escopo = CoroutineScope(SupervisorJob() + Dispatchers.Main)

    // o percurso tem tipo de dado próprio e permissão separada
    private val pedidas = setOf(
        Permission.of(DataTypes.EXERCISE, AccessType.READ),
        Permission.of(DataTypes.EXERCISE_LOCATION, AccessType.READ),
    )

    private fun loja(): HealthDataStore = HealthDataService.getStore(context)

    override fun handleOnDestroy() {
        escopo.cancel()
    }

    /** Roda o bloco e devolve o resultado ou o erro do SDK com código, para o JavaScript decidir a mensagem. */
    private fun executar(call: PluginCall, bloco: suspend () -> JSObject) {
        escopo.launch {
            try {
                call.resolve(bloco())
            } catch (e: ResolvablePlatformException) {
                // ex.: Samsung Health desatualizado; o SDK abre a tela para corrigir
                if (e.hasResolution) activity?.let { e.resolve(it) }
                call.reject(e.errorMessage ?: e.message ?: "Samsung Health indisponível", "RESOLVIVEL_${e.errorCode}")
            } catch (e: HealthDataException) {
                call.reject(e.errorMessage ?: e.message ?: "erro do Samsung Health", "SAMSUNG_${e.errorCode}")
            } catch (e: Exception) {
                call.reject(e.message ?: e.toString(), "ERRO")
            }
        }
    }

    private fun situacao(dadas: Set<Permission>) = JSObject().apply {
        put("exercicios", dadas.any { it.dataType == DataTypes.EXERCISE })
        put("percurso", dadas.any { it.dataType == DataTypes.EXERCISE_LOCATION })
    }

    @PluginMethod
    fun permissoes(call: PluginCall) = executar(call) {
        situacao(loja().getGrantedPermissions(pedidas))
    }

    @PluginMethod
    fun pedirPermissoes(call: PluginCall) = executar(call) {
        situacao(loja().requestPermissions(pedidas, activity))
    }

    /** Treinos que começam entre `desde` e `ate` (ms desde 1970), do mais antigo para o mais novo. */
    @PluginMethod
    fun lerTreinos(call: PluginCall) {
        val desde = call.getLong("desde")
        val ate = call.getLong("ate")
        if (desde == null || ate == null) {
            call.reject("informe desde e ate em milissegundos", "PARAMETROS")
            return
        }
        executar(call) {
            val treinos = withContext(Dispatchers.IO) { ler(Instant.ofEpochMilli(desde), Instant.ofEpochMilli(ate)) }
            JSObject().put("treinos", treinos)
        }
    }

    private suspend fun ler(desde: Instant, ate: Instant): JSArray {
        val saida = JSArray()
        var pagina: String? = null
        do {
            val construtor = DataTypes.EXERCISE.readDataRequestBuilder
                .setInstantTimeFilter(InstantTimeFilter.of(desde, ate))
                .setOrdering(Ordering.ASC)
                .setPageSize(10)
            pagina?.let { construtor.setPageToken(it) }
            val resposta = loja().readData(construtor.build())
            for (ponto in resposta.dataList) {
                val sessoes = ponto.getValue(DataType.ExerciseType.SESSIONS) ?: continue
                sessoes.forEachIndexed { i, sessao ->
                    // um registro pode ter várias sessões; o id fica estável para a API não duplicar
                    saida.put(treino(ponto, sessao, if (sessoes.size > 1) "${ponto.uid}-$i" else ponto.uid))
                }
            }
            pagina = resposta.pageToken
        } while (!pagina.isNullOrEmpty())
        return saida
    }

    private fun JSObject.numero(chave: String, valor: Number?) {
        val v = valor?.toDouble()
        if (v != null && !v.isNaN() && !v.isInfinite()) put(chave, v)
    }

    private fun treino(ponto: HealthDataPoint, s: ExerciseSession, id: String): JSObject {
        val t = JSObject()
        t.put("id", id)
        t.put("tipo", s.exerciseType.name)
        t.put("inicio", s.startTime.toString())   // ISO 8601 em UTC, com "Z"
        t.put("fim", s.endTime.toString())
        t.numero("duracao_s", s.duration.toMillis() / 1000.0)
        t.numero("distancia_m", s.distance)
        t.numero("calorias", s.calories)
        t.numero("fc_media", s.meanHeartRate)
        t.numero("fc_max", s.maxHeartRate)
        t.numero("cadencia_media", s.meanCadence)
        t.numero("ganho_elevacao_m", s.altitudeGain)
        t.numero("vo2max", s.vo2Max)
        s.customTitle?.let { t.put("titulo", it) }
        ponto.updateTime?.let { t.put("atualizado", it.toEpochMilli()) }

        val registros = JSArray()
        for (r in s.log.orEmpty()) {
            val o = JSObject()
            o.put("t", r.timestamp.toEpochMilli())
            o.numero("fc", r.heartRate)
            o.numero("vel", r.speed)
            o.numero("cad", r.cadence)
            o.numero("pot", r.power)
            registros.put(o)
        }
        t.put("registros", registros)

        val percurso = JSArray()
        for (g in s.route.orEmpty()) {
            val o = JSObject()
            o.put("t", g.timestamp.toEpochMilli())
            o.put("lat", g.latitude.toDouble())
            o.put("lon", g.longitude.toDouble())
            o.numero("alt", g.altitude)
            percurso.put(o)
        }
        t.put("percurso", percurso)
        return t
    }
}
