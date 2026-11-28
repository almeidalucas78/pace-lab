// Painel dentro do app Android (ADR 0013): endereço do servidor, tokens no cofre e login pelo navegador (fase 9, etapa 8).
import { QueryClient } from '@tanstack/react-query'
import { act } from 'react'
import { createRoot } from 'react-dom/client'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { ConectarApp, desafioPendente, guardarDesafioDaUrl } from '../paginas/ConectarApp'
import { ehApp } from '../plataforma'
import {
  acessoFresco, api, baseApi, carregarTokens, entrou, lerSessao, lerToken, salvarServidor, salvarSessao, salvarTokens,
  salvarToken,
} from './cliente'
import { cofre } from './cofre'
import { codigoDoLink, concluirLoginApp, desafioDe, EVENTO_ERRO, iniciarLoginApp } from './loginApp'

vi.mock('../plataforma', () => ({ ehApp: vi.fn(() => false) }))
vi.mock('./cofre', () => ({
  cofre: { ler: vi.fn(async () => ({ valor: null })), gravar: vi.fn(async () => {}), apagar: vi.fn(async () => {}) },
}))
vi.mock('@capacitor/browser', () => ({ Browser: { open: vi.fn(async () => {}), close: vi.fn(async () => {}) } }))
;(globalThis as { IS_REACT_ACT_ENVIRONMENT?: boolean }).IS_REACT_ACT_ENVIRONMENT = true
const comoApp = (sim: boolean) => vi.mocked(ehApp).mockReturnValue(sim)
const SERVIDOR = 'https://pacelab.rede.ts.net'
const json = (corpo: unknown, status = 200) => new Response(JSON.stringify(corpo), { status })

beforeEach(() => {
  vi.mocked(cofre.gravar).mockClear()
  vi.mocked(cofre.apagar).mockClear()
})

afterEach(() => {
  vi.restoreAllMocks()
  comoApp(false)
  salvarServidor(null)
  salvarTokens(null)
  salvarSessao(null)
  localStorage.clear()
  sessionStorage.clear()
  document.body.innerHTML = ''
})

