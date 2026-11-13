import { useMutation, useQueryClient } from '@tanstack/react-query'
import { useEffect, useRef, useState, type KeyboardEvent } from 'react'
import Markdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { api } from '../api/cliente'
import { useConversa, useConversas } from '../api/consultas'
import type { Conversa, MensagemChat, RespostaChat } from '../api/tipos'
import { useContextoPagina } from '../contexto'

// Ferramentas que gravam algo: depois delas, os dados da tela são recarregados.
const GRAVAM = new Set(['salvar_plano', 'alterar_sessao', 'adicionar_sessao', 'arquivar_plano', 'registrar_sensacao'])

const NOMES_FERRAMENTAS: Record<string, string> = {
  ultimo_treino: 'último treino', detalhe_treino: 'detalhe do treino', listar_treinos: 'lista de treinos',
  resumo_semanas: 'semanas', carga_atual: 'carga', perfil_atleta: 'perfil', registrar_sensacao: 'registrou sensação',
  ver_sensacoes: 'sensações', status_sincronizacao: 'sincronização', salvar_plano: 'salvou o plano',
  plano_atual: 'plano', aderencia_plano: 'aderência', alterar_sessao: 'alterou sessão',
  adicionar_sessao: 'acrescentou sessão', arquivar_plano: 'arquivou o plano', listar_planos: 'planos',
}

function Mensagem({ m }: { m: Pick<MensagemChat, 'papel' | 'texto' | 'ferramentas'> }) {
  return (
    <div className={`msg ${m.papel}`}>
      {m.papel === 'assistant' ? <Markdown remarkPlugins={[remarkGfm]}>{m.texto}</Markdown> : m.texto}
      {m.ferramentas?.length ? (
        <div className="ferramentas">consultou: {m.ferramentas.map((f) => NOMES_FERRAMENTAS[f] ?? f).join(', ')}</div>
      ) : null}
    </div>
  )
}

/** No PC abre ao lado (com `fechar`); no celular é a página /chat (`pagina`). */
export function Chat({ fechar, pagina }: { fechar?: () => void; pagina?: boolean }) {
  const qc = useQueryClient()
  const { descricao } = useContextoPagina()
  const [conversaId, setConversaId] = useState<number | null>(null)
  const [provedor, setProvedor] = useState<'claude' | 'gemini'>('claude')
  const [texto, setTexto] = useState('')
  const [usarContexto, setUsarContexto] = useState(true)
  const conversas = useConversas()
  const conversa = useConversa(conversaId)
  const fim = useRef<HTMLDivElement>(null)

  const enviar = useMutation({
    mutationFn: (mensagem: string) => api<RespostaChat>('/chat', {
      method: 'POST',
      body: JSON.stringify({
        mensagem, conversa_id: conversaId, provedor: conversaId ? null : provedor,
        contexto: usarContexto ? descricao : null,
      }),
    }),
    onSuccess: async (r, mensagem) => {
      // Mostra pergunta e resposta na hora, sem esperar buscar a conversa de novo (no celular isso demora
      // e a tela ficava vazia). A busca logo abaixo confirma com o que ficou gravado no PC.
      qc.setQueryData<Conversa>(['conversas', r.conversa_id], (antes) => ({
        ...(antes ?? { id: r.conversa_id, titulo: mensagem.slice(0, 80), provedor: r.provedor, atualizada: '', criada: '' }),
        mensagens: [
          ...(antes?.mensagens ?? []),
          { papel: 'user', texto: mensagem, quando: '', ferramentas: null },
          { papel: 'assistant', texto: r.resposta, quando: '', ferramentas: r.ferramentas },
        ],
      }))
      setConversaId(r.conversa_id)
      await qc.invalidateQueries({ queryKey: ['conversas'] })
      if (r.ferramentas.some((f) => GRAVAM.has(f))) {
        await Promise.all([qc.invalidateQueries({ queryKey: ['planos'] }), qc.invalidateQueries({ queryKey: ['treinos'] })])
      }
    },
  })

  const mensagens = conversa.data?.mensagens ?? []
  // Com chaves de propósito: o efeito não pode devolver nada. No Chrome scrollIntoView devolve uma Promise,
  // e o React tentava chamá-la como função de limpeza ao enviar ("destroy is not a function").
  useEffect(() => {
    fim.current?.scrollIntoView?.({ behavior: 'smooth' })
    // As dependências são o gatilho de propósito: rolar quando chega mensagem ou quando começa o envio.
    // oxlint-disable-next-line react/exhaustive-effect-dependencies
  }, [mensagens.length, enviar.isPending])

  function mandar() {
    const m = texto.trim()
    if (!m || enviar.isPending) return
    setTexto('')
    enviar.mutate(m)
  }

  function teclado(ev: KeyboardEvent<HTMLTextAreaElement>) {
    if (ev.key === 'Enter' && !ev.shiftKey) {
      ev.preventDefault()
      mandar()
    }
  }

  const provedorAtual = conversa.data?.provedor ?? provedor

  return (
    <aside className={`chat${pagina ? ' pagina' : ''}`}>
      <div className="chat-cab">
        <select className="campo" style={{ flex: 1, minWidth: 0 }} value={conversaId ?? ''}
                onChange={(e) => setConversaId(e.target.value ? Number(e.target.value) : null)}>
          <option value="">Nova conversa</option>
          {(conversas.data ?? []).map((c) => (
            <option key={c.id} value={c.id}>{c.titulo ?? `Conversa ${c.id}`} ({c.provedor})</option>
          ))}
        </select>
        {fechar && <button className="botao-sec" onClick={fechar} title="Fechar o chat">fechar</button>}
      </div>

      <div className="chat-msgs">
        {conversaId == null && !enviar.isPending && (
          <div className="fraco pequeno">
            Pergunte sobre seus treinos, peça um plano ou conte como se sentiu. Os números vêm do banco;
            a IA interpreta.
          </div>
        )}
        {mensagens.map((m, i) => <Mensagem key={i} m={m} />)}
        {enviar.isPending && (
          <>
            <Mensagem m={{ papel: 'user', texto: enviar.variables ?? '', ferramentas: null }} />
            <div className="msg assistant fraco"><span className="pensando">{provedorAtual === 'gemini' ? 'Gemini' : 'Claude'} pensando</span></div>
          </>
        )}
        {enviar.isError && <div className="erro-caixa">{enviar.error.message}</div>}
        <div ref={fim} />
      </div>

      <div className="chat-form">
        {descricao && (
          <label className="contexto-chat linha" style={{ gap: 6 }}>
            <input type="checkbox" checked={usarContexto} onChange={(e) => setUsarContexto(e.target.checked)} />
            mandar o que estou vendo ({descricao.split(' (')[0].replace('o usuário está ', '')})
          </label>
        )}
        <textarea className="campo" value={texto} onChange={(e) => setTexto(e.target.value)} onKeyDown={teclado}
                  placeholder="Escreva... (Enter envia, Shift+Enter quebra linha)" />
        <div className="linha entre">
          {conversaId == null ? (
            <div className="abas">
              {(['claude', 'gemini'] as const).map((p) => (
                <button key={p} className={provedor === p ? 'ativa' : ''} onClick={() => setProvedor(p)}>
                  {p === 'claude' ? 'Claude' : 'Gemini'}
                </button>
              ))}
            </div>
          ) : <span className="fraco pequeno">com {provedorAtual === 'gemini' ? 'Gemini' : 'Claude'}</span>}
          <button className="botao" onClick={mandar} disabled={!texto.trim() || enviar.isPending}>Enviar</button>
        </div>
      </div>
    </aside>
  )
}
