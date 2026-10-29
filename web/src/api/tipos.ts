// Tipos das respostas da API. Escritos à mão a partir de treino/services.py (ADR 0011):
// ao mudar um dict de resposta no Python, atualize aqui.

export type Esporte = 'run' | 'walk' | 'ride' | 'strength' | 'workout' | 'other' | 'rest'

export interface ResumoTreino {
  id: number
  data: string // ISO no fuso local
  esporte: Esporte
  tipo_original: string | null
  nome: string | null
  distancia_km: number | null
  tempo_movimento_min: number | null
  ritmo: string | null
  fc_media: number | null
  fc_max: number | null
  cadencia_ppm: number | null
  ganho_elevacao_m: number | null
  temperatura_c: number | null
  umidade_pct: number | null
  tenis: string | null
  carga: number | null
  qualidade_fc: 'ok' | 'suspeita' | 'suspeita_cadencia' | 'sem_fc'
  possivel_duplicata_de: number | null
  arquivo: string
}

export interface Parcial {
  km: number
  distancia_m: number
  ritmo: string | null
  fc_media: number | null
  elevacao_m: number | null
}

export interface Sensacao {
  id: number
  dia: string
  treino_id: number | null
  rpe: number | null
  texto: string
  tags: string[] | null
}

export interface DetalheTreino extends ResumoTreino {
  descricao: string | null
  percepcao_esforco: number | null
  zonas_fc_min: Record<string, number> | null
  parciais: Parcial[]
  observacoes_dados: Record<string, unknown>
  sensacoes: Sensacao[]
}

export interface Amostra {
  t: number
  lat: number | null
  lon: number | null
  ele: number | null
  fc: number | null
  cad: number | null
  vel: number | null
  dist: number | null
}

export interface Semana {
  semana: string
  treinos: number
  km: number
  tempo_min: number
  ritmo_medio: string | null
  maior_treino_km: number
  carga: number
}

export interface DiaCarga {
  dia: string
  carga: number
  fitness: number
  fadiga: number
  forma: number
}

export interface CargaAtual {
  hoje: DiaCarga
  ha_7_dias: DiaCarga | null
  ha_28_dias: DiaCarga | null
  carga_7_dias: number
  fc_max_usada: number | null
  fc_max_origem: string
  aviso?: string
}

export interface Perfil {
  fc_max: number | null
  fc_max_origem: 'configurada' | 'estimada' | 'indisponivel'
  fc_max_observacao: string | null
  fc_repouso: number | null
  zonas_fc: Record<string, string> | null
}

export interface SessaoPlano {
  id: number
  dia: string
  dia_semana: string
  esporte: Esporte
  tipo: string
  descricao?: string
  distancia_km?: number
  duracao_min?: number
  ritmo?: string
  zona_fc?: string
  esforco?: number
  notas?: string
  status?: 'cancelada'
}

export interface Plano {
  id: number
  titulo: string
  objetivo?: string
  inicio: string
  fim: string
  status: 'ativo' | 'arquivado' | 'substituido'
  substituido_por?: number
  conversa_id?: number
  notas?: string
  criado: string
  sessoes?: SessaoPlano[]
}

export type StatusSessao = 'feita' | 'feita_outro_dia' | 'perdida' | 'futura' | 'pendente_hoje' | 'cancelada' | 'descanso'

export interface Comparacao {
  distancia?: { alvo_km: number; feito_km: number; pct: number | null }
  duracao?: { alvo_min: number; feito_min: number; pct: number | null }
  ritmo?: { alvo: string; feito: string | null; situacao: 'dentro' | 'mais_rapido' | 'mais_lento' }
  zona_fc?: { alvo: string; pct_na_zona: number; pct_acima: number; pct_abaixo: number }
  esforco?: { alvo: number; feito: number }
}

export interface LinhaAderencia {
  sessao_id: number
  dia: string
  esporte: Esporte
  tipo: string
  descricao?: string
  status: StatusSessao
  treino_id?: number
  treino_dia?: string
  comparacao?: Comparacao
  no_alvo?: boolean
}

export interface Aderencia {
  plano: Plano
  resumo: {
    sessoes_vencidas: number
    feitas: number
    perdidas: number
    pct_feitas: number | null
    feitas_no_alvo: number
    futuras: number
    extras: number
  }
  semanas: {
    semana: string
    planejadas: number
    feitas: number
    perdidas: number
    no_alvo: number
    km_planejados: number
    km_feitos: number
  }[]
  sessoes: LinhaAderencia[]
  extras: { treino_id: number; dia: string; esporte: Esporte; nome: string | null; distancia_km: number | null }[]
  observacao?: string
}

export interface ConversaResumo {
  id: number
  titulo: string | null
  provedor: 'claude' | 'gemini'
  atualizada: string
}

export interface MensagemChat {
  papel: 'user' | 'assistant'
  texto: string
  quando: string
  ferramentas: string[] | null
}

export interface Conversa extends ConversaResumo {
  criada: string
  mensagens: MensagemChat[]
}

export interface RespostaChat {
  conversa_id: number
  provedor: 'claude' | 'gemini'
  resposta: string
  ferramentas: string[]
}
