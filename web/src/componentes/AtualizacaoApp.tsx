import { App as AppNativo } from '@capacitor/app'
import { useCallback, useEffect, useState } from 'react'
import {
  pluginAtualizacao, procurarAtualizacao, tokenAtual, urlDoApk, versaoInstalada,
  type PluginAtualizacao, type VersaoPublicada,
} from '../atualizacao'

type Estado =
  | { tipo: 'nada' }
  | { tipo: 'disponivel'; versao: VersaoPublicada }
  | { tipo: 'permissao'; versao: VersaoPublicada }
  | { tipo: 'baixando'; versao: VersaoPublicada; pct: number | null }
  | { tipo: 'confirmar'; versao: VersaoPublicada }
  | { tipo: 'erro'; versao: VersaoPublicada; mensagem: string }

const tamanhoMb = (v: VersaoPublicada) => (v.tamanho ? ` (${(v.tamanho / 1_048_576).toFixed(1).replace('.', ',')} MB)` : '')

interface Props {
  plugin?: PluginAtualizacao
  instalada?: () => Promise<number>
}

/**
 * Só no app Android: ao abrir e ao voltar para o app, confere se o PC publicou uma versão nova.
 * Se sim, oferece baixar e abre o instalador do Android (que sempre pede confirmação).
 */
export function AtualizacaoApp({ plugin = pluginAtualizacao, instalada = versaoInstalada }: Props) {
  const [estado, setEstado] = useState<Estado>({ tipo: 'nada' })

  const procurar = useCallback(async () => {
    try {
      const v = await procurarAtualizacao(await instalada())
      setEstado((e) => (v && (e.tipo === 'nada' || e.tipo === 'disponivel') ? { tipo: 'disponivel', versao: v } : e))
    } catch {
      // PC fora do ar: tenta de novo na próxima abertura, sem aviso
    }
  }, [instalada])

  useEffect(() => {
    // Procurar versão nova ao abrir consulta o servidor (sistema externo): uso legítimo de efeito.
    // oxlint-disable-next-line react/set-state-in-effect
    procurar()
    const ouvintes = [
      AppNativo.addListener('resume', () => { procurar() }),
      plugin.addListener('progresso', ({ pct }) => {
        setEstado((e) => (e.tipo === 'baixando' ? { ...e, pct } : e))
      }),
      plugin.addListener('instalacao', ({ status, mensagem }) => {
        setEstado((e) => {
          if (e.tipo === 'nada') return e
          if (status === 'falhou') return { tipo: 'erro', versao: e.versao, mensagem: mensagem ?? 'instalação cancelada' }
          return { tipo: 'confirmar', versao: e.versao }
        })
      }),
    ]
    return () => { ouvintes.forEach((o) => { o.then((h) => h.remove()) }) }
  }, [procurar, plugin])

  if (estado.tipo === 'nada') return null
  const v = estado.versao

  async function atualizar() {
    try {
      if (!(await plugin.podeInstalar()).permitido) {
        setEstado({ tipo: 'permissao', versao: v })
        await plugin.abrirPermissao()
        return
      }
      setEstado({ tipo: 'baixando', versao: v, pct: null })
      await plugin.instalar({ url: urlDoApk(), token: tokenAtual(), sha256: v.sha256 })
      setEstado((e) => (e.tipo === 'baixando' ? { tipo: 'confirmar', versao: v } : e))
    } catch (e) {
      setEstado({ tipo: 'erro', versao: v, mensagem: e instanceof Error ? e.message : String(e) })
    }
  }

  return (
    <div className="aviso-versao" role="status">
      {estado.tipo === 'disponivel' && <span>Versão nova do app: {v.nome ?? v.codigo}{tamanhoMb(v)}.</span>}
      {estado.tipo === 'permissao' && (
        <span>Permita que o Pace Lab instale apps (opção que o Android abriu) e toque em Atualizar de novo.</span>
      )}
      {estado.tipo === 'baixando' && <span className="pensando">Baixando do PC{estado.pct != null ? `: ${estado.pct}%` : ''}</span>}
      {estado.tipo === 'confirmar' && <span>Confirme a instalação na tela do Android.</span>}
      {estado.tipo === 'erro' && <span className="erro-texto">Não foi possível atualizar: {estado.mensagem}</span>}
      {(estado.tipo === 'disponivel' || estado.tipo === 'permissao' || estado.tipo === 'erro') && (
        <button className="botao" onClick={atualizar}>Atualizar</button>
      )}
      {estado.tipo !== 'baixando' && (
        <button className="botao-sec" onClick={() => setEstado({ tipo: 'nada' })}>Depois</button>
      )}
    </div>
  )
}
