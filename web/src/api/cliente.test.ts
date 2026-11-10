import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { ErroApi, api, lerConexao, lerToken, lerTokenDaUrl, salvarToken } from './cliente'

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

describe('celular (fase 6)', () => {
  afterEach(() => vi.restoreAllMocks())

  it('lê o token do QR code (#token=) e limpa a barra de endereço', () => {
    salvarToken(null)
    window.history.replaceState(null, '', '/treinos#token=abc%2F123')
    expect(lerTokenDaUrl()).toBe(true)
    expect(lerToken()).toBe('abc/123')
    expect(window.location.hash).toBe('')
    expect(window.location.pathname).toBe('/treinos')
    expect(lerTokenDaUrl()).toBe(false)
  })

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
