// Cliente da API. No navegador, o login fica em cookies HttpOnly que o JavaScript não lê (ADRs 0015 e 0017):
// aqui só guardamos quem entrou, para a tela, e renovamos a sessão quando o acesso de 15 min vence.
// No app Android (ADR 0013) o painel roda em https://localhost e manda o token no cabeçalho (até a etapa 8).

import { ehApp } from '../plataforma'
import type { Usuario } from './tipos'

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

// ---------- quem entrou (navegador) ----------

const CHAVE_CONTA = 'pace-lab.conta'
const CHAVE_ULTIMA = 'pace-lab.ultima-conta'

export function lerSessao(): Usuario | null {
  try {
    const v = localStorage.getItem(CHAVE_CONTA)
    return v ? (JSON.parse(v) as Usuario) : null
  } catch {
    return null
  }
}

/** Marca (ou desmarca) quem entrou neste navegador. O login de verdade está no cookie. */
export function salvarSessao(u: Usuario | null): void {
  try {
    if (u) {
      localStorage.setItem(CHAVE_CONTA, JSON.stringify(u))
      localStorage.setItem(CHAVE_ULTIMA, String(u.id))
    } else localStorage.removeItem(CHAVE_CONTA)
  } catch {
    // sem armazenamento: vale só enquanto a aba estiver aberta
  }
  window.dispatchEvent(new Event('pace-lab:sessao'))
}

/** Id da última conta que entrou aqui, mesmo depois de a sessão vencer (para não mostrar dados de outra pessoa). */
export function ultimaConta(): number | null {
  try {
    const v = localStorage.getItem(CHAVE_ULTIMA)
    return v ? Number(v) : null
  } catch {
    return null
  }
}

/** No app vale o token; no navegador, a marca de quem entrou. */
export const entrou = (): boolean => (ehApp() ? lerToken() !== null : lerSessao() !== null)

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

async function mensagemDe(resp: Response): Promise<string> {
  try {
    const corpo = await resp.json()
    if (typeof corpo?.detail === 'string') return corpo.detail
  } catch {
    // resposta sem JSON
  }
  return `erro ${resp.status}`
}

// Rotas em que 401 é a resposta da própria tela (senha errada), não sessão vencida.
const SEM_RENOVAR = new Set(['/auth/entrar', '/auth/cadastro', '/auth/renovar'])

type Renovacao = 'ok' | 'expirou' | 'sem-rede'
let renovando: Promise<Renovacao> | null = null

/** Troca o cookie de renovação por um acesso novo. Chamadas simultâneas esperam a mesma renovação. */
export function renovarSessao(): Promise<Renovacao> {
  renovando ??= fetch('/api/auth/renovar', { method: 'POST', credentials: 'same-origin' })
    .then((r): Renovacao => (r.ok ? 'ok' : r.status === 401 || r.status === 403 ? 'expirou' : 'sem-rede'))
    .catch((): Renovacao => 'sem-rede')
    .finally(() => { renovando = null })
  return renovando
}

function buscar(caminho: string, init: RequestInit): Promise<Response> {
  const headers = new Headers(init.headers)
  const token = ehApp() ? lerToken() : null
  if (token) headers.set('Authorization', `Bearer ${token}`)
  if (typeof init.body === 'string' && !headers.has('Content-Type')) headers.set('Content-Type', 'application/json')
  return fetch(`${baseApi()}/api${caminho}`, { ...init, headers, credentials: 'same-origin' })
}

export async function api<T>(caminho: string, init: RequestInit = {}): Promise<T> {
  let resp: Response
  try {
    resp = await buscar(caminho, init)
    if (resp.status === 401 && !ehApp() && !SEM_RENOVAR.has(caminho)) {
      const r = await renovarSessao()
      if (r === 'sem-rede') throw new Error('sem rede')
      if (r === 'ok') resp = await buscar(caminho, init)
    }
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
    // sessão vencida (ou token trocado no .env, no app): volta para a tela de entrar
    if (ehApp()) salvarToken(null)
    else if (!SEM_RENOVAR.has(caminho)) salvarSessao(null)
  }
  if (!resp.ok) throw new ErroApi(resp.status, await mensagemDe(resp))
  return (await resp.json()) as T
}

/** Confere um token chamando uma rota protegida, sem apagar o salvo se estiver errado. */
export async function testarToken(token: string): Promise<boolean> {
  const resp = await fetch(`${baseApi()}/api/perfil`, { headers: { Authorization: `Bearer ${token}` } })
  return resp.ok
}
