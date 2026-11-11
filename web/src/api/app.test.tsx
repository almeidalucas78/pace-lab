// Painel dentro do app Android (ADR 0013): endereço do PC, link pacelab://conectar e página /abrir-app.
import { act } from 'react'
import { createRoot } from 'react-dom/client'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { AbrirApp } from '../paginas/AbrirApp'
import { ehApp } from '../plataforma'
import { api, baseApi, conectarPorLink, lerServidor, lerToken, lerTokenDaUrl, salvarServidor, salvarToken } from './cliente'

vi.mock('../plataforma', () => ({ ehApp: vi.fn(() => false) }))
;(globalThis as { IS_REACT_ACT_ENVIRONMENT?: boolean }).IS_REACT_ACT_ENVIRONMENT = true
const comoApp = (sim: boolean) => vi.mocked(ehApp).mockReturnValue(sim)

afterEach(() => {
  vi.restoreAllMocks()
  comoApp(false)
  salvarServidor(null)
  salvarToken(null)
  document.body.innerHTML = ''
})

describe('app Android', () => {
  it('no navegador a API é o próprio site; no app, o endereço do PC', async () => {
    salvarServidor('https://pacelab.rede.ts.net/')
    expect(baseApi()).toBe('')
    comoApp(true)
    expect(baseApi()).toBe('https://pacelab.rede.ts.net')
    salvarToken('t')
    const f = vi.spyOn(globalThis, 'fetch').mockResolvedValue(new Response('{}', { status: 200 }))
    await api('/perfil')
    expect(f.mock.calls[0][0]).toBe('https://pacelab.rede.ts.net/api/perfil')
  })

  it('link pacelab://conectar guarda endereço e token', () => {
    expect(conectarPorLink('pacelab://conectar?servidor=https%3A%2F%2Fpacelab.rede.ts.net&token=abc%2F1')).toBe(true)
    expect(lerServidor()).toBe('https://pacelab.rede.ts.net')
    expect(lerToken()).toBe('abc/1')
  })

  it('links inválidos são ignorados', () => {
    expect(conectarPorLink('https://pacelab.rede.ts.net/?token=x')).toBe(false)
    expect(conectarPorLink('pacelab://outra?servidor=https://a&token=x')).toBe(false)
    expect(conectarPorLink('pacelab://conectar?servidor=http://inseguro&token=x')).toBe(false)
    expect(conectarPorLink('pacelab://conectar?servidor=https://a')).toBe(false)
    expect(conectarPorLink('isso não é url')).toBe(false)
    expect(lerToken()).toBeNull()
  })

  it('/abrir-app repassa o token ao app e não o guarda no navegador', async () => {
    window.history.replaceState(null, '', '/abrir-app#token=abc%2F1')
    expect(lerTokenDaUrl()).toBe(false)   // não salva no navegador
    const div = document.createElement('div')
    document.body.appendChild(div)
    const raiz = createRoot(div)
    await act(async () => { raiz.render(<AbrirApp />) })
    const link = div.querySelector('a')!.getAttribute('href')!
    expect(link).toBe(`pacelab://conectar?servidor=${encodeURIComponent(window.location.origin)}&token=abc%2F1`)
    expect(window.location.hash).toBe('')
    expect(lerToken()).toBeNull()
    act(() => raiz.unmount())
  })
})
