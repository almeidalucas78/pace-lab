// Teste de fumaça: cada página renderiza com respostas da API no formato real (dados sintéticos).
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { act } from 'react'
import { createRoot } from 'react-dom/client'
import { MemoryRouter } from 'react-router'
import { afterEach, beforeAll, describe, expect, it, vi } from 'vitest'
import { salvarToken } from '../api/cliente'
import { App } from '../App'
import { ProvedorContexto } from '../contexto'

;(globalThis as { IS_REACT_ACT_ENVIRONMENT?: boolean }).IS_REACT_ACT_ENVIRONMENT = true

const treino = {
  id: 4, data: '2026-10-20T07:52-03:00', esporte: 'run', tipo_original: 'Corrida', nome: 'Corrida matinal',
  distancia_km: 10.03, tempo_movimento_min: 49.8, ritmo: '4:58/km', fc_media: 144, fc_max: 208, cadencia_ppm: 172,
  ganho_elevacao_m: 54, temperatura_c: null, umidade_pct: null, tenis: null, carga: 112.2, qualidade_fc: 'ok',
  possivel_duplicata_de: null, arquivo: 'ok',
}
const dia = (d: string) => ({ dia: d, carga: 10, fitness: 23.7, fadiga: 10.4, forma: 12.3 })
const sessoes = [
  { id: 1, dia: '2026-10-19', dia_semana: 'seg', esporte: 'run', tipo: 'rodagem', distancia_km: 6, zona_fc: 'z2' },
  { id: 2, dia: '2026-10-21', dia_semana: 'qua', esporte: 'rest', tipo: 'descanso' },
]
const plano = { id: 1, titulo: 'Teste', inicio: '2026-10-19', fim: '2026-10-25', status: 'ativo', criado: '2026-10-28T22:00-03:00', sessoes }
const aderencia = {
  plano, resumo: { sessoes_vencidas: 1, feitas: 1, perdidas: 0, pct_feitas: 100, feitas_no_alvo: 0, futuras: 0, extras: 1 },
  semanas: [{ semana: '2026-10-19', planejadas: 1, feitas: 1, perdidas: 0, no_alvo: 0, km_planejados: 6, km_feitos: 10 }],
  sessoes: [{ sessao_id: 1, dia: '2026-10-19', esporte: 'run', tipo: 'rodagem', status: 'feita_outro_dia', treino_id: 4,
    treino_dia: '2026-10-20', no_alvo: false, comparacao: { distancia: { alvo_km: 6, feito_km: 10, pct: 167 } } },
  { sessao_id: 2, dia: '2026-10-21', esporte: 'rest', tipo: 'descanso', status: 'descanso' }],
  extras: [{ treino_id: 9, dia: '2026-10-22', esporte: 'strength', nome: 'Perna', distancia_km: null }],
}
const amostras = Array.from({ length: 60 }, (_, i) => ({
  t: i * 5, lat: -23.5 + i * 1e-4, lon: -46.6, ele: 700 + i, fc: 140 + (i % 10), cad: 170, vel: 3.3, dist: i * 16.5,
}))

const ROTAS: [RegExp, unknown][] = [
  [/\/api\/carga\/atual/, { hoje: dia('2026-10-28'), ha_7_dias: dia('2026-10-21'), ha_28_dias: null, carga_7_dias: 0, fc_max_usada: 214, fc_max_origem: 'estimada' }],
  [/\/api\/load/, [dia('2026-10-27'), dia('2026-10-28')]],
  [/\/api\/weeks/, [{ semana: '2026-10-19', treinos: 1, km: 10, tempo_min: 50, ritmo_medio: '4:58/km', maior_treino_km: 10, carga: 112 }]],
  [/\/api\/activities\/4\/samples/, amostras],
  [/\/api\/activities\/4$/, { ...treino, descricao: null, percepcao_esforco: null, zonas_fc_min: { z0: 1, z2: 30, z3: 10 },
    parciais: [{ km: 1, distancia_m: 1000, ritmo: '5:27/km', fc_media: 135, elevacao_m: 2 }], observacoes_dados: {},
    sensacoes: [{ id: 1, dia: '2026-10-20', treino_id: 4, rpe: 7, texto: 'pernas pesadas', tags: null }] }],
  [/\/api\/activities/, [treino]],
  [/\/api\/perfil/, { fc_max: 214, fc_max_origem: 'estimada', fc_max_observacao: '', fc_repouso: null, zonas_fc: { z2: '128 a 149 bpm' } }],
  [/\/api\/planos\/ativo\/aderencia/, aderencia],
  [/\/api\/planos\/ativo/, plano],
  [/\/api\/planos$/, [plano]],
  [/\/api\/chat\/conversas$/, []],
  [/\/api\/painel\/config/, { url_celular: 'https://pacelab.teste.ts.net' }],
]

