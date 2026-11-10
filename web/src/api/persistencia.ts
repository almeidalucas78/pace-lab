// Dados guardados no aparelho (ADR 0012): as respostas da API ficam no IndexedDB e aparecem na hora,
// mesmo com o PC fora do ar. Sair apaga tudo.

import { createAsyncStoragePersister } from '@tanstack/query-async-storage-persister'
import type { QueryClient } from '@tanstack/react-query'
import { del, get, set } from 'idb-keyval'

const CHAVE = 'pace-lab.dados'
export const VALIDADE_MS = 30 * 24 * 60 * 60 * 1000 // 30 dias
// Suba ao mudar o formato de alguma resposta da API: descarta o que estava guardado.
export const VERSAO_DADOS = '1'

/** Onde os dados ficam: o tipo é o que o persister do TanStack aceita. */
export type Armazenamento = NonNullable<Parameters<typeof createAsyncStoragePersister>[0]['storage']>

const indexedDb: Armazenamento = { getItem: get, setItem: set, removeItem: del }

/** `armazenamento` só muda nos testes (lá não há IndexedDB). */
export const criarPersister = (armazenamento: Armazenamento = indexedDb) =>
  createAsyncStoragePersister({ storage: armazenamento, key: CHAVE })

export const persister = criarPersister()

/**
 * Opções do PersistQueryClientProvider (usadas no main.tsx e nos testes).
 * Guarda toda consulta que tem dados, mesmo se a última busca falhou: o padrão do TanStack guarda só as de
 * status 'success', e aí, quando o PC caía com o app aberto, a nova gravação apagava justamente os dados.
 */
export const opcoesPersistencia = (p = persister) => ({
  persister: p,
  maxAge: VALIDADE_MS,
  buster: VERSAO_DADOS,
  dehydrateOptions: { shouldDehydrateQuery: (q: { state: { data: unknown } }) => q.state.data !== undefined },
})

export async function apagarDadosGuardados(queryClient: QueryClient): Promise<void> {
  queryClient.clear()
  try {
    await del(CHAVE)
  } catch {
    // navegador sem IndexedDB: não havia nada guardado
  }
}
