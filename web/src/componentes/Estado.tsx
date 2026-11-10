import type { UseQueryResult } from '@tanstack/react-query'
import type { ReactNode } from 'react'
import { ErroApi } from '../api/cliente'

/**
 * Mostra "carregando" ou o erro de uma consulta; quando há dados, renderiza os filhos.
 * Dados guardados no aparelho aparecem mesmo se a busca nova falhou (PC fora do ar).
 */
export function Estado<T>({ consulta, children, vazio }: {
  consulta: UseQueryResult<T>
  children: (dados: NonNullable<T>) => ReactNode
  vazio?: ReactNode
}) {
  const temDados = consulta.data != null && !(Array.isArray(consulta.data) && consulta.data.length === 0)
  if (temDados) return <>{children(consulta.data as NonNullable<T>)}</>
  if (consulta.isPending && consulta.fetchStatus !== 'idle') return <div className="carregando">Carregando...</div>
  if (consulta.isError) {
    const foraDoAr = consulta.error instanceof ErroApi && consulta.error.message === 'PC fora do ar'
    return (
      <div className="erro-caixa">
        {foraDoAr ? 'PC fora do ar e esta tela ainda não tinha sido aberta neste aparelho.' : `Erro: ${consulta.error.message}`}
      </div>
    )
  }
  if (consulta.isPending) return <div className="carregando">Aguardando conexão com o PC...</div>
  return <div className="vazio">{vazio ?? 'Nada para mostrar.'}</div>
}
