import { Link, useParams } from 'react-router'
import { useAderencia, useAderenciaAtiva, usePlano, usePlanoAtivo, usePlanos } from '../api/consultas'
import type { Aderencia, Plano as TPlano } from '../api/tipos'
import { Estado } from '../componentes/Estado'
import { SemanasPlano } from '../componentes/SemanasPlano'
import { useDescreverPagina } from '../contexto'
import { dataCurta } from '../util/formato'

const STATUS_PLANO: Record<TPlano['status'], string> = { ativo: 'ativo', arquivado: 'arquivado', substituido: 'substituído' }

function Resumo({ a }: { a: Aderencia }) {
  const r = a.resumo
  return (
    <div className="grade grade-4">
      <div className="cartao">
        <div className="rotulo">Sessões feitas</div>
        <div className="numero-grande">{r.pct_feitas != null ? `${r.pct_feitas}%` : '-'}</div>
        <div className="fraco pequeno">{r.feitas} de {r.sessoes_vencidas} até hoje</div>
      </div>
      <div className="cartao">
        <div className="rotulo">No alvo</div>
        <div className="numero-grande">{r.feitas_no_alvo}</div>
        <div className="fraco pequeno">das {r.feitas} feitas</div>
      </div>
      <div className="cartao"><div className="rotulo">Perdidas</div><div className="numero-grande">{r.perdidas}</div></div>
      <div className="cartao">
        <div className="rotulo">Por vir / extras</div>
        <div className="numero-grande">{r.futuras} / {r.extras}</div>
        <div className="fraco pequeno">sessões futuras / treinos fora do plano</div>
      </div>
    </div>
  )
}

function VerPlano({ plano, aderencia }: { plano: TPlano; aderencia: Aderencia | null | undefined }) {
  useDescreverPagina(`o usuário está vendo o plano #${plano.id} ("${plano.titulo}", ${plano.inicio} a ${plano.fim}, `
    + `${plano.status}); use plano_atual e aderencia_plano com esse id`)
  return (
    <div className="pilha">
      <div>
        <div className="linha entre">
          <h1>{plano.titulo}</h1>
          <span className={`etiqueta ${plano.status === 'ativo' ? 'e-ok' : 'e-neutro'}`}>{STATUS_PLANO[plano.status]}</span>
        </div>
        <p className="subtitulo">
          {dataCurta(plano.inicio)} a {dataCurta(plano.fim)}
          {plano.objetivo && <> · {plano.objetivo}</>}
          {plano.substituido_por && <> · substituído pelo <Link to={`/plano/${plano.substituido_por}`}>plano #{plano.substituido_por}</Link></>}
        </p>
      </div>
      {aderencia && <Resumo a={aderencia} />}
      {aderencia?.observacao && <div className="fraco pequeno">{aderencia.observacao}</div>}
      <div className="cartao"><SemanasPlano sessoes={plano.sessoes ?? []} aderencia={aderencia} /></div>
      {plano.notas && <div className="cartao"><h2>Notas</h2>{plano.notas}</div>}
    </div>
  )
}

function Historico() {
  const planos = usePlanos()
  return (
    <div className="cartao">
      <h2>Histórico de planos</h2>
      <Estado consulta={planos} vazio="Nenhum plano ainda.">
        {(lista) => (
          <table>
            <tbody>
              {lista.map((p) => (
                <tr key={p.id}>
                  <td><Link to={`/plano/${p.id}`}>{p.titulo}</Link></td>
                  <td className="fraco">{dataCurta(p.inicio, false)} a {dataCurta(p.fim, false)}</td>
                  <td>{STATUS_PLANO[p.status]}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </Estado>
    </div>
  )
}

function PlanoAtivo() {
  const plano = usePlanoAtivo()
  const aderencia = useAderenciaAtiva()
  return (
    <div className="pilha">
      <Estado consulta={plano} vazio={
        <div className="cartao pilha">
          <h1>Nenhum plano ativo</h1>
          <p className="fraco" style={{ margin: 0 }}>
            Abra o chat e peça um, por exemplo: "quero correr 10 km em 50 min em dezembro, posso treinar
            segunda, quarta e sábado". O treinador mostra o plano e só salva depois que você confirmar.
          </p>
        </div>
      }>
        {(p) => <VerPlano plano={p} aderencia={aderencia.data} />}
      </Estado>
      <Historico />
    </div>
  )
}

function PlanoPorId({ id }: { id: number }) {
  const plano = usePlano(id)
  const aderencia = useAderencia(id)
  return (
    <div className="pilha">
      <Link to="/plano" className="pequeno">voltar para o plano ativo</Link>
      <Estado consulta={plano}>{(p) => <VerPlano plano={p} aderencia={aderencia.data} />}</Estado>
    </div>
  )
}

export function Plano() {
  const { id } = useParams()
  return id ? <PlanoPorId id={Number(id)} /> : <PlanoAtivo />
}
