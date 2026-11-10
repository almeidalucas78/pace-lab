// Formatação para exibir (pt-BR). Ritmos já vêm formatados da API quando possível.

import type { Esporte, StatusSessao } from '../api/tipos'

export const ESPORTES: Record<string, string> = {
  run: 'Corrida', walk: 'Caminhada', ride: 'Pedalada', strength: 'Musculação',
  workout: 'Treino', other: 'Outro', rest: 'Descanso',
}

export const TIPOS_SESSAO: Record<string, string> = {
  rodagem: 'Rodagem', longao: 'Longão', intervalado: 'Intervalado', ritmo: 'Ritmo',
  regenerativo: 'Regenerativo', descanso: 'Descanso', musculacao: 'Musculação', outro: 'Outro',
}

export const STATUS_SESSAO: Record<StatusSessao, string> = {
  feita: 'Feita', feita_outro_dia: 'Feita em outro dia', perdida: 'Perdida', futura: 'Futura',
  pendente_hoje: 'Hoje', cancelada: 'Cancelada', descanso: 'Descanso',
}

export function esporte(e: Esporte | string): string {
  return ESPORTES[e] ?? e
}

/** Segundos por km em "m:ss/km". */
export function ritmo(segundosPorKm: number | null | undefined): string {
  if (!segundosPorKm || !Number.isFinite(segundosPorKm)) return '-'
  const total = Math.round(segundosPorKm)
  const m = Math.floor(total / 60)
  const s = total % 60
  return `${m}:${String(s).padStart(2, '0')}/km`
}

/** Velocidade em m/s para ritmo em segundos por km (null quando parado). */
export function velocidadeParaRitmo(ms: number | null | undefined): number | null {
  if (!ms || ms < 0.5) return null
  return 1000 / ms
}

/** Minutos em "1h05" ou "48 min". */
export function duracao(minutos: number | null | undefined): string {
  if (minutos == null || !Number.isFinite(minutos)) return '-'
  const total = Math.round(minutos)
  if (total < 60) return `${total} min`
  const h = Math.floor(total / 60)
  return `${h}h${String(total % 60).padStart(2, '0')}`
}

export function km(valor: number | null | undefined, casas = 2): string {
  if (valor == null) return '-'
  return `${valor.toLocaleString('pt-BR', { minimumFractionDigits: casas, maximumFractionDigits: casas })} km`
}

const DIAS = ['dom', 'seg', 'ter', 'qua', 'qui', 'sex', 'sáb']

/** "2026-10-20" ou "2026-10-20T07:52-03:00" em "ter, 20/10". A data já vem no fuso local. */
export function dataCurta(iso: string, comDiaSemana = true): string {
  const [a, m, d] = iso.slice(0, 10).split('-').map(Number)
  const dia = new Date(Date.UTC(a, m - 1, d)).getUTCDay()
  const texto = `${String(d).padStart(2, '0')}/${String(m).padStart(2, '0')}`
  return comDiaSemana ? `${DIAS[dia]}, ${texto}` : texto
}

/** Hora "07:52" de um ISO com fuso. */
export function hora(iso: string): string {
  return iso.slice(11, 16)
}

export function numero(valor: number | null | undefined, casas = 0): string {
  if (valor == null) return '-'
  return valor.toLocaleString('pt-BR', { minimumFractionDigits: casas, maximumFractionDigits: casas })
}

/** Variação com sinal: "+1,2" ou "-3,0". */
export function variacao(valor: number | null | undefined, casas = 1): string {
  if (valor == null) return '-'
  const txt = numero(Math.abs(valor), casas)
  return valor > 0 ? `+${txt}` : valor < 0 ? `-${txt}` : txt
}

/** Momento registrado no próprio aparelho (ms desde a época) em "09/11 às 07:52". */
export function momentoLocal(ms: number | null | undefined): string {
  if (!ms) return '-'
  const d = new Date(ms)
  const p = (n: number) => String(n).padStart(2, '0')
  return `${p(d.getDate())}/${p(d.getMonth() + 1)} às ${p(d.getHours())}:${p(d.getMinutes())}`
}
