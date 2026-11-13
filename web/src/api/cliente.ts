// Cliente da API: guarda o token no navegador e o envia em toda chamada (ADR 0011).
// No app Android (ADR 0013) o painel roda em https://localhost e fala com o PC pelo endereço do Tailscale.

import { ehApp } from '../plataforma'

const CHAVE_TOKEN = 'pace-lab.token'
const CHAVE_SERVIDOR = 'pace-lab.servidor'

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

/** Endereço do PC (ex.: https://pacelab.rede.ts.net). Só usado no app; no navegador a API é o próprio site. */
export function lerServidor(): string | null {
  try {
    return localStorage.getItem(CHAVE_SERVIDOR)
  } catch {
    return null
  }
}

export function salvarServidor(url: string | null): void {
  try {
    if (url) localStorage.setItem(CHAVE_SERVIDOR, url.trim().replace(/\/+$/, ''))
    else localStorage.removeItem(CHAVE_SERVIDOR)
  } catch {
    // sem armazenamento
  }
}

/** Prefixo das chamadas: vazio no navegador (mesmo site); o endereço do PC no app. */
export function baseApi(): string {
  return ehApp() ? (lerServidor() ?? '') : ''
}

/**
 * Link `pacelab://conectar?servidor=...&token=...` que abre o app (vem da página /abrir-app).
 * Guarda endereço e token. Devolve true se o link era desse tipo e válido.
 */
export function conectarPorLink(url: string): boolean {
  let u: URL
  try {
    u = new URL(url)
  } catch {
    return false
  }
  if (u.protocol !== 'pacelab:' || (u.hostname || u.pathname.replace(/^\/+/, '')) !== 'conectar') return false
  const servidor = u.searchParams.get('servidor')
  const token = u.searchParams.get('token')
  if (!servidor || !token || !servidor.startsWith('https://')) return false
  salvarServidor(servidor)
  salvarToken(token)
  return true
}

/**
 * QR code do "Conectar celular" abre o painel com `#token=...` (o fragmento não vai ao servidor).
 * Salva o token e tira da barra de endereço. Devolve true se havia token.
 * Na página /abrir-app o token é repassado ao app, então não é guardado no navegador.
 */
export function lerTokenDaUrl(): boolean {
  if (window.location.pathname === '/abrir-app') return false
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
    resp = await fetch(`${baseApi()}/api${caminho}`, { ...init, headers })
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
  const resp = await fetch(`${baseApi()}/api/perfil`, { headers: { Authorization: `Bearer ${token}` } })
  return resp.ok
}
