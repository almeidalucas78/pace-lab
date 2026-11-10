import { useQuery } from '@tanstack/react-query'
import QRCode from 'qrcode'
import { useState } from 'react'
import { api, lerToken } from '../api/cliente'
import { Estado } from '../componentes/Estado'

interface ConfigPainel { url_celular: string | null }

/** QR code com o endereço do Tailscale e o token, para abrir o painel no celular já conectado (ADR 0012). */
export function Conectar() {
  const config = useQuery({ queryKey: ['painel', 'config'], queryFn: () => api<ConfigPainel>('/painel/config') })
  const [qr, setQr] = useState<string | null>(null)
  const [erro, setErro] = useState<string | null>(null)

  async function mostrar(url: string) {
    try {
      const destino = `${url.replace(/\/+$/, '')}/#token=${encodeURIComponent(lerToken() ?? '')}`
      setQr(await QRCode.toDataURL(destino, { width: 320, margin: 2 }))
    } catch (e) {
      setErro(e instanceof Error ? e.message : String(e))
    }
  }

  return (
    <div className="pilha" style={{ maxWidth: 640 }}>
      <div>
        <h1>Conectar celular</h1>
        <p className="subtitulo">Abra o Pace Lab no celular sem digitar o token.</p>
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
              <li>Aponte a câmera para o QR code e abra o link.</li>
              <li>No Chrome do celular, menu ⋮ e <strong>Instalar app</strong> (ou "Adicionar à tela inicial").</li>
            </ol>
            <div className="fraco pequeno">Endereço: {c.url_celular}</div>
            {qr ? (
              <div className="pilha" style={{ alignItems: 'center' }}>
                <img src={qr} alt="QR code para abrir o Pace Lab no celular" width={320} height={320}
                     style={{ background: '#fff', borderRadius: 8 }} />
                <button className="botao-sec" onClick={() => setQr(null)}>Esconder QR code</button>
              </div>
            ) : (
              <button className="botao" onClick={() => mostrar(c.url_celular!)}>Mostrar QR code</button>
            )}
            <div className="erro-caixa" style={{ background: 'var(--alerta-suave)', color: 'var(--alerta)' }}>
              O QR code contém o seu token de acesso. Não compartilhe nem tire foto dele.
            </div>
            {erro && <div className="erro-caixa">{erro}</div>}
          </div>
        )}
      </Estado>
    </div>
  )
}
