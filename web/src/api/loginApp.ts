// Login do app Android (fase 9, etapa 8; ADR 0015): a tela de entrar é a do servidor, aberta no navegador do
// celular (Custom Tabs). Depois de entrar, o navegador devolve ao app um código de uso único por pacelab://entrou,
// e o app troca o código pelos tokens com o verificador do PKCE, que nunca saiu do app.

import { Browser } from '@capacitor/browser'
import type { QueryClient } from '@tanstack/react-query'
import { api, baseApi, salvarServidor, salvarTokens, tokensDaResposta } from './cliente'
import { entrouComo } from './sessao'
import type { Usuario } from './tipos'

const CHAVE_VERIFICADOR = 'pace-lab.login-app'
export const EVENTO_ERRO = 'pace-lab:erro-login'

function base64url(bytes: Uint8Array): string {
  let texto = ''
  for (const b of bytes) texto += String.fromCharCode(b)
  return btoa(texto).replaceAll('+', '-').replaceAll('/', '_').replace(/=+$/, '')
}

/** S256 do PKCE (RFC 7636): base64url do SHA-256 do verificador. */
export async function desafioDe(verificador: string): Promise<string> {
  const hash = await crypto.subtle.digest('SHA-256', new TextEncoder().encode(verificador))
  return base64url(new Uint8Array(hash))
}

/** Guarda o endereço, cria o verificador e abre a tela de entrar do servidor no navegador do celular. */
export async function iniciarLoginApp(servidor: string): Promise<void> {
  salvarServidor(servidor)
  const verificador = base64url(crypto.getRandomValues(new Uint8Array(32)))
  localStorage.setItem(CHAVE_VERIFICADOR, verificador)
  await Browser.open({ url: `${baseApi()}/entrar-app?desafio=${await desafioDe(verificador)}` })
}

/** Código de `pacelab://entrou?codigo=...`; null se o link é de outro tipo. */
export function codigoDoLink(url: string): string | null {
  let u: URL
  try {
    u = new URL(url)
  } catch {
    return null
  }
  if (u.protocol !== 'pacelab:' || (u.hostname || u.pathname.replace(/^\/+/, '')) !== 'entrou') return null
  return u.searchParams.get('codigo') || null
}

interface RespostaTroca { usuario: Usuario; acesso: string; renovacao: string; acesso_expira?: string }

/**
 * Volta do navegador: troca o código pelos tokens e entra. Devolve false se o link não era de login.
 * Erros vão para a tela de entrar pelo evento EVENTO_ERRO.
 */
export async function concluirLoginApp(url: string, qc: QueryClient): Promise<boolean> {
  const codigo = codigoDoLink(url)
  if (!codigo) return false
  Browser.close().catch(() => {}) // no Android a aba some sozinha quando o app volta; aqui só por garantia
  let verificador: string | null = null
  try {
    verificador = localStorage.getItem(CHAVE_VERIFICADOR)
    localStorage.removeItem(CHAVE_VERIFICADOR)
  } catch {
    // sem armazenamento
  }
  try {
    if (!verificador) throw new Error('Este login não começou neste app. Toque em Entrar de novo.')
    const r = await api<RespostaTroca>('/auth/app/trocar', {
      method: 'POST',
      body: JSON.stringify({ codigo, verificador }),
    })
    await entrouComo(qc, r.usuario) // apaga dados de outra conta antes de mostrar o painel
    salvarTokens(tokensDaResposta(r))
  } catch (e) {
    const mensagem = e instanceof Error ? e.message : String(e)
    window.dispatchEvent(new CustomEvent(EVENTO_ERRO, { detail: mensagem }))
  }
  return true
}
