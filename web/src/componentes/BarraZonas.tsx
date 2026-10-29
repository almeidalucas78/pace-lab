import { duracao } from '../util/formato'

const CORES: Record<string, string> = {
  z0: '#cbd5e1', z1: '#93c5fd', z2: '#4ade80', z3: '#facc15', z4: '#fb923c', z5: '#ef4444',
}

/** Tempo em cada zona de FC (minutos), com as faixas em bpm quando conhecidas. */
export function BarraZonas({ zonas, faixas }: { zonas: Record<string, number>; faixas?: Record<string, string> | null }) {
  const total = Object.values(zonas).reduce((a, b) => a + b, 0)
  if (!total) return <div className="vazio">Sem dados de FC.</div>
  const ordem = ['z0', 'z1', 'z2', 'z3', 'z4', 'z5'].filter((z) => z in zonas)
  return (
    <div className="pilha" style={{ gap: 10 }}>
      <div className="barra-zonas">
        {ordem.map((z) => (
          <div key={z} title={`${z.toUpperCase()}: ${duracao(zonas[z])}`}
               style={{ width: `${(100 * zonas[z]) / total}%`, background: CORES[z] }} />
        ))}
      </div>
      <table>
        <tbody>
          {ordem.map((z) => (
            <tr key={z}>
              <td><span className="etiqueta" style={{ background: CORES[z], color: '#111' }}>{z.toUpperCase()}</span></td>
              <td className="fraco pequeno">{faixas?.[z] ?? ''}</td>
              <td className="num">{duracao(zonas[z])}</td>
              <td className="num fraco">{Math.round((100 * zonas[z]) / total)}%</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
