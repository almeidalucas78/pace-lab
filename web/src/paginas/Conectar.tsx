import { useQuery } from '@tanstack/react-query'
import QRCode from 'qrcode'
import { useState } from 'react'
import { api } from '../api/cliente'
import { Estado } from '../componentes/Estado'

interface ConfigPainel { url_celular: string | null }

/**
 * QR code com o endereço do Tailscale para abrir o painel no celular (ADR 0012). O celular entra com a conta, no
 * navegador ou no app Android (no app, basta digitar este endereço na tela de entrar).
 */
export function Conectar() {
  const config = useQuery({ queryKey: ['painel', 'config'], queryFn: () => api<ConfigPainel>('/painel/config') })
  const [qr, setQr] = useState<string | null>(null)
  const [erro, setErro] = useState<string | null>(null)

  async function mostrar(url: string) {
    try {
      const destino = `${url.replace(/\/+$/, '')}/`
      setQr(await QRCode.toDataURL(destino, { width: 320, margin: 2 }))
    } catch (e) {
      setErro(e instanceof Error ? e.message : String(e))
    }
  }

  return (
    <div className="pilha" style={{ maxWidth: 640 }}>
      <div>
        <h1>Conectar celular</h1>
        <p className="subtitulo">Abra o Pace Lab no celular sem digitar o endereço.</p>
      </div>
      <Estado consulta={config}>
        {(c) => !c.url_celular ? (
          <div className="cartao pilha">
            <strong>Endereço do celular não configurado.</strong>
            <span className="fraco">
              Depois de ativar o Tailscale (guia em <code>docs/celular.md</code>), coloque o endereço no <code>.env</code>,
              por exemplo <code>PAINEL_URL_CELULAR=https://pacelab.nome-da-rede.ts.net</code>, e reabra o Treino.
            </span>
          </div>
        ) : (
          <div className="cartao pilha">
            <ol style={{ margin: 0, paddingLeft: 20 }}>
              <li>No celular, ligue o Tailscale.</li>
              <li><strong>Navegador:</strong> leia o QR, abra o link e entre com a sua conta (dá para instalar pelo menu ⋮ do Chrome).</li>
              <li><strong>App Android:</strong> na tela de entrar do app, use o endereço abaixo.</li>
            </ol>
            <div className="fraco pequeno">Endereço: {c.url_celular}</div>
            {qr ? (
              <div className="pilha" style={{ alignItems: 'center' }}>
                <img src={qr} alt="QR code para abrir o Pace Lab no celular" width={320} height={320}
                     style={{ background: '#fff', borderRadius: 8 }} />
                <button className="botao-sec" onClick={() => setQr(null)}>Esconder QR code</button>
              </div>
            ) : (
              <div className="linha">
                <button className="botao" onClick={() => mostrar(c.url_celular!)}>Mostrar QR code</button>
              </div>
            )}
            {erro && <div className="erro-caixa">{erro}</div>}
          </div>
        )}
      </Estado>
    </div>
  )
}
