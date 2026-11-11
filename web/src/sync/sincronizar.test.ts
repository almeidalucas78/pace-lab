// Sincronização do app com uma fonte simulada (o plugin em Kotlin só roda no celular).
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { salvarToken } from '../api/cliente'
import type { FonteTreinos, Permissoes, TreinoDaFonte } from './fontes'
import { ErroSync, MARGEM, POR_LOTE, PRIMEIRA_JANELA, sincronizar, ultimaSincronizacao } from './sincronizar'

const AGORA = Date.UTC(2026, 10, 11, 12, 0, 0)
const treino = (id: string, diasAtras: number, atualizado = 1): TreinoDaFonte => ({
  id, tipo: 'RUNNING', inicio: new Date(AGORA - diasAtras * 86_400_000).toISOString(),
  fim: new Date(AGORA - diasAtras * 86_400_000 + 3_600_000).toISOString(), atualizado,
  registros: [{ t: 1, fc: 150 }], percurso: [{ t: 1, lat: -23.5, lon: -46.6 }],
})

function fonteFalsa(treinos: TreinoDaFonte[], perm: Permissoes = { exercicios: true, percurso: true }) {
  return {
    nome: 'samsung_health', rotulo: 'Samsung Health',
    permissoes: vi.fn(async () => perm),
    pedirPermissoes: vi.fn(async () => ({ exercicios: true, percurso: true })),
    lerTreinos: vi.fn(async () => treinos),
  } satisfies FonteTreinos
}

function apiFalsa() {
  const corpos: { fonte: string; treinos: TreinoDaFonte[] }[] = []
  const f = vi.spyOn(globalThis, 'fetch').mockImplementation(async (_url, init) => {
    const corpo = JSON.parse(String(init?.body))
    corpos.push(corpo)
    return new Response(JSON.stringify({ novos: corpo.treinos.length, atualizados: 0, novos_duplicados: 0 }),
      { status: 200 })
  })
  return { corpos, f }
}

beforeEach(() => {
  localStorage.clear()
  salvarToken('t')
})
afterEach(() => vi.restoreAllMocks())

describe('sincronização do app', () => {
  it('primeira vez lê 30 dias, envia em lotes e guarda a marca', async () => {
    const fonte = fonteFalsa([treino('a', 10), treino('b', 5), treino('c', 3), treino('d', 1)])
    const { corpos } = apiFalsa()
    const r = await sincronizar(fonte, AGORA)
    expect(fonte.lerTreinos).toHaveBeenCalledWith(AGORA - PRIMEIRA_JANELA, AGORA)
    expect(corpos.map((c) => c.treinos.length)).toEqual([POR_LOTE, 1])
    expect(corpos[0].fonte).toBe('samsung_health')
    expect(corpos[0].treinos[0]).not.toHaveProperty('atualizado')   // campo só do app
    expect(r).toMatchObject({ lidos: 4, enviados: 4, novos: 4, semPercurso: false })
    expect(ultimaSincronizacao('samsung_health')).toBe(AGORA)
  })

  it('próxima vez lê desde a marca menos a margem e não reenvia o que não mudou', async () => {
    const { corpos } = apiFalsa()
    await sincronizar(fonteFalsa([treino('a', 1)]), AGORA)
    const fonte = fonteFalsa([treino('a', 1), treino('b', 0)])
    const depois = AGORA + 3_600_000
    const r = await sincronizar(fonte, depois)
    expect(fonte.lerTreinos).toHaveBeenCalledWith(AGORA - MARGEM, depois)
    expect(corpos[1].treinos.map((t) => t.id)).toEqual(['b'])
    expect(r).toMatchObject({ lidos: 2, enviados: 1 })
    // editado no celular (data de atualização mudou): reenvia
    await sincronizar(fonteFalsa([treino('a', 1, 2)]), depois + 1)
    expect(corpos[2].treinos.map((t) => t.id)).toEqual(['a'])
  })

  it('pede permissão quando falta e falha se for negada', async () => {
    apiFalsa()
    const fonte = fonteFalsa([], { exercicios: false, percurso: false })
    await sincronizar(fonte, AGORA)
    expect(fonte.pedirPermissoes).toHaveBeenCalled()
    const negada = fonteFalsa([], { exercicios: false, percurso: false })
    negada.pedirPermissoes.mockResolvedValue({ exercicios: false, percurso: false })
    await expect(sincronizar(negada, AGORA)).rejects.toMatchObject({ motivo: 'sem_permissao' })
  })

  it('sem permissão de percurso sincroniza e avisa', async () => {
    apiFalsa()
    const r = await sincronizar(fonteFalsa([treino('a', 1)], { exercicios: true, percurso: false }), AGORA)
    expect(r.semPercurso).toBe(true)
  })

  it('PC fora do ar: não avança a marca e continua de onde parou', async () => {
    const fonte = fonteFalsa([treino('a', 3), treino('b', 2), treino('c', 1), treino('d', 0)])
    let chamadas = 0
    vi.spyOn(globalThis, 'fetch').mockImplementation(async () => {
      chamadas += 1
      if (chamadas > 1) throw new TypeError('Failed to fetch')
      return new Response(JSON.stringify({ novos: 3, atualizados: 0, novos_duplicados: 0 }), { status: 200 })
    })
    const erro = await sincronizar(fonte, AGORA).catch((e: unknown) => e)
    expect(erro).toBeInstanceOf(ErroSync)
    expect((erro as ErroSync).motivo).toBe('pc_fora')
    expect(ultimaSincronizacao('samsung_health')).toBeNull()
    vi.restoreAllMocks()
    const { corpos } = apiFalsa()
    await sincronizar(fonte, AGORA + 1)
    expect(corpos[0].treinos.map((t) => t.id)).toEqual(['d'])   // os 3 primeiros já tinham ido
  })

  it('erro do Samsung Health vira mensagem da fonte', async () => {
    const fonte = fonteFalsa([])
    fonte.lerTreinos.mockRejectedValue(new Error('developer mode off'))
    await expect(sincronizar(fonte, AGORA)).rejects.toMatchObject({ motivo: 'fonte' })
  })
})
