import { useState, type FormEvent } from 'react'
import { lerServidor, salvarServidor, salvarToken, testarToken } from '../api/cliente'
import { ehApp } from '../plataforma'

/**
 * Primeira vez: pede o API_TOKEN do .env (ADR 0011). No app Android pede também o endereço do PC
 * (o jeito mais fácil é o QR do Conectar celular, que preenche os dois).
 */
export function Token() {
  const app = ehApp()
  const [valor, setValor] = useState('')
  const [servidor, setServidor] = useState(() => lerServidor() ?? 'https://')
  const [erro, setErro] = useState<string | null>(null)
  const [testando, setTestando] = useState(false)

  async function entrar(ev: FormEvent) {
    ev.preventDefault()
    setTestando(true)
    setErro(null)
    if (app) salvarServidor(servidor)
    try {
      if (await testarToken(valor.trim())) salvarToken(valor.trim())
      else setErro('Token recusado. Confira o API_TOKEN no arquivo .env do projeto.')
    } catch {
      setErro(app ? 'Não consegui falar com o PC. Confira o endereço, o Tailscale e se o Treino está aberto.'
        : 'Não consegui falar com o backend. O `treino servico` está aberto?')
    } finally {
      setTestando(false)
    }
  }

  return (
    <div style={{ display: 'grid', placeItems: 'center', minHeight: '100vh', padding: 16 }}>
      <form className="cartao pilha" style={{ width: 'min(420px, 100%)' }} onSubmit={entrar}>
        <h1>Pace Lab</h1>
        {app && (
          <>
            <p className="fraco" style={{ margin: 0 }}>
              Mais fácil: no PC, abra <strong>Conectar celular</strong> e leia o QR do app Android com este celular.
              Ou preencha à mão:
            </p>
            <input className="campo" type="url" value={servidor} onChange={(e) => setServidor(e.target.value)}
                   placeholder="https://pacelab.nome-da-rede.ts.net" />
          </>
        )}
        <p className="fraco" style={{ margin: 0 }}>
          Cole o <code>API_TOKEN</code> do arquivo <code>.env</code>. Ele fica salvo neste {app ? 'app' : 'navegador'}.
        </p>
        <input className="campo" type="password" value={valor} onChange={(e) => setValor(e.target.value)}
               placeholder="API_TOKEN" autoFocus={!app} />
        {erro && <div className="erro-caixa">{erro}</div>}
        <button className="botao" disabled={!valor.trim() || testando || (app && !/^https:\/\/.+/.test(servidor))}>
          {testando ? 'Conferindo...' : 'Entrar'}
        </button>
      </form>
    </div>
  )
}
