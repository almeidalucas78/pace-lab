// Fontes de treinos no celular (ADR 0013). Hoje só o Samsung Health (plugin próprio em Kotlin,
// web/android/app/src/main/java/app/pacelab/SamsungHealthPlugin.kt); o Health Connect entra quando o app
// for para outras pessoas. Todas devolvem o formato que a API recebe em POST /api/saude/treinos.

import { registerPlugin } from '@capacitor/core'

export interface TreinoDaFonte {
  id: string
  tipo: string
  inicio: string // ISO com fuso
  fim: string
  duracao_s?: number
  distancia_m?: number
  calorias?: number
  fc_media?: number
  fc_max?: number
  cadencia_media?: number
  ganho_elevacao_m?: number
  vo2max?: number
  titulo?: string
  atualizado?: number // ms; muda quando o treino é editado no celular
  registros: { t: number; fc?: number; vel?: number; cad?: number; pot?: number }[]
  percurso: { t: number; lat: number; lon: number; alt?: number }[]
}

export interface Permissoes {
  exercicios: boolean
  percurso: boolean
}

export interface FonteTreinos {
  nome: 'samsung_health' | 'health_connect'
  rotulo: string
  permissoes(): Promise<Permissoes>
  pedirPermissoes(): Promise<Permissoes>
  lerTreinos(desde: number, ate: number): Promise<TreinoDaFonte[]>
}

interface PluginSamsungHealth {
  permissoes(): Promise<Permissoes>
  pedirPermissoes(): Promise<Permissoes>
  lerTreinos(opcoes: { desde: number; ate: number }): Promise<{ treinos: TreinoDaFonte[] }>
}

const SamsungHealth = registerPlugin<PluginSamsungHealth>('SamsungHealth')

export const samsungHealth: FonteTreinos = {
  nome: 'samsung_health',
  rotulo: 'Samsung Health',
  permissoes: () => SamsungHealth.permissoes(),
  pedirPermissoes: () => SamsungHealth.pedirPermissoes(),
  lerTreinos: async (desde, ate) => (await SamsungHealth.lerTreinos({ desde, ate })).treinos,
}
