import { Link, useSearchParams } from 'react-router'
import { useTreinos } from '../api/consultas'
import { Estado } from '../componentes/Estado'
import { EtiquetaQualidadeFc } from '../componentes/Etiquetas'
import { useDescreverPagina } from '../contexto'
import { dataCurta, duracao, esporte, hora, km, numero } from '../util/formato'

const FILTROS = [['run', 'Corrida'], ['walk', 'Caminhada'], ['ride', 'Pedalada'], ['strength', 'Musculação'], ['', 'Todos']]
const POR_PAGINA = 25

export function Treinos() {
  const [params, setParams] = useSearchParams()
  const filtro = params.get('esporte') ?? 'run'
  const pagina = Number(params.get('pagina') ?? '0')
  const treinos = useTreinos(filtro || null, POR_PAGINA, pagina * POR_PAGINA)
  useDescreverPagina(`o usuário está vendo a lista de treinos (${filtro ? esporte(filtro) : 'todos os esportes'})`)

  const ir = (mudancas: Record<string, string>) => setParams({ esporte: filtro, pagina: String(pagina), ...mudancas })

  return (
    <div className="pilha">
      <div>
        <h1>Treinos</h1>
        <p className="subtitulo">Do mais recente para o mais antigo.</p>
      </div>
      <div className="abas">
        {FILTROS.map(([valor, nome]) => (
          <button key={valor} className={filtro === valor ? 'ativa' : ''} onClick={() => ir({ esporte: valor, pagina: '0' })}>
            {nome}
          </button>
        ))}
      </div>
      <div className="cartao">
        <Estado consulta={treinos} vazio="Nenhum treino.">
          {(lista) => (
            <>
            <div className="so-celular lista-cartoes">
              {lista.map((t) => (
                <Link key={t.id} to={`/treinos/${t.id}`} className="cartao-treino"
                      style={{ opacity: t.possivel_duplicata_de ? 0.5 : 1 }}>
                  <div className="linha entre">
                    <strong>{t.nome ?? esporte(t.esporte)}</strong>
                    <span className="fraco pequeno">{dataCurta(t.data)} {hora(t.data)}</span>
                  </div>
                  <div className="linha fraco pequeno" style={{ gap: 12 }}>
                    {t.distancia_km ? <span>{km(t.distancia_km)}</span> : null}
                    <span>{duracao(t.tempo_movimento_min)}</span>
                    {t.ritmo && <span>{t.ritmo}</span>}
                    {t.fc_media && <span>FC {numero(t.fc_media)}</span>}
                    {t.carga && <span>carga {numero(t.carga)}</span>}
                  </div>
                  {(t.possivel_duplicata_de || t.qualidade_fc !== 'ok') && (
                    <div className="linha" style={{ gap: 4 }}>
                      {t.possivel_duplicata_de && <span className="etiqueta e-neutro">duplicata</span>}
                      {t.qualidade_fc !== 'ok' && <EtiquetaQualidadeFc qualidade={t.qualidade_fc} />}
                    </div>
                  )}
                </Link>
              ))}
            </div>
            <table className="so-desktop">
              <thead>
                <tr>
                  <th>Data</th><th>Treino</th><th className="num">Distância</th><th className="num">Tempo</th>
                  <th className="num">Ritmo</th><th className="num">FC média</th><th className="num">Carga</th><th />
                </tr>
              </thead>
              <tbody>
                {lista.map((t) => (
                  <tr key={t.id} style={{ opacity: t.possivel_duplicata_de ? 0.5 : 1 }}>
                    <td>{dataCurta(t.data)} <span className="fraco">{hora(t.data)}</span></td>
                    <td>
                      <Link to={`/treinos/${t.id}`}>{t.nome ?? esporte(t.esporte)}</Link>
                      {!filtro && <span className="fraco pequeno"> · {esporte(t.esporte)}</span>}
                      {t.possivel_duplicata_de && <span className="etiqueta e-neutro" style={{ marginLeft: 6 }}>duplicata</span>}
                    </td>
                    <td className="num">{t.distancia_km ? km(t.distancia_km) : '-'}</td>
                    <td className="num">{duracao(t.tempo_movimento_min)}</td>
                    <td className="num">{t.ritmo ?? '-'}</td>
                    <td className="num">{numero(t.fc_media)}</td>
                    <td className="num">{numero(t.carga)}</td>
                    <td>{t.qualidade_fc !== 'ok' && <EtiquetaQualidadeFc qualidade={t.qualidade_fc} />}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            </>
          )}
        </Estado>
        <div className="linha entre" style={{ marginTop: 12 }}>
          <button className="botao-sec" disabled={pagina === 0} onClick={() => ir({ pagina: String(pagina - 1) })}>
            Mais recentes
          </button>
          <span className="fraco pequeno">página {pagina + 1}</span>
          <button className="botao-sec" disabled={(treinos.data?.length ?? 0) < POR_PAGINA}
                  onClick={() => ir({ pagina: String(pagina + 1) })}>
            Mais antigos
          </button>
        </div>
      </div>
    </div>
  )
}
