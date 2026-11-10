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

/**
 * QR code do "Conectar celular" abre o painel com `#token=...` (o fragmento não vai ao servidor).
 * Salva o token e tira da barra de endereço. Devolve true se havia token.
 */
export function lerTokenDaUrl(): boolean {
  const m = window.location.hash.match(/(?:^#|&)token=([^&]+)/)
  if (!m) return false
  salvarToken(decodeURIComponent(m[1]))
  window.history.replaceState(null, '', window.location.pathname + window.location.search)
  return true
}

// ---------- situação da conexão com o PC (ADR 0012) ----------

const CHAVE_CONTATO = 'pace-lab.ultimo-contato'

export interface Conexao {
  online: boolean
  ultimoContato: number | null // ms desde a época; última resposta do PC
}

let conexao: Conexao = { online: true, ultimoContato: lerContato() }

function lerContato(): number | null {
  try {
    const v = localStorage.getItem(CHAVE_CONTATO)
    return v ? Number(v) : null
  } catch {
    return null
  }
}

function mudarConexao(online: boolean) {
  const agora = Date.now()
  const novo = { online, ultimoContato: online ? agora : conexao.ultimoContato }
  if (online) {
    try {
      localStorage.setItem(CHAVE_CONTATO, String(agora))
    } catch {
      // sem armazenamento
    }
  }
  const mudou = novo.online !== conexao.online
  conexao = novo
  if (mudou || online) window.dispatchEvent(new Event('pace-lab:conexao'))
}

export const lerConexao = (): Conexao => conexao

/** Erros do nosso backend vêm em JSON com `detail` (ex.: o chat devolve 502 quando a IA falha). */
async function doBackend(resp: Response): Promise<boolean> {
  try {
    return typeof (await resp.clone().json())?.detail === 'string'
  } catch {
    return false
  }
}

export async function api<T>(caminho: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers)
  const token = lerToken()
  if (token) headers.set('Authorization', `Bearer ${token}`)
  if (init.body && !headers.has('Content-Type')) headers.set('Content-Type', 'application/json')
  let resp: Response
  try {
    resp = await fetch(`/api${caminho}`, { ...init, headers })
  } catch {
    mudarConexao(false) // celular sem rede, Tailscale desligado ou PC desligado
    throw new ErroApi(0, 'PC fora do ar')
  }
  if (resp.status >= 502 && resp.status <= 504 && !(await doBackend(resp))) {
    // o `tailscale serve` responde 502 quando o `treino servico` está fechado
    mudarConexao(false)
    throw new ErroApi(resp.status, 'PC fora do ar')
  }
  mudarConexao(true)
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
