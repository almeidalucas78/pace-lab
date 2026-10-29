import type { UseQueryResult } from '@tanstack/react-query'
import type { ReactNode } from 'react'

/** Mostra "carregando" ou o erro de uma consulta; quando há dados, renderiza os filhos. */
export function Estado<T>({ consulta, children, vazio }: {
  consulta: UseQueryResult<T>
  children: (dados: NonNullable<T>) => ReactNode
  vazio?: ReactNode
}) {
  if (consulta.isPending) return <div className="carregando">Carregando...</div>
  if (consulta.isError) return <div className="erro-caixa">Erro: {consulta.error.message}</div>
  if (consulta.data == null || (Array.isArray(consulta.data) && consulta.data.length === 0)) {
    return <div className="vazio">{vazio ?? 'Nada para mostrar.'}</div>
  }
  return <>{children(consulta.data as NonNullable<T>)}</>
}