beforeAll(() => {
  globalThis.ResizeObserver ??= class { observe() {} unobserve() {} disconnect() {} } as unknown as typeof ResizeObserver
  vi.spyOn(globalThis, 'fetch').mockImplementation(async (url) => {
    const rota = ROTAS.find(([re]) => re.test(String(url)))
    return new Response(JSON.stringify(rota ? rota[1] : {}), { status: rota ? 200 : 404 })
  })
  salvarToken('teste')
})

let raiz: ReturnType<typeof createRoot> | null = null
afterEach(() => {
  act(() => raiz?.unmount())
  document.body.innerHTML = ''
})

async function renderizar(caminho: string): Promise<string> {
  const div = document.createElement('div')
  document.body.appendChild(div)
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  raiz = createRoot(div)
  await act(async () => {
    raiz!.render(
      <QueryClientProvider client={qc}>
        <MemoryRouter initialEntries={[caminho]}><ProvedorContexto><App /></ProvedorContexto></MemoryRouter>
      </QueryClientProvider>,
    )
  })
  // páginas carregam sob demanda: espera sumir o "Carregando..." (até ~5 s)
  for (let i = 0; i < 100 && (i < 5 || (div.textContent ?? '').includes('Carregando')); i++) {
    await act(async () => { await new Promise((r) => setTimeout(r, 50)) })
  }
  return div.textContent ?? ''
}

describe('páginas', () => {
  it('visão geral', async () => {
    const txt = await renderizar('/')
    expect(txt).toContain('Fitness')
    expect(txt).toContain('Corrida matinal')
    expect(txt).toContain('estimada')
  })

  it('lista de treinos', async () => {
    const txt = await renderizar('/treinos')
    expect(txt).toContain('Corrida matinal')
    expect(txt).toContain('4:58/km')
  })

  it('detalhe do treino', async () => {
    const txt = await renderizar('/treinos/4')
    expect(txt).toContain('Parciais por km')
    expect(txt).toContain('5:27/km')
    expect(txt).toContain('pernas pesadas')
    expect(txt).toContain('128 a 149 bpm')
  })

  it('chat em página própria (celular)', async () => {
    const txt = await renderizar('/chat')
    expect(txt).toContain('Pergunte sobre seus treinos')
    expect(txt).toContain('Enviar')
  })

  it('conectar celular mostra o endereço e o botão do QR code', async () => {
    const txt = await renderizar('/conectar')
    expect(txt).toContain('https://pacelab.teste.ts.net')
    expect(txt).toContain('Mostrar QR code')
    expect(txt).toContain('Não compartilhe')
  })

  it('treinos têm cartões para o celular e tabela para o PC', async () => {
    await renderizar('/treinos')
    expect(document.querySelectorAll('.cartao-treino').length).toBe(1)
    expect(document.querySelector('table.so-desktop')).not.toBeNull()
    expect(document.querySelectorAll('.barra-inferior a').length).toBe(4)
  })

  it('plano com aderência', async () => {
    const txt = await renderizar('/plano')
    expect(txt).toContain('Teste')
    expect(txt).toContain('Feita em outro dia')
    expect(txt).toContain('fora do alvo')
    expect(txt).toContain('extra: Perna')
  })
})