describe('app Android: chamadas à API', () => {
  it('no navegador a API é o próprio site; no app, o endereço do servidor', async () => {
    salvarServidor(`${SERVIDOR}/`)
    expect(baseApi()).toBe('')
    comoApp(true)
    expect(baseApi()).toBe(SERVIDOR)
    salvarToken('t')
    const f = vi.spyOn(globalThis, 'fetch').mockResolvedValue(json({}))
    await api('/perfil')
    expect(f.mock.calls[0][0]).toBe(`${SERVIDOR}/api/perfil`)
    expect(new Headers(f.mock.calls[0][1]?.headers).get('Authorization')).toBe('Bearer t')
  })

  it('acesso vencido: renova com o token de renovação no corpo, guarda o par novo e repete', async () => {
    comoApp(true)
    salvarServidor(SERVIDOR)
    salvarTokens({ acesso: 'pla_1', renovacao: 'plr_1' })
    const f = vi.spyOn(globalThis, 'fetch')
      .mockResolvedValueOnce(json({ detail: 'sessão expirada' }, 401))
      .mockResolvedValueOnce(json({ acesso: 'pla_2', renovacao: 'plr_2', acesso_expira: '2026-11-28T12:15:00+00:00' }))
      .mockResolvedValueOnce(json({ ok: true }))
    expect(await api('/perfil')).toEqual({ ok: true })
    expect(f.mock.calls[1][0]).toBe(`${SERVIDOR}/api/auth/renovar`)
    expect(JSON.parse(String(f.mock.calls[1][1]?.body))).toEqual({ renovacao: 'plr_1' })
    expect(new Headers(f.mock.calls[2][1]?.headers).get('Authorization')).toBe('Bearer pla_2')
    expect(lerToken()).toBe('pla_2')
    const gravado = JSON.parse(vi.mocked(cofre.gravar).mock.lastCall![0].valor)
    expect(gravado).toMatchObject({ acesso: 'pla_2', renovacao: 'plr_2', expira: Date.parse('2026-11-28T12:15:00Z') })
  })

  it('renovação recusada: apaga os tokens do app e do cofre e volta para a tela de entrar', async () => {
    comoApp(true)
    salvarServidor(SERVIDOR)
    salvarTokens({ acesso: 'pla_1', renovacao: 'plr_1' })
    salvarSessao({ id: 1, email: 'bia@exemplo.com', nome: null, google: false, senha: true })
    vi.spyOn(globalThis, 'fetch')
      .mockResolvedValueOnce(json({ detail: 'sessão expirada' }, 401))
      .mockResolvedValueOnce(json({ detail: 'sessão expirada' }, 401))
      .mockResolvedValueOnce(json({ detail: 'sessão expirada' }, 401))
    await expect(api('/perfil')).rejects.toMatchObject({ status: 401 })
    expect(entrou()).toBe(false)
    expect(lerSessao()).toBeNull()
    expect(cofre.apagar).toHaveBeenCalledWith({ chave: 'tokens' })
  })

  it('sem token de renovação, 401 apaga o acesso sem tentar renovar', async () => {
    comoApp(true)
    salvarServidor(SERVIDOR)
    salvarToken('t')
    const f = vi.spyOn(globalThis, 'fetch').mockResolvedValue(json({ detail: 'token inválido' }, 401))
    await expect(api('/perfil')).rejects.toMatchObject({ status: 401 })
    expect(f).toHaveBeenCalledTimes(1)
    expect(lerToken()).toBeNull()
  })

  it('abertura do app lê os tokens do cofre e descarta o token antigo do localStorage', async () => {
    localStorage.setItem('pace-lab.token', 'api-token-antigo')
    comoApp(true)
    vi.mocked(cofre.ler).mockResolvedValueOnce({ valor: JSON.stringify({ acesso: 'pla_9', renovacao: 'plr_9' }) })
    await carregarTokens()
    expect(lerToken()).toBe('pla_9')
    expect(entrou()).toBe(true)
    expect(localStorage.getItem('pace-lab.token')).toBeNull()
    vi.mocked(cofre.ler).mockRejectedValueOnce(new Error('chave do Keystore perdida'))
    await carregarTokens()
    expect(entrou()).toBe(false)
  })

  it('o download do APK recebe um acesso renovado quando o atual está no fim', async () => {
    comoApp(true)
    salvarServidor(SERVIDOR)
    salvarTokens({ acesso: 'pla_1', renovacao: 'plr_1', expira: Date.now() + 10_000 })
    vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce(json({ acesso: 'pla_2', renovacao: 'plr_2' }))
    expect(await acessoFresco()).toBe('pla_2')
    salvarTokens({ acesso: 'pla_3', renovacao: 'plr_3', expira: Date.now() + 600_000 })
    expect(await acessoFresco()).toBe('pla_3')
  })
})

