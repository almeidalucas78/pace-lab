import { useQueryClient } from '@tanstack/react-query'
import { useEffect, useState } from 'react'
import { lerConexao, type Conexao } from '../api/cliente'
import { momentoLocal } from '../util/formato'

export function useConexao(): Conexao {
  const [estado, setEstado] = useState(lerConexao)
  useEffect(() => {
    const atualizar = () => setEstado(lerConexao())
    window.addEventListener('pace-lab:conexao', atualizar)
    return () => window.removeEventListener('pace-lab:conexao', atualizar)
  }, [])
  return estado
}

/** Faixa no topo quando o PC não responde: os dados na tela são os guardados no aparelho. */
export function AvisoConexao() {
  const { online, ultimoContato } = useConexao()
  const qc = useQueryClient()
  const [tentando, setTentando] = useState(false)
  if (online) return null

  async function tentar() {
    setTentando(true)
    try {
      await qc.refetchQueries({ type: 'active' })
    } finally {
      setTentando(false)
    }
  }

  return (
    <div className="aviso-conexao">
      <div>
        <strong>PC fora do ar.</strong>{' '}
        {ultimoContato ? `Mostrando os dados guardados neste aparelho (de ${momentoLocal(ultimoContato)}).`
          : 'Ainda não há dados guardados neste aparelho.'}
        <div className="pequeno">Confira se o PC está ligado, o Treino aberto e o Tailscale ativo nos dois aparelhos.</div>
      </div>
      <button className="botao-sec" onClick={tentar} disabled={tentando}>{tentando ? 'Tentando...' : 'Tentar de novo'}</button>
    </div>
  )
}

/** Botão do topo no celular: busca de novo os dados da tela. */
export function BotaoAtualizar() {
  const qc = useQueryClient()
  const { online, ultimoContato } = useConexao()
  const [ocupado, setOcupado] = useState(false)

  async function atualizar() {
    setOcupado(true)
    try {
      await qc.refetchQueries({ type: 'active' })
    } finally {
      setOcupado(false)
    }
  }

  return (
    <button className="botao-sec pequeno" onClick={atualizar} disabled={ocupado}
            title={ultimoContato ? `Última resposta do PC: ${momentoLocal(ultimoContato)}` : undefined}>
      {ocupado ? 'Atualizando...' : online ? 'Atualizar' : 'Offline'}
    </button>
  )
}
