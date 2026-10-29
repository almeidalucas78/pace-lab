import { Link, useParams } from 'react-router'
import { useAmostras, usePerfil, useTreino } from '../api/consultas'
import type { DetalheTreino } from '../api/tipos'
import { BarraZonas } from '../componentes/BarraZonas'
import { Estado } from '../componentes/Estado'
import { EtiquetaQualidadeFc } from '../componentes/Etiquetas'
import { GraficosTreino } from '../componentes/GraficosTreino'
import { Mapa } from '../componentes/Mapa'
import { useDescreverPagina } from '../contexto'
import { dataCurta, duracao, esporte, hora, km, numero } from '../util/formato'

function Dado({ rotulo, valor }: { rotulo: string; valor: string }) {
  return <div><div className="rotulo">{rotulo}</div><strong>{valor}</strong></div>
}

function Resumo({ t }: { t: DetalheTreino }) {
  const endurance = ['run', 'walk', 'ride'].includes(t.esporte)
  return (
    <div className="cartao grade grade-4">
      {endurance && <Dado rotulo="Distância" valor={km(t.distancia_km)} />}
      <Dado rotulo="Tempo em movimento" valor={duracao(t.tempo_movimento_min)} />
      {t.ritmo && <Dado rotulo="Ritmo médio" valor={t.ritmo} />}
      <Dado rotulo="FC média / máx." valor={`${numero(t.fc_media)} / ${numero(t.fc_max)} bpm`} />
      <Dado rotulo="Carga (TRIMP)" valor={numero(t.carga)} />
      {t.cadencia_ppm && <Dado rotulo="Cadência" valor={`${numero(t.cadencia_ppm)} ppm`} />}
      {t.ganho_elevacao_m != null && <Dado rotulo="Ganho de elevação" valor={`${numero(t.ganho_elevacao_m)} m`} />}
      {t.temperatura_c != null && (
        <Dado rotulo="Clima" valor={`${numero(t.temperatura_c)} °C${t.umidade_pct != null ? `, ${t.umidade_pct}%` : ''}`} />
      )}
      {t.percepcao_esforco != null && <Dado rotulo="Esforço percebido" valor={`${t.percepcao_esforco}/10`} />}
      {t.tenis && <Dado rotulo="Tênis" valor={t.tenis} />}
    </div>
  )
}

function Parciais({ t }: { t: DetalheTreino }) {
  if (!t.parciais.length) return <div className="vazio">Sem parciais.</div>
  return (
    <table>
      <thead>
        <tr><th>Km</th><th className="num">Ritmo</th><th className="num">FC</th><th className="num">Elevação</th></tr>
      </thead>
      <tbody>
        {t.parciais.map((p) => (
          <tr key={p.km}>
            <td>{p.distancia_m < 990 ? `${p.km} (${p.distancia_m} m)` : p.km}</td>
            <td className="num">{p.ritmo ?? '-'}</td>
            <td className="num">{numero(p.fc_media)}</td>
            <td className="num">{p.elevacao_m != null ? `${p.elevacao_m > 0 ? '+' : ''}${numero(p.elevacao_m, 0)} m` : '-'}</td>
          </tr>
        ))}
      </tbody>
    </table>
  )
}

export function Treino() {
  const id = Number(useParams().id)
  const treino = useTreino(id)
  const amostras = useAmostras(id)
  const perfil = usePerfil()
  const t = treino.data
  useDescreverPagina(t ? `o usuário está vendo o treino #${t.id} (${esporte(t.esporte)} de ${dataCurta(t.data)}`
    + `${t.distancia_km ? `, ${km(t.distancia_km)}` : ''}); use detalhe_treino com esse id` : null)

  return (
    <Estado consulta={treino}>
      {(t) => (
        <div className="pilha">
          <div>
            <Link to="/treinos" className="pequeno">voltar para treinos</Link>
            <div className="linha entre">
              <h1>{t.nome ?? esporte(t.esporte)}</h1>
              <div className="linha">
                {t.possivel_duplicata_de && (
                  <Link to={`/treinos/${t.possivel_duplicata_de}`} className="etiqueta e-neutro">duplicata de #{t.possivel_duplicata_de}</Link>
                )}
                <EtiquetaQualidadeFc qualidade={t.qualidade_fc} />
              </div>
            </div>
            <p className="subtitulo">{esporte(t.esporte)} · {dataCurta(t.data)} às {hora(t.data)} · #{t.id}</p>
          </div>
          {t.descricao && <div className="cartao">{t.descricao}</div>}
          <Resumo t={t} />

          <Estado consulta={amostras} vazio={<div className="cartao vazio">Este treino não tem arquivo com dados ao longo do tempo.</div>}>
            {(a) => (
              <div className="grade grade-2">
                <div className="cartao"><h2>Percurso</h2><Mapa amostras={a} /></div>
                <div className="cartao">
                  <h2>Ao longo do treino</h2>
                  <GraficosTreino amostras={a} mostrarRitmo={t.esporte === 'run' || t.esporte === 'walk'} />
                </div>
              </div>
            )}
          </Estado>

          <div className="grade grade-2">
            <div className="cartao"><h2>Parciais por km</h2><Parciais t={t} /></div>
            <div className="pilha">
              <div className="cartao">
                <h2>Tempo por zona de FC</h2>
                {t.zonas_fc_min ? <BarraZonas zonas={t.zonas_fc_min} faixas={perfil.data?.zonas_fc} />
                  : <div className="vazio">Sem zonas para este treino.</div>}
                {perfil.data?.fc_max_origem === 'estimada' && (
                  <div className="fraco pequeno" style={{ marginTop: 8 }}>
                    Zonas por % da FC máxima <strong>estimada</strong> ({perfil.data.fc_max} bpm).
                  </div>
                )}
              </div>
              <div className="cartao">
                <h2>Sensações</h2>
                {t.sensacoes.length === 0
                  ? <div className="fraco">Nada registrado. Conte no chat como foi.</div>
                  : t.sensacoes.map((s) => (
                    <div key={s.id} style={{ marginBottom: 8 }}>
                      {s.rpe != null && <span className="etiqueta e-destaque">esforço {s.rpe}/10</span>} {s.texto}
                      {s.tags?.length ? <div className="fraco pequeno">{s.tags.join(', ')}</div> : null}
                    </div>
                  ))}
              </div>
            </div>
          </div>
        </div>
      )}
    </Estado>
  )
}
