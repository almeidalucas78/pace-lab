// Cliente da API: guarda o token no navegador e o envia em toda chamada (ADR 0011).

const CHAVE_TOKEN = 'pace-lab.token'

export class ErroApi extends Error {
  status: number
  constructor(status: number, mensagem: string) {
    super(mensagem)
    this.status = status
  }
}

export function lerToken(): string | null {
  try {
    return localStorage.getItem(CHAVE_TOKEN)
  } catch {
    return null
  }
}

export function salvarToken(token: string | null): void {
  try {
    if (token) localStorage.setItem(CHAVE_TOKEN, token)
    else localStorage.removeItem(CHAVE_TOKEN)
  } catch {
    // navegador sem armazenamento: o token vale só nesta aba
  }
  window.dispatchEvent(new Event('pace-lab:token'))
}

export async function api<T>(caminho: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers)
  const token = lerToken()
  if (token) headers.set('Authorization', `Bearer ${token}`)
  if (init.body && !headers.has('Content-Type')) headers.set('Content-Type', 'application/json')
  const resp = await fetch(`/api${caminho}`, { ...init, headers })
  if (resp.status === 401) {
    salvarToken(null) // token errado ou trocado no .env: volta para a tela do token
    throw new ErroApi(401, 'token inválido')
  }
  if (!resp.ok) {
    let mensagem = `erro ${resp.status}`
    try {
      const corpo = await resp.json()
      if (typeof corpo?.detail === 'string') mensagem = corpo.detail
    } catch {
      // resposta sem JSON
    }
    throw new ErroApi(resp.status, mensagem)
  }
  return (await resp.json()) as T
}

/** Confere um token chamando uma rota protegida, sem apagar o salvo se estiver errado. */
export async function testarToken(token: string): Promise<boolean> {
  const resp = await fetch('/api/perfil', { headers: { Authorization: `Bearer ${token}` } })
  return resp.ok
}
