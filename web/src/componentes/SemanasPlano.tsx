import { Link } from 'react-router'
import type { Aderencia, LinhaAderencia, SessaoPlano } from '../api/tipos'
import { dataCurta, duracao, esporte, TIPOS_SESSAO } from '../util/formato'
import { EtiquetaAlvo, EtiquetaStatus } from './Etiquetas'

const DIAS = ['seg', 'ter', 'qua', 'qui', 'sex', 'sáb', 'dom']

function isoDia(d: Date): string {
  return d.toISOString().slice(0, 10)
}

/** Segunda-feira (ISO) da semana de uma data AAAA-MM-DD. */
export function segundaDa(iso: string): string {
  const [a, m, d] = iso.split('-').map(Number)
  const dt = new Date(Date.UTC(a, m - 1, d))
  dt.setUTCDate(dt.getUTCDate() - ((dt.getUTCDay() + 6) % 7))
  return isoDia(dt)
}

function diasDaSemana(segunda: string): string[] {
  const [a, m, d] = segunda.split('-').map(Number)
  return DIAS.map((_, i) => isoDia(new Date(Date.UTC(a, m - 1, d + i))))
}

function metas(s: SessaoPlano): string {
  return [s.distancia_km ? `${s.distancia_km} km` : null, s.duracao_min ? duracao(s.duracao_min) : null,
    s.ritmo ?? null, s.zona_fc?.toUpperCase() ?? null, s.esforco ? `esforço ${s.esforco}` : null]
    .filter(Boolean).join(' · ')
}

function Sessao({ s, linha }: { s: SessaoPlano; linha?: LinhaAderencia }) {
  const status = linha?.status ?? 'futura'
  return (
    <div className={`dia-plano ${status}`} title={s.descricao ?? ''}>
      <div className="cab"><span>{TIPOS_SESSAO[s.tipo] ?? s.tipo}</span><span>{s.esporte !== 'rest' && s.esporte !== 'run' ? esporte(s.esporte) : ''}</span></div>
      {metas(s) && <div>{metas(s)}</div>}
      {s.descricao && <div className="fraco pequeno">{s.descricao}</div>}
      <div className="linha" style={{ gap: 4, marginTop: 'auto' }}>
        {status !== 'descanso' && <EtiquetaStatus status={status} />}
        <EtiquetaAlvo noAlvo={linha?.no_alvo} />
      </div>
      {linha?.treino_id && <Link to={`/treinos/${linha.treino_id}`} className="pequeno">ver treino</Link>}
    </div>
  )
}

/** Semanas do plano (segunda a domingo), com a situação de cada sessão vinda da aderência. */
export function SemanasPlano({ sessoes, aderencia, soSemanaDe }: {
  sessoes: SessaoPlano[]
  aderencia: Aderencia | null | undefined
  soSemanaDe?: string // AAAA-MM-DD: mostra só a semana desta data
}) {
  const porSessao = new Map((aderencia?.sessoes ?? []).map((l) => [l.sessao_id, l]))
  const extrasPorDia = new Map<string, Aderencia['extras']>()
  for (const e of aderencia?.extras ?? []) extrasPorDia.set(e.dia, [...(extrasPorDia.get(e.dia) ?? []), e])
  const porDia = new Map<string, SessaoPlano[]>()
  for (const s of sessoes) porDia.set(s.dia, [...(porDia.get(s.dia) ?? []), s])
  const segundas = soSemanaDe ? [segundaDa(soSemanaDe)]
    : [...new Set(sessoes.map((s) => segundaDa(s.dia)))].sort()
  const resumoSemana = new Map((aderencia?.semanas ?? []).map((w) => [w.semana, w]))

  return (
    <div className="pilha">
      {segundas.map((seg) => {
        const w = resumoSemana.get(seg)
        return (
          <div key={seg} className="pilha" style={{ gap: 8 }}>
            <div className="linha entre">
              <strong>Semana de {dataCurta(seg, false)}</strong>
              {w && w.planejadas > 0 && (
                <span className="fraco pequeno">
                  {w.feitas}/{w.planejadas} feitas · {w.km_feitos} de {w.km_planejados} km
                </span>
              )}
            </div>
            <div className="semana-plano">
              {diasDaSemana(seg).map((dia, i) => {
                const doDia = porDia.get(dia) ?? []
                const extras = extrasPorDia.get(dia) ?? []
                return (
                  <div key={dia} className="pilha" style={{ gap: 6 }}>
                    <div className="rotulo">{DIAS[i]} {dataCurta(dia, false)}</div>
                    {doDia.length === 0 && extras.length === 0 && <div className="dia-plano vazio-dia" />}
                    {doDia.map((s) => <Sessao key={s.id} s={s} linha={porSessao.get(s.id)} />)}
                    {extras.map((e) => (
                      <Link key={e.treino_id} to={`/treinos/${e.treino_id}`} className="etiqueta e-destaque"
                            title="treino fora do plano">
                        extra: {e.nome ?? esporte(e.esporte)}
                      </Link>
                    ))}
                  </div>
                )
              })}
            </div>
          </div>
        )
      })}
    </div>
  )
}
