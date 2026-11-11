// Sincronização do app Android: lê os treinos da fonte no celular e envia ao PC (ADR 0013).
// Roda ao abrir o app, ao voltar para ele e no botão Sincronizar.

import { api, ErroApi } from '../api/cliente'
import type { FonteTreinos, TreinoDaFonte } from './fontes'

const DIA = 24 * 60 * 60 * 1000
export const PRIMEIRA_JANELA = 30 * DIA // primeira vez: últimos 30 dias
export const MARGEM = 2 * DIA // o relógio às vezes passa os dados ao celular com atraso
export const POR_LOTE = 3 // treinos por envio (cada um pode ter milhares de pontos)

const chave = (fonte: string, o_que: string) => `pace-lab.sync.${fonte}.${o_que}`

export interface ResultadoSync {
  lidos: number
  enviados: number
  novos: number
  atualizados: number
  duplicados: number
  semPercurso: boolean // permissão de percurso negada: treinos chegam sem mapa
}

export class ErroSync extends Error {
  motivo: 'sem_permissao' | 'pc_fora' | 'fonte'
  constructor(motivo: ErroSync['motivo'], mensagem: string) {
    super(mensagem)
    this.motivo = motivo
  }
}

interface RespostaApi { novos: number; atualizados: number; novos_duplicados: number }

function ler<T>(k: string, padrao: T): T {
  try {
    const v = localStorage.getItem(k)
    return v ? (JSON.parse(v) as T) : padrao
  } catch {
    return padrao
  }
}

function gravar(k: string, v: unknown) {
  try {
    localStorage.setItem(k, JSON.stringify(v))
  } catch {
    // sem armazenamento: na próxima vez relê a janela inteira (a API não duplica)
  }
}

export function ultimaSincronizacao(fonte: string): number | null {
  return ler<number | null>(chave(fonte, 'marca'), null)
}

export async function sincronizar(fonte: FonteTreinos, agora = Date.now()): Promise<ResultadoSync> {
  let perm = await fonte.permissoes()
  if (!perm.exercicios) perm = await fonte.pedirPermissoes()
  if (!perm.exercicios) {
    throw new ErroSync('sem_permissao', `Sem permissão para ler os exercícios do ${fonte.rotulo}.`)
  }

  const marca = ultimaSincronizacao(fonte.nome)
  const desde = marca ? marca - MARGEM : agora - PRIMEIRA_JANELA
  let treinos: TreinoDaFonte[]
  try {
    treinos = await fonte.lerTreinos(desde, agora)
  } catch (e) {
    throw new ErroSync('fonte', `${fonte.rotulo}: ${e instanceof Error ? e.message : String(e)}`)
  }

  // não reenvia o que já foi enviado e não mudou: id -> data de atualização (a) e início (i), em ms
  const enviados = ler<Record<string, { a: number; i: number }>>(chave(fonte.nome, 'enviados'), {})
  const pendentes = treinos.filter((t) => enviados[t.id]?.a !== (t.atualizado ?? 0))

  const total: ResultadoSync = { lidos: treinos.length, enviados: 0, novos: 0, atualizados: 0, duplicados: 0,
    semPercurso: !perm.percurso }
  for (let i = 0; i < pendentes.length; i += POR_LOTE) {
    const lote = pendentes.slice(i, i + POR_LOTE)
    let r: RespostaApi
    try {
      r = await api<RespostaApi>('/saude/treinos', {
        method: 'POST',
        body: JSON.stringify({ fonte: fonte.nome, treinos: lote.map(({ atualizado: _, ...t }) => t) }),
      })
    } catch (e) {
      // o que já foi enviado fica registrado; a marca não avança, então a próxima vez continua daqui
      gravar(chave(fonte.nome, 'enviados'), enviados)
      if (e instanceof ErroApi && (e.status === 0 || e.message === 'PC fora do ar')) {
        throw new ErroSync('pc_fora', 'PC fora do ar: os treinos serão enviados na próxima sincronização.')
      }
      throw e
    }
    for (const t of lote) enviados[t.id] = { a: t.atualizado ?? 0, i: Date.parse(t.inicio) }
    total.enviados += lote.length
    total.novos += r.novos - r.novos_duplicados
    total.duplicados += r.novos_duplicados
    total.atualizados += r.atualizados
  }

  // esquece ids antigos para a lista não crescer para sempre
  const limite = agora - PRIMEIRA_JANELA - MARGEM
  for (const [id, e] of Object.entries(enviados)) if (e.i < limite) delete enviados[id]
  gravar(chave(fonte.nome, 'enviados'), enviados)
  gravar(chave(fonte.nome, 'marca'), agora)
  return total
}
