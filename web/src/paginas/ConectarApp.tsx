import { useState } from 'react'
import { api, ErroApi, lerSessao } from '../api/cliente'

const CHAVE = 'pace-lab.desafio-app'
const DESAFIO = /^[A-Za-z0-9_-]{43}$/

/**
 * Pedido de login do app que chegou em /entrar-app?desafio=...: guarda na aba (sobrevive à ida e volta do login com
 * Google, que volta para /) e limpa a barra de endereço. Chamada em main.tsx, antes de o roteador montar.
 */
export function guardarDesafioDaUrl(): void {
  try {
    if (window.location.pathname !== '/entrar-app') return
    const d = new URLSearchParams(window.location.search).get('desafio')
    if (d && DESAFIO.test(d)) sessionStorage.setItem(CHAVE, d)
    window.history.replaceState(null, '', '/')
  } catch {
    // sem armazenamento: o login do app não segue, o painel abre normal
  }
}

/** Pedido de login do app em andamento nesta aba, se houver. */
export function desafioPendente(): string | null {
  try {
    const guardado = sessionStorage.getItem(CHAVE)
    return guardado && DESAFIO.test(guardado) ? guardado : null
  } catch {
    return null
  }
}

export function esquecerDesafio(): void {
  try {
    sessionStorage.removeItem(CHAVE)
  } catch {
    // sem armazenamento
  }
}

/**
 * No navegador do celular, depois de entrar: confirma e devolve o login ao app Android por pacelab://entrou com um
 * código de uso único (fase 9, etapa 8). Só o app que abriu este pedido consegue trocar o código (PKCE).
 */
export function ConectarApp({ desafio, aoTerminar }: { desafio: string; aoTerminar: () => void }) {
  const usuario = lerSessao()
  const [link, setLink] = useState<string | null>(null)
  const [erro, setErro] = useState<string | null>(null)
  const [enviando, setEnviando] = useState(false)

  async function conectar() {
    setEnviando(true)
    setErro(null)
    try {
      const r = await api<{ codigo: string }>('/auth/app/codigo', { method: 'POST', body: JSON.stringify({ desafio }) })
      esquecerDesafio()
      const destino = `pacelab://entrou?codigo=${encodeURIComponent(r.codigo)}`
      setLink(destino)
      window.location.href = destino
    } catch (e) {
      setErro(e instanceof ErroApi && e.status === 0 ? 'Não consegui falar com o servidor. Tente de novo.'
        : e instanceof Error ? e.message : String(e))
    } finally {
      setEnviando(false)
    }
  }

  function cancelar() {
    esquecerDesafio()
    aoTerminar()
  }

  return (
    <div style={{ display: 'grid', placeItems: 'center', minHeight: '100vh', padding: 16 }}>
      <div className="cartao pilha" style={{ width: 'min(420px, 100%)' }}>
        <h1 style={{ margin: 0 }}>Conectar o app</h1>
        {link ? (
          <>
            <p style={{ margin: 0 }}>Voltando para o app Pace Lab...</p>
            <a className="botao" href={link} style={{ textAlign: 'center', textDecoration: 'none' }}>Abrir o app</a>
            <p className="fraco pequeno" style={{ margin: 0 }}>
              Se nada acontecer, toque no botão. O link vale por 10 minutos e uma vez só.
            </p>
          </>
        ) : (
          <>
            <p style={{ margin: 0 }}>
              Entrar no app Pace Lab deste celular com a conta <strong>{usuario?.email ?? 'atual'}</strong>?
            </p>
            <p className="fraco pequeno" style={{ margin: 0 }}>
              Só confirme se foi você que tocou em Entrar no app agora há pouco.
            </p>
            {erro && <div className="erro-caixa" role="alert">{erro}</div>}
            <div className="linha">
              <button className="botao" disabled={enviando} onClick={conectar}>
                {enviando ? 'Conectando...' : 'Conectar o app'}
              </button>
              <button className="botao-sec" disabled={enviando} onClick={cancelar}>Cancelar</button>
            </div>
          </>
        )}
      </div>
    </div>
  )
}
