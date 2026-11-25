import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { ErroApi, api, entrou, lerConexao, lerSessao, salvarSessao, salvarToken, ultimaConta } from './cliente'

function resposta(status: number, corpo: unknown) {
  return new Response(JSON.stringify(corpo), { status, headers: { 'Content-Type': 'application/json' } })
}

const USUARIO = { id: 7, email: 'bia@exemplo.com', nome: null, google: false, senha: true }

describe('cliente da API no navegador (login em cookie)', () => {
  beforeEach(() => salvarSessao(USUARIO))
  afterEach(() => vi.restoreAllMocks())

  it('manda o cookie (same-origin) e nenhum token no cabeçalho', async () => {
    salvarToken('antigo') // token que sobrou de antes das contas: o navegador não usa mais
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockResolvedValue(resposta(200, { ok: 1 }))
    expect(await api<{ ok: number }>('/perfil')).toEqual({ ok: 1 })
    const [url, init] = fetchMock.mock.calls[0]
    expect(url).toBe('/api/perfil')
    expect(init?.credentials).toBe('same-origin')
    expect(new Headers(init?.headers).get('Authorization')).toBeNull()
    salvarToken(null)
  })

  it('acesso vencido: renova uma vez e repete a chamada', async () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch')
      .mockResolvedValueOnce(resposta(401, { detail: 'sessão expirada' }))
      .mockResolvedValueOnce(resposta(200, { acesso_expira: 'x' }))
      .mockResolvedValueOnce(resposta(200, { ok: 2 }))
    expect(await api('/perfil')).toEqual({ ok: 2 })
    expect(fetchMock.mock.calls.map((c) => String(c[0]))).toEqual(['/api/perfil', '/api/auth/renovar', '/api/perfil'])
    expect(fetchMock.mock.calls[1][1]?.method).toBe('POST')
    expect(lerSessao()).toEqual(USUARIO)
  })

  it('várias chamadas vencidas ao mesmo tempo esperam uma única renovação', async () => {
    let renovacoes = 0
    let primeira = true
    vi.spyOn(globalThis, 'fetch').mockImplementation(async (url) => {
      if (String(url).endsWith('/auth/renovar')) {
        renovacoes++
        await new Promise((r) => setTimeout(r, 20))
        primeira = false
        return resposta(200, {})
      }
      return primeira ? resposta(401, {}) : resposta(200, { ok: 1 })
    })
    await Promise.all([api('/perfil'), api('/load'), api('/weeks')])
    expect(renovacoes).toBe(1)
  })

  it('renovação recusada: sai da conta e avisa a tela', async () => {
    const ouvinte = vi.fn()
    window.addEventListener('pace-lab:sessao', ouvinte)
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(resposta(401, { detail: 'sessão expirada; faça login de novo' }))
    await expect(api('/perfil')).rejects.toMatchObject({ status: 401, message: 'sessão expirada; faça login de novo' })
    expect(lerSessao()).toBeNull()
    expect(entrou()).toBe(false)
    expect(ultimaConta()).toBe(7) // lembra quem era, para apagar os dados se outra pessoa entrar
    expect(ouvinte).toHaveBeenCalled()
    window.removeEventListener('pace-lab:sessao', ouvinte)
  })

  it('sem rede na hora de renovar: continua logado e marca fora do ar', async () => {
    vi.spyOn(globalThis, 'fetch')
      .mockResolvedValueOnce(resposta(401, {}))
      .mockRejectedValueOnce(new TypeError('Failed to fetch'))
    await expect(api('/perfil')).rejects.toMatchObject({ status: 0 })
    expect(lerSessao()).toEqual(USUARIO)
    expect(lerConexao().online).toBe(false)
    vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce(resposta(200, {}))
    await api('/perfil') // volta ao normal
  })

  it('senha errada no entrar não tenta renovar nem mexe na sessão', async () => {
    salvarSessao(null)
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockResolvedValue(resposta(401, { detail: 'e-mail ou senha errados' }))
    await expect(api('/auth/entrar', { method: 'POST', body: '{}' })).rejects.toMatchObject({ message: 'e-mail ou senha errados' })
    expect(fetchMock).toHaveBeenCalledTimes(1)
  })

  it('outros erros trazem a mensagem do backend', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(resposta(404, { detail: 'nenhum plano ativo' }))
    const erro = await api<unknown>('/planos/ativo').catch((e: unknown) => e)
    if (!(erro instanceof ErroApi)) throw new Error('esperava ErroApi')
    expect(erro.message).toBe('nenhum plano ativo')
    expect(lerSessao()).toEqual(USUARIO)
  })

  it('manda JSON quando o corpo é texto; arquivo vai com o tipo dele', async () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockImplementation(async () => resposta(200, {}))
    await api('/chat', { method: 'POST', body: JSON.stringify({ mensagem: 'oi' }) })
    expect(new Headers(fetchMock.mock.calls[0][1]?.headers).get('Content-Type')).toBe('application/json')
    await api('/importar/strava', { method: 'POST', body: new Blob(['PK']), headers: { 'Content-Type': 'application/zip' } })
    expect(new Headers(fetchMock.mock.calls[1][1]?.headers).get('Content-Type')).toBe('application/zip')
  })
})

describe('celular (fase 6)', () => {
  afterEach(() => vi.restoreAllMocks())

  it('sem resposta do PC marca fora do ar; resposta volta ao normal', async () => {
    const ouvinte = vi.fn()
    window.addEventListener('pace-lab:conexao', ouvinte)
    vi.spyOn(globalThis, 'fetch').mockRejectedValueOnce(new TypeError('Failed to fetch'))
    await expect(api('/perfil')).rejects.toMatchObject({ status: 0, message: 'PC fora do ar' })
    expect(lerConexao().online).toBe(false)

    vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce(new Response('', { status: 502 }))
    await expect(api('/perfil')).rejects.toMatchObject({ message: 'PC fora do ar' })
    expect(lerConexao().online).toBe(false)

    vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce(resposta(200, {}))
    await api('/perfil')
    expect(lerConexao()).toMatchObject({ online: true })
    expect(lerConexao().ultimoContato).toBeGreaterThan(0)
    expect(ouvinte).toHaveBeenCalled()
    window.removeEventListener('pace-lab:conexao', ouvinte)
  })

  it('erro 502 do nosso backend (ex.: a IA falhou) não é PC fora do ar', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce(resposta(502, { detail: 'Gemini: 503 high demand' }))
    await expect(api('/chat')).rejects.toMatchObject({ status: 502, message: 'Gemini: 503 high demand' })
    expect(lerConexao().online).toBe(true)
  })
})
