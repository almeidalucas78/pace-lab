import { Component, type ErrorInfo, type ReactNode } from 'react'

interface Estado { erro: Error | null; onde: string | null }

/**
 * Sem isto, um erro ao desenhar a tela desmonta o painel inteiro (tela preta).
 * Mostra o erro e deixa recarregar; `area` diz que parte quebrou.
 */
export class ErroTela extends Component<{ area: string; children: ReactNode }, Estado> {
  state: Estado = { erro: null, onde: null }

  static getDerivedStateFromError(erro: Error): Partial<Estado> {
    return { erro }
  }

  componentDidCatch(erro: Error, info: ErrorInfo) {
    console.error(`[Pace Lab] erro em ${this.props.area}:`, erro, info.componentStack)
    this.setState({ onde: info.componentStack?.trim().split('\n').slice(0, 6).join('\n') ?? null })
  }

  render() {
    const { erro, onde } = this.state
    if (!erro) return this.props.children
    return (
      <div className="cartao pilha" style={{ margin: 16 }}>
        <strong>Algo quebrou em {this.props.area}.</strong>
        <div className="erro-caixa" style={{ whiteSpace: 'pre-wrap', overflowWrap: 'anywhere' }}>
          {erro.name}: {erro.message}
          {onde ? `\n\n${onde}` : ''}
        </div>
        <div className="linha">
          <button className="botao" onClick={() => this.setState({ erro: null, onde: null })}>Tentar de novo</button>
          <button className="botao-sec" onClick={() => window.location.reload()}>Recarregar a página</button>
        </div>
      </div>
    )
  }
}
