import { useEffect, useState, type FormEvent } from 'react'
import { lerServidor } from '../api/cliente'
import { EVENTO_ERRO, iniciarLoginApp } from '../api/loginApp'

const primeiraMaiuscula = (s: string) => (s ? s[0].toUpperCase() + s.slice(1) : s)

/**
 * Tela de entrar do app Android (fase 9, etapa 8): pede o endereço do servidor e abre a tela de entrar dele no
 * navegador do celular, onde dá para usar senha ou Google. O login volta ao app sozinho.
 */
export function EntrarApp() {
  const [servidor, setServidor] = useState(() => lerServidor() ?? 'https://')
  const [erro, setErro] = useState<string | null>(null)
  const [abrindo, setAbrindo] = useState(false)

  useEffect(() => {
    const mostrar = (e: Event) => { setErro(primeiraMaiuscula(String((e as CustomEvent).detail))) }
    window.addEventListener(EVENTO_ERRO, mostrar)
    return () => { window.removeEventListener(EVENTO_ERRO, mostrar) }
  }, [])

  async function entrar(ev: FormEvent) {
    ev.preventDefault()
    setAbrindo(true)
    setErro(null)
    try {
      await iniciarLoginApp(servidor.trim())
    } catch (e) {
      setErro(e instanceof Error ? e.message : String(e))
    } finally {
      setAbrindo(false)
    }
  }

  const valido = /^https:\/\/[^/\s]+/.test(servidor.trim())
  return (
    <div style={{ display: 'grid', placeItems: 'center', minHeight: '100vh', padding: 16 }}>
      <form className="cartao pilha" style={{ width: 'min(420px, 100%)' }} onSubmit={entrar}>
        <div className="linha" style={{ gap: 8 }}>
          <img src="/favicon.svg" width={28} height={28} alt="" />
          <h1 style={{ margin: 0 }}>Pace Lab</h1>
        </div>
        <label className="rotulo">
          Endereço do servidor
          <input className="campo" type="url" inputMode="url" value={servidor} autoComplete="url"
                 onChange={(e) => setServidor(e.target.value)} placeholder="https://pacelab.nome-da-rede.ts.net" />
        </label>
        <p className="fraco pequeno" style={{ margin: 0 }}>
          O login abre no navegador do celular, com senha ou Google. Depois toque em <strong>Conectar o app</strong> e
          você volta para cá já dentro da conta.
        </p>
        {erro && <div className="erro-caixa" role="alert">{erro}</div>}
        <button className="botao" disabled={!valido || abrindo}>{abrindo ? 'Abrindo...' : 'Entrar'}</button>
      </form>
    </div>
  )
}