describe('app Android: login pelo navegador do celular', () => {
  it('Entrar abre a tela do servidor com o desafio do verificador guardado no app', async () => {
    comoApp(true)
    const { Browser } = await import('@capacitor/browser')
    await iniciarLoginApp(`${SERVIDOR}/`)
    const url = new URL(vi.mocked(Browser.open).mock.lastCall![0].url)
    expect(`${url.origin}${url.pathname}`).toBe(`${SERVIDOR}/entrar-app`)
    const verificador = localStorage.getItem('pace-lab.login-app')!
    expect(verificador).toMatch(/^[A-Za-z0-9_-]{43}$/)
    expect(url.searchParams.get('desafio')).toBe(await desafioDe(verificador))
  })

  it('desafio segue o exemplo da RFC 7636', async () => {
    expect(await desafioDe('dBjftJeZ4CVP-mB92K27uhbUJU1p1r_wW1gFWFOEjXk')).toBe('E9Melhoa2OwvFrEMTJguCHaoeK1t8URWbuGJSstw-cM')
  })

  it('só links pacelab://entrou com código são de login', () => {
    expect(codigoDoLink('pacelab://entrou?codigo=abc%2F1')).toBe('abc/1')
    expect(codigoDoLink('pacelab://entrou')).toBeNull()
    expect(codigoDoLink('pacelab://conectar?servidor=https://a&token=x')).toBeNull()
    expect(codigoDoLink('https://pacelab.rede.ts.net/?codigo=x')).toBeNull()
    expect(codigoDoLink('isso não é url')).toBeNull()
  })

  it('volta do navegador: troca código e verificador pelos tokens e entra', async () => {
    comoApp(true)
    salvarServidor(SERVIDOR)
    localStorage.setItem('pace-lab.login-app', 'verificador-guardado')
    const usuario = { id: 7, email: 'bia@exemplo.com', nome: 'Bia', google: false, senha: true }
    const f = vi.spyOn(globalThis, 'fetch').mockResolvedValue(json({ usuario, acesso: 'pla_1', renovacao: 'plr_1' }))
    expect(await concluirLoginApp('pacelab://entrou?codigo=c1', new QueryClient())).toBe(true)
    expect(f.mock.calls[0][0]).toBe(`${SERVIDOR}/api/auth/app/trocar`)
    expect(JSON.parse(String(f.mock.calls[0][1]?.body))).toEqual({ codigo: 'c1', verificador: 'verificador-guardado' })
    expect(lerToken()).toBe('pla_1')
    expect(lerSessao()?.email).toBe('bia@exemplo.com')
    expect(localStorage.getItem('pace-lab.login-app')).toBeNull() // verificador é de uso único
  })

  it('código recusado ou login que não começou no app vira mensagem na tela de entrar', async () => {
    comoApp(true)
    salvarServidor(SERVIDOR)
    const erros: string[] = []
    const ouvir = (e: Event) => { erros.push(String((e as CustomEvent).detail)) }
    window.addEventListener(EVENTO_ERRO, ouvir)
    await concluirLoginApp('pacelab://entrou?codigo=c1', new QueryClient())
    localStorage.setItem('pace-lab.login-app', 'v')
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(json({ detail: 'código de login expirado ou inválido' }, 400))
    await concluirLoginApp('pacelab://entrou?codigo=c2', new QueryClient())
    window.removeEventListener(EVENTO_ERRO, ouvir)
    expect(erros).toEqual(['Este login não começou neste app. Toque em Entrar de novo.', 'código de login expirado ou inválido'])
    expect(entrou()).toBe(false)
  })
})

describe('navegador do celular: devolver o login ao app', () => {
  const DESAFIO = 'E9Melhoa2OwvFrEMTJguCHaoeK1t8URWbuGJSstw-cM'

  it('/entrar-app guarda o desafio na aba e limpa a barra de endereço', () => {
    window.history.replaceState(null, '', `/entrar-app?desafio=${DESAFIO}`)
    guardarDesafioDaUrl()
    expect(window.location.pathname + window.location.search).toBe('/')
    expect(desafioPendente()).toBe(DESAFIO)
    window.history.replaceState(null, '', '/entrar-app?desafio=curto')
    sessionStorage.clear()
    guardarDesafioDaUrl()
    expect(desafioPendente()).toBeNull()
  })

  it('Conectar o app pede o código e volta ao app por pacelab://entrou', async () => {
    sessionStorage.setItem('pace-lab.desafio-app', DESAFIO)
    salvarSessao({ id: 7, email: 'bia@exemplo.com', nome: null, google: false, senha: true })
    const f = vi.spyOn(globalThis, 'fetch').mockResolvedValue(json({ codigo: 'c/1' }))
    const div = document.createElement('div')
    document.body.appendChild(div)
    const raiz = createRoot(div)
    await act(async () => { raiz.render(<ConectarApp desafio={DESAFIO} aoTerminar={() => {}} />) })
    expect(div.textContent).toContain('bia@exemplo.com')
    await act(async () => { div.querySelector('button')!.click() })
    expect(f.mock.calls[0][0]).toBe('/api/auth/app/codigo')
    expect(JSON.parse(String(f.mock.calls[0][1]?.body))).toEqual({ desafio: DESAFIO })
    expect(div.querySelector('a')!.getAttribute('href')).toBe('pacelab://entrou?codigo=c%2F1')
    expect(desafioPendente()).toBeNull()
    act(() => raiz.unmount())
  })
})
