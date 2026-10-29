// O que o usuário está vendo agora. A página define; o chat manda junto para a IA (ADR 0011).

import { createContext, useContext, useEffect, useState, type ReactNode } from 'react'

interface ContextoPagina {
  descricao: string | null
  definir: (descricao: string | null) => void
}

const Ctx = createContext<ContextoPagina>({ descricao: null, definir: () => {} })

export function ProvedorContexto({ children }: { children: ReactNode }) {
  const [descricao, definir] = useState<string | null>(null)
  return <Ctx.Provider value={{ descricao, definir }}>{children}</Ctx.Provider>
}

export const useContextoPagina = () => useContext(Ctx)

/** Use na página: `useDescreverPagina("o usuário está vendo o treino #356 ...")`. */
export function useDescreverPagina(descricao: string | null) {
  const { definir } = useContext(Ctx)
  useEffect(() => {
    definir(descricao)
    return () => definir(null)
  }, [descricao, definir])
}
