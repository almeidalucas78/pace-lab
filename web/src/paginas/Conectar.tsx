import { useQuery } from '@tanstack/react-query'
import QRCode from 'qrcode'
import { useState } from 'react'
import { api, lerToken } from '../api/cliente'
import { Estado } from '../componentes/Estado'

interface ConfigPainel { url_celular: string | null }

/**
 * QR code com o endereço do Tailscale para abrir o painel no celular (ADR 0012). No navegador o celular entra com a
 * conta; o QR do app Android ainda leva o token (só existe quando o painel roda no app, até a etapa 8 da fase 9).
 */
export function Conectar() {
  const config = useQuery({ queryKey: ['painel', 'config'], queryFn: () => api<ConfigPainel>('/painel/config') })
  const [qr, setQr] = useState<string | null>(null)
  const [erro, setErro] = useState<string | null>(null)

  const token = lerToken()
  // navegador: abre o painel (o celular entra com a conta); app: página que repassa endereço e token ao app Android
  async function mostrar(url: string, paraApp: boolean) {
    try {
      const base = url.replace(/\/+$/, '')
      const destino = paraApp ? `${base}/abrir-app#token=${encodeURIComponent(token ?? '')}` : `${base}/`
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
              {token && <li><strong>App Android:</strong> leia o QR do app, abra o link no Chrome e toque em <strong>Abrir o app</strong>.</li>}
              <li><strong>Navegador:</strong> leia o QR do navegador, abra o link e entre com a sua conta (dá para instalar pelo menu ⋮ do Chrome).</li>
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
                <button className="botao" onClick={() => mostrar(c.url_celular!, false)}>QR do navegador</button>
                {token && <button className="botao-sec" onClick={() => mostrar(c.url_celular!, true)}>QR do app Android</button>}
              </div>
            )}
            {token ? (
              <div className="erro-caixa" style={{ background: 'var(--alerta-suave)', color: 'var(--alerta)' }}>
                O QR do app contém o seu token de acesso. Não compartilhe nem tire foto dele.
              </div>
            ) : (
              <div className="fraco pequeno">O app Android ganha a tela de entrar com a conta na próxima etapa.</div>
            )}
            {erro && <div className="erro-caixa">{erro}</div>}
          </div>
        )}
      </Estado>
    </div>
  )
}
