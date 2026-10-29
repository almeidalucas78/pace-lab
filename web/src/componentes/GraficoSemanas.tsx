import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import type { Semana } from '../api/tipos'
import { dataCurta, numero } from '../util/formato'

export function GraficoSemanas({ dados }: { dados: Semana[] }) {
  return (
    <ResponsiveContainer width="100%" height={220}>
      <BarChart data={dados} margin={{ top: 8, right: 4, bottom: 0, left: -18 }}>
        <CartesianGrid stroke="var(--borda)" vertical={false} />
        <XAxis dataKey="semana" tickFormatter={(d) => dataCurta(d, false)} tick={{ fill: 'var(--texto-2)', fontSize: 12 }}
               stroke="var(--borda)" />
        <YAxis tick={{ fill: 'var(--texto-2)', fontSize: 12 }} stroke="var(--borda)" unit=" km" width={64} />
        <Tooltip
          contentStyle={{ background: 'var(--superficie)', border: '1px solid var(--borda)', borderRadius: 8 }}
          labelFormatter={(d) => `Semana de ${dataCurta(String(d))}`}
          formatter={(v, _n, item) => {
            const s = item.payload as Semana
            return [`${numero(Number(v), 1)} km em ${s.treinos} treino(s), ritmo ${s.ritmo_medio ?? '-'}`, 'Volume']
          }}
        />
        <Bar dataKey="km" fill="var(--destaque)" radius={[4, 4, 0, 0]} maxBarSize={36} />
      </BarChart>
    </ResponsiveContainer>
  )
}
