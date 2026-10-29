import { Link } from 'react-router'
import { useAderenciaAtiva, useCargaAtual, usePlanoAtivo, useSemanas, useSerieCarga, useTreinos } from '../api/consultas'
import type { DiaCarga } from '../api/tipos'
import { Estado } from '../componentes/Estado'
import { EtiquetaQualidadeFc } from '../componentes/Etiquetas'
import { GraficoCarga } from '../componentes/GraficoCarga'
import { GraficoSemanas } from '../componentes/GraficoSemanas'
import { SemanasPlano } from '../componentes/SemanasPlano'
import { useDescreverPagina } from '../contexto'
import { dataCurta, duracao, hora, km, numero, variacao } from '../util/formato'

function Indicador({ titulo, valor, antes, dica }: {
  titulo: string; valor: number; antes: number | undefined; dica: string
}) {
  return (
    <div className="cartao" title={dica}>
      <div className="rotulo">{titulo}</div>
      <div className="numero-grande">{numero(valor, 1)}</div>
      {antes !== undefined && <div className="fraco pequeno">{variacao(valor - antes)} em 7 dias</div>}
    </div>
  )
}

function Indicadores({ hoje, ha7, carga7 }: { hoje: DiaCarga; ha7: DiaCarga | null; carga7: number }) {
  return (
    <div className="grade grade-4">
      <Indicador titulo="Fitness" valor={hoje.fitness} antes={ha7?.fitness}
                 dica="Média exponencial de 42 dias da carga: o condicionamento construído." />
      <Indicador titulo="Fadiga" valor={hoje.fadiga} antes={ha7?.fadiga}
                 dica="Média exponencial de 7 dias da carga: o cansaço recente." />
      <Indicador titulo="Forma" valor={hoje.forma} antes={ha7?.forma}
                 dica="Fitness menos fadiga. Positiva: descansado; muito negativa: carga alta." />
      <div className="cartao" title="Soma do TRIMP dos últimos 7 dias">
        <div className="rotulo">Carga em 7 dias</div>
        <div className="numero-grande">{numero(carga7)}</div>
        <div className="fraco pequeno">TRIMP</div>
      </div>
    </div>
  )
}

export function VisaoGeral() {
  useDescreverPagina('o usuário está na visão geral do painel (carga, volume semanal, último treino e semana do plano)')
  const carga = useCargaAtual()
  const serie = useSerieCarga(90)
  const semanas = useSemanas(12)
  const ultimo = useTreinos('run', 1, 0)
  const plano = usePlanoAtivo()
  const aderencia = useAderenciaAtiva()
  const hoje = new Date().toLocaleDateString('sv-SE') // AAAA-MM-DD no fuso do navegador

  return (
    <div className="pilha">
      <div>
        <h1>Visão geral</h1>
        <p className="subtitulo">Carga de treino, volume e o que vem pela frente.</p>
      </div>

      <Estado consulta={carga}>
        {(c) => c.aviso ? <div className="vazio">{c.aviso}</div>
          : <Indicadores hoje={c.hoje} ha7={c.ha_7_dias} carga7={c.carga_7_dias} />}
      </Estado>
      {carga.data?.fc_max_origem === 'estimada' && (
        <div className="fraco pequeno">
          Zonas e carga usam FC máxima <strong>estimada</strong> de {carga.data.fc_max_usada} bpm.
        </div>
      )}

      <div className="cartao">
        <h2>Últimos 90 dias</h2>
        <Estado consulta={serie} vazio="Sem carga registrada.">{(d) => <GraficoCarga dados={d} />}</Estado>
      </div>

      <div className="grade grade-2">
        <div className="cartao">
          <h2>Corrida por semana</h2>
          <Estado consulta={semanas}>{(d) => <GraficoSemanas dados={d} />}</Estado>
        </div>
        <div className="cartao">
          <h2>Última corrida</h2>
          <Estado consulta={ultimo} vazio="Nenhuma corrida ainda.">
            {([t]) => (
              <div className="pilha" style={{ gap: 10 }}>
                <div className="linha entre">
                  <Link to={`/treinos/${t.id}`}><strong>{t.nome ?? 'Corrida'}</strong></Link>
                  <span className="fraco">{dataCurta(t.data)} às {hora(t.data)}</span>
                </div>
                <div className="grade grade-3">
                  <div><div className="rotulo">Distância</div><strong>{km(t.distancia_km)}</strong></div>
                  <div><div className="rotulo">Tempo</div><strong>{duracao(t.tempo_movimento_min)}</strong></div>
                  <div><div className="rotulo">Ritmo</div><strong>{t.ritmo ?? '-'}</strong></div>
                  <div><div className="rotulo">FC média</div><strong>{numero(t.fc_media)} bpm</strong></div>
                  <div><div className="rotulo">Carga</div><strong>{numero(t.carga)}</strong></div>
                  <div><div className="rotulo">Dados</div><EtiquetaQualidadeFc qualidade={t.qualidade_fc} /></div>
                </div>
              </div>
            )}
          </Estado>
        </div>
      </div>

      <div className="cartao">
        <div className="linha entre">
          <h2>Esta semana no plano</h2>
          {plano.data && <Link to="/plano">ver plano completo</Link>}
        </div>
        <Estado consulta={plano} vazio="Nenhum plano ativo. Peça um no chat.">
          {(p) => <SemanasPlano sessoes={p.sessoes ?? []} aderencia={aderencia.data} soSemanaDe={hoje} />}
        </Estado>
      </div>
    </div>
  )
}
