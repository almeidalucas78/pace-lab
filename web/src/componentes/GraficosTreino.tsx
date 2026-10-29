import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import type { Amostra } from '../api/tipos'
import { numero, ritmo, velocidadeParaRitmo } from '../util/formato'

interface Ponto { km: number; fc: number | null; ritmo: number | null; ele: number | null }

/** Mediana móvel: o ritmo instantâneo do GPS oscila muito. */
function suavizar(valores: (number | null)[], janela = 7): (number | null)[] {
  return valores.map((_, i) => {
    const viz = valores.slice(Math.max(0, i - janela), i + janela + 1).filter((v): v is number => v != null)
    if (!viz.length) return null
    viz.sort((a, b) => a - b)
    return viz[Math.floor(viz.length / 2)]
  })
}

export function pontosDoTreino(amostras: Amostra[]): Ponto[] {
  const comDist = amostras.filter((a) => a.dist != null)
  const ritmos = suavizar(comDist.map((a) => velocidadeParaRitmo(a.vel)))
  return comDist.map((a, i) => ({ km: (a.dist as number) / 1000, fc: a.fc, ritmo: ritmos[i], ele: a.ele }))
}

const eixoX = { dataKey: 'km', type: 'number' as const, domain: ['dataMin', 'dataMax'] as [string, string],
  tickFormatter: (v: number) => `${numero(v, 0)} km`, tick: { fill: 'var(--texto-2)', fontSize: 12 }, stroke: 'var(--borda)' }
const dica = { contentStyle: { background: 'var(--superficie)', border: '1px solid var(--borda)', borderRadius: 8 },
  labelFormatter: (v: unknown) => `${numero(Number(v), 2)} km` }

function Grafico({ dados, chave, cor, titulo, formato, invertido, dominio }: {
  dados: Ponto[]; chave: keyof Ponto; cor: string; titulo: string; formato: (v: number) => string
  invertido?: boolean; dominio?: [number, number]
}) {
  if (!dados.some((p) => p[chave] != null)) return null
  return (
    <div>
      <div className="rotulo">{titulo}</div>
      <ResponsiveContainer width="100%" height={150}>
        <LineChart data={dados} syncId="treino" margin={{ top: 6, right: 8, bottom: 0, left: 0 }}>
          <CartesianGrid stroke="var(--borda)" vertical={false} />
          <XAxis {...eixoX} />
          <YAxis reversed={invertido} domain={dominio ?? ['auto', 'auto']} tickFormatter={formato} width={64}
                 tick={{ fill: 'var(--texto-2)', fontSize: 12 }} stroke="var(--borda)" />
          <Tooltip {...dica} formatter={(v) => [formato(Number(v)), titulo]} />
          <Line dataKey={chave} stroke={cor} dot={false} strokeWidth={1.6} isAnimationActive={false} connectNulls />
        </LineChart>
      </ResponsiveContainer>
    </div>
  )
}

/** FC, ritmo e altitude ao longo da distância, com o cursor sincronizado. */
export function GraficosTreino({ amostras, mostrarRitmo }: { amostras: Amostra[]; mostrarRitmo: boolean }) {
  const dados = pontosDoTreino(amostras)
  if (dados.length < 10) return <div className="vazio">Sem dados ao longo do treino.</div>
  const rs = dados.map((p) => p.ritmo).filter((v): v is number => v != null).sort((a, b) => a - b)
  const dominioRitmo: [number, number] | undefined = rs.length
    ? [Math.floor(rs[Math.floor(rs.length * 0.02)] / 15) * 15, Math.ceil(rs[Math.floor(rs.length * 0.98)] / 15) * 15]
    : undefined
  return (
    <div className="pilha" style={{ gap: 8 }}>
      <Grafico dados={dados} chave="fc" cor="var(--fc)" titulo="Frequência cardíaca" formato={(v) => `${Math.round(v)} bpm`} />
      {mostrarRitmo && (
        <Grafico dados={dados} chave="ritmo" cor="var(--ritmo)" titulo="Ritmo" formato={(v) => ritmo(v)}
                 invertido dominio={dominioRitmo} />
      )}
      <Grafico dados={dados} chave="ele" cor="var(--altitude)" titulo="Altitude" formato={(v) => `${Math.round(v)} m`} />
    </div>
  )
}
