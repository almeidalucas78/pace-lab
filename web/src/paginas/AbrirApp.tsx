import { useState } from 'react'

/**
 * Aberta pelo QR "App Android" do Conectar celular, no navegador do celular (sem token salvo).
 * Lê o token do fragmento (#token=, que não vai ao servidor) e oferece o link que abre o app
 * já com o endereço deste PC e o token (ADR 0013). A câmera nem sempre abre `pacelab://` direto;
 * o Chrome abre ao tocar no botão.
 */
export function AbrirApp() {
  const [token] = useState(() => {
    const m = window.location.hash.match(/(?:^#|&)token=([^&]+)/)
    if (m) window.history.replaceState(null, '', window.location.pathname) // tira o token da barra de endereço
    return m ? decodeURIComponent(m[1]) : null
  })
  const link = token
    ? `pacelab://conectar?servidor=${encodeURIComponent(window.location.origin)}&token=${encodeURIComponent(token)}`
    : null

  return (
    <div style={{ display: 'grid', placeItems: 'center', minHeight: '100vh', padding: 16 }}>
      <div className="cartao pilha" style={{ width: 'min(420px, 100%)' }}>
        <h1>Abrir no app Pace Lab</h1>
        {link ? (
          <>
            <p className="fraco" style={{ margin: 0 }}>
              Toque no botão para abrir o app já conectado a este PC.
            </p>
            <a className="botao" href={link} style={{ textAlign: 'center', textDecoration: 'none' }}>Abrir o app</a>
            <p className="fraco pequeno" style={{ margin: 0 }}>
              Se nada acontecer, o app ainda não está instalado neste celular.
            </p>
          </>
        ) : (
          <div className="erro-caixa">
            Link sem token. Gere o QR de novo no PC, em Conectar celular.
          </div>
        )}
      </div>
    </div>
  )
}
