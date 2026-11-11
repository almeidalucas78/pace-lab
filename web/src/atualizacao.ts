// Atualização do app Android pelo próprio app (fase 7, etapa 4b). O PC publica o APK com
// `treino publicar-app`; o app compara a versão dele com /api/app/versao e, se houver nova, baixa
// e chama o instalador do Android pelo plugin próprio (android/.../AtualizacaoPlugin.kt).

import { App as AppNativo } from '@capacitor/app'
import { registerPlugin, type PluginListenerHandle } from '@capacitor/core'
import { api, baseApi, lerToken } from './api/cliente'

export interface VersaoPublicada {
  codigo: number | null
  nome?: string
  tamanho?: number
  sha256?: string
  publicado_em?: string
}

export type EventoInstalacao = { status: 'confirmar' | 'instalado' | 'falhou'; mensagem?: string }

export interface PluginAtualizacao {
  podeInstalar(): Promise<{ permitido: boolean }>
  abrirPermissao(): Promise<void>
  instalar(opcoes: { url: string; token: string; sha256?: string }): Promise<void>
  addListener(evento: 'progresso', f: (e: { pct: number }) => void): Promise<PluginListenerHandle>
  addListener(evento: 'instalacao', f: (e: EventoInstalacao) => void): Promise<PluginListenerHandle>
}

export const pluginAtualizacao = registerPlugin<PluginAtualizacao>('Atualizacao')

/** versionCode do app instalado (no Android, `build` do @capacitor/app é o versionCode). */
export async function versaoInstalada(): Promise<number> {
  return Number((await AppNativo.getInfo()).build)
}

/** Versão publicada no PC, se for mais nova que a instalada; senão null. */
export async function procurarAtualizacao(instalada: number): Promise<VersaoPublicada | null> {
  const v = await api<VersaoPublicada>('/app/versao')
  return v.codigo != null && v.codigo > instalada ? v : null
}

export function urlDoApk(): string {
  return `${baseApi()}/api/app/apk`
}

export function tokenAtual(): string {
  return lerToken() ?? ''
}
