import type { ResumoTreino, StatusSessao } from '../api/tipos'
import { STATUS_SESSAO } from '../util/formato'

const CLASSE_STATUS: Record<StatusSessao, string> = {
  feita: 'e-ok', feita_outro_dia: 'e-ok', perdida: 'e-erro', futura: 'e-neutro',
  pendente_hoje: 'e-destaque', cancelada: 'e-neutro', descanso: 'e-neutro',
}

export function EtiquetaStatus({ status }: { status: StatusSessao }) {
  return <span className={`etiqueta ${CLASSE_STATUS[status]}`}>{STATUS_SESSAO[status]}</span>
}

export function EtiquetaAlvo({ noAlvo }: { noAlvo: boolean | undefined }) {
  if (noAlvo === undefined) return null
  return noAlvo
    ? <span className="etiqueta e-ok">no alvo</span>
    : <span className="etiqueta e-alerta">fora do alvo</span>
}

const QUALIDADE: Record<ResumoTreino['qualidade_fc'], [string, string]> = {
  ok: ['FC ok', 'e-ok'],
  suspeita: ['FC suspeita', 'e-alerta'],
  suspeita_cadencia: ['FC colada na cadência', 'e-alerta'],
  sem_fc: ['sem FC', 'e-neutro'],
}

export function EtiquetaQualidadeFc({ qualidade }: { qualidade: ResumoTreino['qualidade_fc'] }) {
  const [texto, classe] = QUALIDADE[qualidade]
  return <span className={`etiqueta ${classe}`} title="qualidade da frequência cardíaca">{texto}</span>
}
