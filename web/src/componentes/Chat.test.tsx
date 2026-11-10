// Fluxo do chat: enviar uma mensagem e ver pergunta e resposta na tela (bug relatado no celular).
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { act } from 'react'
import { createRoot } from 'react-dom/client'
import { MemoryRouter } from 'react-router'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { salvarToken } from '../api/cliente'
import { ProvedorContexto } from '../contexto'
import { Chat } from './Chat'

;(globalThis as { IS_REACT_ACT_ENVIRONMENT?: boolean }).IS_REACT_ACT_ENVIRONMENT = true

const json = (corpo: unknown, status = 200) => new Response(JSON.stringify(corpo), { status })
const espera = (ms: number) => act(async () => { await new Promise((r) => setTimeout(r, ms)) })

let raiz: ReturnType<typeof createRoot> | null = null
afterEach(() => {
  act(() => raiz?.unmount())
  document.body.innerHTML = ''
  vi.restoreAllMocks()
})

async function montar() {
  salvarToken('teste')
  const div = document.createElement('div')
  document.body.appendChild(div)
  raiz = createRoot(div)
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  await act(async () => {
    raiz!.render(
      <QueryClientProvider client={qc}>
        <MemoryRouter initialEntries={['/chat']}><ProvedorContexto><Chat pagina /></ProvedorContexto></MemoryRouter>
      </QueryClientProvider>,
    )
  })
  return div
}

async function digitarEEnviar(div: HTMLElement, texto: string) {
  const area = div.querySelector('textarea')!
  const setter = Object.getOwnPropertyDescriptor(HTMLTextAreaElement.prototype, 'value')!.set!
  await act(async () => {
    setter.call(area, texto)
    area.dispatchEvent(new Event('input', { bubbles: true }))
  })
  const botao = [...div.querySelectorAll('button')].find((b) => b.textContent === 'Enviar')!
  await act(async () => { botao.click() })
}

describe('chat', () => {
  it('depois de enviar, a pergunta e a resposta continuam na tela', async () => {
    let conversaCarregada = false
    vi.spyOn(globalThis, 'fetch').mockImplementation(async (url, init) => {
      const u = String(url)
      if (u.endsWith('/api/chat') && init?.method === 'POST') {
        await new Promise((r) => setTimeout(r, 30))
        return json({ conversa_id: 7, provedor: 'claude', resposta: 'Bom treino!', ferramentas: ['ultimo_treino'] })
      }
      if (u.endsWith('/api/chat/conversas/7')) {
        await new Promise((r) => setTimeout(r, 200)) // rede lenta (celular pelo Tailscale)
        conversaCarregada = true
        return json({ id: 7, titulo: 'como foi?', provedor: 'claude', atualizada: '', criada: '', mensagens: [
          { papel: 'user', texto: 'como foi?', quando: '', ferramentas: null },
          { papel: 'assistant', texto: 'Bom treino!', quando: '', ferramentas: ['ultimo_treino'] },
        ] })
      }
      if (u.endsWith('/api/chat/conversas')) return json([])
      return json({}, 404)
    })
    const div = await montar()
    await digitarEEnviar(div, 'como foi?')
    expect(div.textContent).toContain('como foi?')
    expect(div.textContent).toContain('pensando')

    // logo depois da resposta, antes da conversa carregar do servidor: não pode ficar vazio
    await espera(80)
    expect(conversaCarregada).toBe(false)
    expect(div.textContent).toContain('como foi?')
    expect(div.textContent).toContain('Bom treino!')

    await espera(300)
    expect(conversaCarregada).toBe(true)
    expect(div.textContent).toContain('Bom treino!')
    expect(div.textContent).toContain('último treino')
  })
})

describe('chat com conversa existente', () => {
  it('enviar numa conversa já aberta não derruba a tela', async () => {
    const erros: unknown[] = []
    const ouvinte = (e: ErrorEvent) => erros.push(e.error)
    window.addEventListener('error', ouvinte)
    vi.spyOn(console, 'error').mockImplementation((...a) => erros.push(a))
    // como o backend real: a conversa guardada passa a ter a pergunta e a resposta novas
    const gravadas: unknown[] = [
      { papel: 'user', texto: 'veja meus treinos', quando: '', ferramentas: null },
      { papel: 'assistant', texto: '**Resumo**\n\n| a | b |\n|---|---|\n| 1 | 2 |\n\n- item', quando: '', ferramentas: ['listar_treinos'] },
    ]
    vi.spyOn(globalThis, 'fetch').mockImplementation(async (url, init) => {
      const u = String(url)
      if (u.endsWith('/api/chat') && init?.method === 'POST') {
        await new Promise((r) => setTimeout(r, 100))
        gravadas.push({ papel: 'user', texto: 'e agora?', quando: '', ferramentas: null },
                      { papel: 'assistant', texto: 'Segunda resposta', quando: '', ferramentas: [] })
        return json({ conversa_id: 7, provedor: 'claude', resposta: 'Segunda resposta', ferramentas: [] })
      }
      if (u.endsWith('/api/chat/conversas/7')) return json({ id: 7, titulo: 'veja meus treinos', provedor: 'claude',
        atualizada: '', criada: '', mensagens: [...gravadas] })
      if (u.endsWith('/api/chat/conversas')) return json([{ id: 7, titulo: 'veja meus treinos', provedor: 'claude', atualizada: '' }])
      return json({}, 404)
    })
    const div = await montar()
    await espera(50)
    const select = div.querySelector('select')!
    await act(async () => {
      select.value = '7'
      select.dispatchEvent(new Event('change', { bubbles: true }))
    })
    await espera(50)
    expect(div.textContent).toContain('veja meus treinos')
    await digitarEEnviar(div, 'e agora?')
    await espera(20)
    expect(div.textContent).toContain('e agora?')
    await espera(200)
    expect(div.textContent).toContain('Segunda resposta')
    window.removeEventListener('error', ouvinte)
    expect(erros.filter((e) => String(e).toLowerCase().includes('error'))).toEqual([])
  })
})

describe('chat no Chrome', () => {
  it('scrollIntoView que devolve Promise (Chrome) não derruba o chat ao enviar', async () => {
    const original = Element.prototype.scrollIntoView
    Element.prototype.scrollIntoView = function () { return Promise.resolve() } as unknown as typeof original
    const erros: unknown[] = []
    vi.spyOn(console, 'error').mockImplementation((...a) => erros.push(a))
    vi.spyOn(globalThis, 'fetch').mockImplementation(async (url, init) => {
      const u = String(url)
      if (u.endsWith('/api/chat') && init?.method === 'POST') {
        await new Promise((r) => setTimeout(r, 30))
        return json({ conversa_id: 3, provedor: 'claude', resposta: 'Resposta ok', ferramentas: [] })
      }
      if (u.endsWith('/api/chat/conversas/3')) return json({ id: 3, titulo: 'oi', provedor: 'claude', atualizada: '', criada: '',
        mensagens: [{ papel: 'user', texto: 'oi', quando: '', ferramentas: null },
                    { papel: 'assistant', texto: 'Resposta ok', quando: '', ferramentas: [] }] })
      if (u.endsWith('/api/chat/conversas')) return json([])
      return json({}, 404)
    })
    try {
      const div = await montar()
      await digitarEEnviar(div, 'oi')
      await espera(150)
      expect(div.textContent).toContain('Resposta ok')
      expect(erros.map(String).join(' ')).not.toContain('is not a function')
    } finally {
      Element.prototype.scrollIntoView = original
    }
  })
})
