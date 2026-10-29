import { Area, Bar, CartesianGrid, ComposedChart, Legend, Line, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import type { DiaCarga } from '../api/tipos'
import { dataCurta, numero } from '../util/formato'

const NOMES: Record<string, string> = { carga: 'Carga do dia', fitness: 'Fitness', fadiga: 'Fadiga', forma: 'Forma' }

/** Carga diária em barras, fitness e fadiga em linhas, forma em área (eixo da esquerda). */
export function GraficoCarga({ dados }: { dados: DiaCarga[] }) {
  return (
    <ResponsiveContainer width="100%" height={300}>
      <ComposedChart data={dados} margin={{ top: 8, right: 4, bottom: 0, left: -12 }}>
        <CartesianGrid stroke="var(--borda)" vertical={false} />
        <XAxis dataKey="dia" tickFormatter={(d) => dataCurta(d, false)} tick={{ fill: 'var(--texto-2)', fontSize: 12 }}
               minTickGap={24} stroke="var(--borda)" />
        <YAxis yAxisId="estado" tick={{ fill: 'var(--texto-2)', fontSize: 12 }} stroke="var(--borda)" />
        <YAxis yAxisId="carga" orientation="right" tick={{ fill: 'var(--texto-2)', fontSize: 12 }} stroke="var(--borda)" />
        <Tooltip
          contentStyle={{ background: 'var(--superficie)', border: '1px solid var(--borda)', borderRadius: 8 }}
          labelFormatter={(d) => dataCurta(String(d))}
          formatter={(v, nome) => [numero(Number(v), 1), NOMES[String(nome)] ?? nome]}
        />
        <Legend formatter={(nome) => NOMES[nome] ?? nome} wrapperStyle={{ fontSize: 13 }} />
        <Bar yAxisId="carga" dataKey="carga" fill="var(--carga)" opacity={0.55} maxBarSize={8} />
        <Area yAxisId="estado" dataKey="forma" stroke="var(--forma)" fill="var(--forma)" fillOpacity={0.12} dot={false} />
        <Line yAxisId="estado" dataKey="fitness" stroke="var(--fitness)" strokeWidth={2} dot={false} />
        <Line yAxisId="estado" dataKey="fadiga" stroke="var(--fadiga)" strokeWidth={2} dot={false} />
      </ComposedChart>
    </ResponsiveContainer>
  )
}
