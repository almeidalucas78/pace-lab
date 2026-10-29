import { useState, type FormEvent } from 'react'
import { salvarToken, testarToken } from '../api/cliente'

/** Primeira vez no navegador: pede o API_TOKEN do .env (ADR 0011). */
export function Token() {
  const [valor, setValor] = useState('')
  const [erro, setErro] = useState<string | null>(null)
  const [testando, setTestando] = useState(false)

  async function entrar(ev: FormEvent) {
    ev.preventDefault()
    setTestando(true)
    setErro(null)
    try {
      if (await testarToken(valor.trim())) salvarToken(valor.trim())
      else setErro('Token recusado. Confira o API_TOKEN no arquivo .env do projeto.')
    } catch {
      setErro('Não consegui falar com o backend. O `treino servico` está aberto?')
    } finally {
      setTestando(false)
    }
  }

  return (
    <div style={{ display: 'grid', placeItems: 'center', minHeight: '100vh', padding: 16 }}>
      <form className="cartao pilha" style={{ width: 'min(420px, 100%)' }} onSubmit={entrar}>
        <h1>Pace Lab</h1>
        <p className="fraco" style={{ margin: 0 }}>
          Cole o <code>API_TOKEN</code> do arquivo <code>.env</code>. Ele fica salvo neste navegador.
        </p>
        <input className="campo" type="password" value={valor} onChange={(e) => setValor(e.target.value)}
               placeholder="API_TOKEN" autoFocus />
        {erro && <div className="erro-caixa">{erro}</div>}
        <button className="botao" disabled={!valor.trim() || testando}>{testando ? 'Conferindo...' : 'Entrar'}</button>
      </form>
    </div>
  )
}
