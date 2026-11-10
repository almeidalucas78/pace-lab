// Dados guardados no aparelho: abrir uma tela com o PC ligado, fechar o app, abrir de novo com o PC fora do ar.
import { QueryClient } from '@tanstack/react-query'
import { PersistQueryClientProvider } from '@tanstack/react-query-persist-client'
import { act } from 'react'
import { createRoot } from 'react-dom/client'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { salvarToken } from './cliente'
import { useCargaAtual } from './consultas'
import { criarPersister, opcoesPersistencia, type Armazenamento } from './persistencia'
import { Estado } from '../componentes/Estado'
import { ErroApi } from './cliente'

;(globalThis as { IS_REACT_ACT_ENVIRONMENT?: boolean }).IS_REACT_ACT_ENVIRONMENT = true

function memoria(): Armazenamento & { dados: Map<string, string> } {
  const dados = new Map<string, string>()
  return {
    dados,
    getItem: async (k) => dados.get(k) ?? null,
    setItem: async (k, v) => { dados.set(k, v) },
    removeItem: async (k) => { dados.delete(k) },
  }
}

// mesmas opções do main.tsx
const novoCliente = () => new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 60_000, gcTime: Infinity, refetchOnWindowFocus: true,
      retry: (falhas, erro) => !(erro instanceof ErroApi && erro.status < 500 && erro.status !== 0) && falhas < 2,
      retryDelay: 1,
    },
  },
})

function Tela() {
  const carga = useCargaAtual()
  return <Estado consulta={carga}>{(c) => <div>fitness {c.hoje.fitness}</div>}</Estado>
}

const espera = (ms: number) => act(async () => { await new Promise((r) => setTimeout(r, ms)) })
let raizes: ReturnType<typeof createRoot>[] = []
afterEach(() => {
  raizes.forEach((r) => act(() => r.unmount()))
  raizes = []
  document.body.innerHTML = ''
  vi.restoreAllMocks()
})

async function abrirApp(armazenamento: Armazenamento) {
  const div = document.createElement('div')
  document.body.appendChild(div)
  const raiz = createRoot(div)
  raizes.push(raiz)
  await act(async () => {
    raiz.render(
      <PersistQueryClientProvider client={novoCliente()}
                                  persistOptions={opcoesPersistencia(criarPersister(armazenamento))}>
        <Tela />
      </PersistQueryClientProvider>,
    )
  })
  return { div, fechar: () => act(() => raiz.unmount()) }
}

describe('dados guardados no aparelho', () => {
  it('tela aberta com o PC ligado aparece de novo com o PC fora do ar', async () => {
    salvarToken('x')
    const armazenamento = memoria()
    const carga = { hoje: { dia: '2026-11-09', carga: 0, fitness: 23.7, fadiga: 10.4, forma: 12.3 },
      ha_7_dias: null, ha_28_dias: null, carga_7_dias: 0, fc_max_usada: 214, fc_max_origem: 'estimada' }
    vi.spyOn(globalThis, 'fetch').mockImplementation(async () => new Response(JSON.stringify(carga), { status: 200 }))

    const app1 = await abrirApp(armazenamento)
    await espera(50)
    expect(app1.div.textContent).toContain('fitness 23.7')
    await espera(1200) // o persister grava com no máximo 1 s de atraso
    expect(armazenamento.dados.size, 'nada foi gravado').toBe(1)
    await app1.fechar()

    vi.restoreAllMocks()
    vi.spyOn(globalThis, 'fetch').mockRejectedValue(new TypeError('Failed to fetch')) // PC fora do ar
    const app2 = await abrirApp(armazenamento)
    await espera(100)
    expect(app2.div.textContent).toContain('fitness 23.7')
  })

  it('PC cai com o app aberto: os dados guardados não são apagados', async () => {
    salvarToken('x')
    const armazenamento = memoria()
    const carga = { hoje: { dia: '2026-11-09', carga: 0, fitness: 31.2, fadiga: 10.4, forma: 12.3 },
      ha_7_dias: null, ha_28_dias: null, carga_7_dias: 0, fc_max_usada: 214, fc_max_origem: 'estimada' }
    let pcLigado = true
    vi.spyOn(globalThis, 'fetch').mockImplementation(async () => {
      if (!pcLigado) throw new TypeError('Failed to fetch')
      return new Response(JSON.stringify(carga), { status: 200 })
    })
    const app1 = await abrirApp(armazenamento)
    await espera(1200)
    expect(app1.div.textContent).toContain('fitness 31.2')

    pcLigado = false // fecharam o Treino no PC; o usuário volta para o app e ele tenta atualizar
    await act(async () => { window.dispatchEvent(new Event('focus')); document.dispatchEvent(new Event('visibilitychange')) })
    await act(async () => { await new Promise((r) => setTimeout(r, 50)) })
    const { focusManager } = await import('@tanstack/react-query')
    await act(async () => { focusManager.setFocused(false); focusManager.setFocused(true) })
    await espera(1300) // falha da busca + nova gravação
    expect(app1.div.textContent).toContain('fitness 31.2')
    await app1.fechar()

    const app2 = await abrirApp(armazenamento)
    await espera(100)
    expect(app2.div.textContent).toContain('fitness 31.2')
  })
})
