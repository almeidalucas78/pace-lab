import { App as AppNativo } from '@capacitor/app'
import { useQueryClient } from '@tanstack/react-query'
import { useCallback, useEffect, useRef, useState } from 'react'
import { samsungHealth, type FonteTreinos } from '../sync/fontes'
import { ErroSync, sincronizar, ultimaSincronizacao, type ResultadoSync } from '../sync/sincronizar'
import { momentoLocal } from '../util/formato'

const INTERVALO_MIN_MS = 2 * 60 * 1000 // ao voltar para o app, no máximo uma vez a cada 2 min

type Estado =
  | { tipo: 'parado' }
  | { tipo: 'sincronizando' }
  | { tipo: 'ok'; resultado: ResultadoSync }
  | { tipo: 'erro'; mensagem: string }

function resumo(r: ResultadoSync): string {
  const partes = []
  if (r.novos) partes.push(r.novos === 1 ? '1 treino novo' : `${r.novos} treinos novos`)
  if (r.atualizados) partes.push(`${r.atualizados} atualizado(s)`)
  if (r.duplicados) partes.push(`${r.duplicados} já vindo(s) do Strava`)
  return partes.length ? partes.join(', ') : 'nada novo'
}

function mensagemDeErro(e: unknown): string {
  if (e instanceof ErroSync) {
    if (e.motivo === 'sem_permissao') return `${e.message} Toque em Sincronizar e permita.`
    if (e.motivo === 'fonte') return `${e.message} Confira se o modo desenvolvedor do Samsung Health está ligado.`
    return e.message
  }
  return e instanceof Error ? e.message : String(e)
}

/**
 * Só no app Android (ADR 0013): lê o Samsung Health e envia ao PC ao abrir o app, ao voltar para ele
 * e no botão. Mostra a situação no topo da tela.
 */
export function Sincronizacao({ fonte = samsungHealth }: { fonte?: FonteTreinos }) {
  const qc = useQueryClient()
  const [estado, setEstado] = useState<Estado>({ tipo: 'parado' })
  const rodando = useRef(false)
  const ultimaTentativa = useRef(0)

  const rodar = useCallback(async (forcar: boolean) => {
    if (rodando.current) return
    if (!forcar && Date.now() - ultimaTentativa.current < INTERVALO_MIN_MS) return
    rodando.current = true
    ultimaTentativa.current = Date.now()
    setEstado({ tipo: 'sincronizando' })
    try {
      const r = await sincronizar(fonte)
      setEstado({ tipo: 'ok', resultado: r })
      if (r.novos || r.atualizados || r.duplicados) await qc.invalidateQueries()
    } catch (e) {
      setEstado({ tipo: 'erro', mensagem: mensagemDeErro(e) })
    } finally {
      rodando.current = false
    }
  }, [fonte, qc])

  useEffect(() => {
    rodar(true)
    const ouvinte = AppNativo.addListener('resume', () => { rodar(false) })
    return () => { ouvinte.then((h) => h.remove()) }
  }, [rodar])

  const ultima = ultimaSincronizacao(fonte.nome)
  return (
    <div className="sincronizacao">
      <div className="pequeno">
        {estado.tipo === 'sincronizando' && <span className="pensando">Lendo o {fonte.rotulo}</span>}
        {estado.tipo === 'ok' && (
          <span>
            {fonte.rotulo}: {resumo(estado.resultado)}.
            {estado.resultado.semPercurso && ' Sem permissão de percurso: treinos chegam sem mapa.'}
          </span>
        )}
        {estado.tipo === 'erro' && <span className="erro-texto">{estado.mensagem}</span>}
        {estado.tipo === 'parado' && <span className="fraco">Última sincronização: {momentoLocal(ultima)}</span>}
      </div>
      <button className="botao-sec pequeno" onClick={() => rodar(true)} disabled={estado.tipo === 'sincronizando'}>
        Sincronizar
      </button>
    </div>
  )
}
