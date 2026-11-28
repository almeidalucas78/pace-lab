// Cliente da API. No navegador, o login fica em cookies HttpOnly que o JavaScript não lê (ADRs 0015 e 0017):
// aqui só guardamos quem entrou, para a tela, e renovamos a sessão quando o acesso de 15 min vence.
// No app Android (ADR 0013) o painel roda em https://localhost e manda o token de acesso no cabeçalho; os tokens
// ficam no cofre do Android (cofre.ts) e numa cópia em memória, e a renovação manda o token de renovação no corpo.

import { ehApp } from '../plataforma'
import { cofre } from './cofre'
import type { Usuario } from './tipos'

const CHAVE_TOKEN_ANTIGO = 'pace-lab.token' // API_TOKEN do .env, de antes das contas
const CHAVE_COFRE = 'tokens'
const CHAVE_SERVIDOR = 'pace-lab.servidor'

export class ErroApi extends Error {
  status: number
  constructor(status: number, mensagem: string) {
    super(mensagem)
    this.status = status
  }
}

// ---------- tokens do app ----------

export interface Tokens {
  acesso: string
  renovacao: string | null
  expira?: number // ms desde a época; acesso vence em 15 min
}

let tokens: Tokens | null = null

/** Abertura do app: lê os tokens do cofre (antes de desenhar a tela) e apaga o token antigo do localStorage. */
export async function carregarTokens(): Promise<void> {
  try {
    localStorage.removeItem(CHAVE_TOKEN_ANTIGO)
  } catch {
    // sem armazenamento
  }
  if (!ehApp()) return
  try {
    const { valor } = await cofre.ler({ chave: CHAVE_COFRE })
    tokens = valor ? (JSON.parse(valor) as Tokens) : null
  } catch {
    tokens = null // cofre ilegível (chave do Keystore perdida): pede login de novo
  }
}

/** Guarda (ou apaga, com null) os tokens do app: memória na hora, cofre em seguida. */
export function salvarTokens(t: Tokens | null): void {
  tokens = t
  const gravacao = t ? cofre.gravar({ chave: CHAVE_COFRE, valor: JSON.stringify(t) }) : cofre.apagar({ chave: CHAVE_COFRE })
  gravacao.catch(() => {
    // sem cofre (navegador, testes): vale até fechar o app
  })
  window.dispatchEvent(new Event('pace-lab:token'))
}

/** Token de acesso do app (null fora do app ou sem login). */
export function lerToken(): string | null {
  return tokens?.acesso ?? null
}

/** Atalho para testes e chamadas antigas: só o acesso, sem renovação. */
export function salvarToken(token: string | null): void {
  salvarTokens(token ? { acesso: token, renovacao: null } : null)
}

/** Converte a resposta de login ou de renovação do servidor (cliente "app"). */
export function tokensDaResposta(r: { acesso: string; renovacao: string; acesso_expira?: string }): Tokens {
  const expira = r.acesso_expira ? Date.parse(r.acesso_expira) : NaN
  return { acesso: r.acesso, renovacao: r.renovacao, ...(Number.isFinite(expira) ? { expira } : {}) }
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

/** No app valem os tokens do cofre; no navegador, a marca de quem entrou. */
export const entrou = (): boolean => (ehApp() ? tokens !== null : lerSessao() !== null)

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
const SEM_RENOVAR = new Set(['/auth/entrar', '/auth/cadastro', '/auth/renovar', '/auth/app/trocar'])

type Renovacao = 'ok' | 'expirou' | 'sem-rede'
let renovando: Promise<Renovacao> | null = null

/**
 * Troca a renovação por um acesso novo: cookie no navegador; no app, o token de renovação no corpo (o servidor
 * devolve um par novo, e o antigo deixa de valer). Chamadas simultâneas esperam a mesma renovação.
 */
export function renovarSessao(): Promise<Renovacao> {
  renovando ??= (ehApp() ? renovarApp() : renovarNavegador()).finally(() => { renovando = null })
  return renovando
}

function renovarNavegador(): Promise<Renovacao> {
  return fetch('/api/auth/renovar', { method: 'POST', credentials: 'same-origin' })
    .then((r): Renovacao => (r.ok ? 'ok' : r.status === 401 || r.status === 403 ? 'expirou' : 'sem-rede'))
    .catch((): Renovacao => 'sem-rede')
}

async function renovarApp(): Promise<Renovacao> {
  const renovacao = tokens?.renovacao
  if (!renovacao) return 'expirou'
  try {
    const r = await fetch(`${baseApi()}/api/auth/renovar`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ renovacao }),
    })
    if (r.status === 401 || r.status === 403) return 'expirou'
    if (!r.ok) return 'sem-rede'
    salvarTokens(tokensDaResposta(await r.json()))
    return 'ok'
  } catch {
    return 'sem-rede'
  }
}

/** Acesso do app válido por mais um minuto, renovando antes se preciso (para downloads feitos pelo Android). */
export async function acessoFresco(): Promise<string> {
  if (tokens?.expira !== undefined && tokens.expira - Date.now() < 60_000) await renovarSessao()
  return lerToken() ?? ''
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
    if (resp.status === 401 && !SEM_RENOVAR.has(caminho) && (!ehApp() || tokens?.renovacao)) {
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
    // sessão vencida e sem renovação possível: volta para a tela de entrar
    if (!SEM_RENOVAR.has(caminho)) {
      if (ehApp()) salvarTokens(null)
      salvarSessao(null)
    }
  }
  if (!resp.ok) throw new ErroApi(resp.status, await mensagemDe(resp))
  return (await resp.json()) as T
}
