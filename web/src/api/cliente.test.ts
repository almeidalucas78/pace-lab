import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { ErroApi, api, lerToken, salvarToken } from './cliente'

function resposta(status: number, corpo: unknown) {
  return new Response(JSON.stringify(corpo), { status, headers: { 'Content-Type': 'application/json' } })
}

describe('cliente da API', () => {
  beforeEach(() => salvarToken('abc'))
  afterEach(() => vi.restoreAllMocks())

  it('envia o token e o prefixo /api', async () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockResolvedValue(resposta(200, { ok: 1 }))
    expect(await api<{ ok: number }>('/perfil')).toEqual({ ok: 1 })
    const [url, init] = fetchMock.mock.calls[0]
    expect(url).toBe('/api/perfil')
    expect(new Headers(init?.headers).get('Authorization')).toBe('Bearer abc')
  })

  it('401 apaga o token salvo e avisa a tela', async () => {
    const ouvinte = vi.fn()
    window.addEventListener('pace-lab:token', ouvinte)
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(resposta(401, { detail: 'token inválido' }))
    await expect(api('/perfil')).rejects.toMatchObject({ status: 401 })
    expect(lerToken()).toBeNull()
    expect(ouvinte).toHaveBeenCalled()
    window.removeEventListener('pace-lab:token', ouvinte)
  })

  it('outros erros trazem a mensagem do backend', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(resposta(404, { detail: 'nenhum plano ativo' }))
    const erro = await api<unknown>('/planos/ativo').catch((e: unknown) => e)
    if (!(erro instanceof ErroApi)) throw new Error('esperava ErroApi')
    expect(erro).toBeInstanceOf(ErroApi)
    expect(erro.message).toBe('nenhum plano ativo')
    expect(lerToken()).toBe('abc')
  })

  it('manda JSON quando há corpo', async () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockResolvedValue(resposta(200, {}))
    await api('/chat', { method: 'POST', body: JSON.stringify({ mensagem: 'oi' }) })
    expect(new Headers(fetchMock.mock.calls[0][1]?.headers).get('Content-Type')).toBe('application/json')
  })
})
