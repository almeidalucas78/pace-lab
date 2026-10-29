// Consultas à API com cache (TanStack Query). As chaves começam pelo recurso para invalidar em grupo.

import { useQuery } from '@tanstack/react-query'
import { ErroApi, api } from './cliente'
import type {
  Aderencia, Amostra, CargaAtual, Conversa, ConversaResumo, DetalheTreino, DiaCarga, Perfil, Plano,
  ResumoTreino, Semana,
} from './tipos'

/** 404 em "plano ativo" quer dizer "não há plano", não erro. */
async function ouNulo<T>(p: Promise<T>): Promise<T | null> {
  try {
    return await p
  } catch (e) {
    if (e instanceof ErroApi && e.status === 404) return null
    throw e
  }
}

export const useCargaAtual = () =>
  useQuery({ queryKey: ['carga', 'atual'], queryFn: () => api<CargaAtual>('/carga/atual') })

export const useSerieCarga = (dias = 90) =>
  useQuery({ queryKey: ['carga', 'serie', dias], queryFn: () => api<DiaCarga[]>(`/load?days=${dias}`) })

export const useSemanas = (n = 12, esporte = 'run') =>
  useQuery({ queryKey: ['semanas', n, esporte], queryFn: () => api<Semana[]>(`/weeks?n=${n}&sport=${esporte}`) })

export const usePerfil = () => useQuery({ queryKey: ['perfil'], queryFn: () => api<Perfil>('/perfil') })

export const useTreinos = (esporte: string | null, limite: number, offset: number) =>
  useQuery({
    queryKey: ['treinos', esporte, limite, offset],
    queryFn: () => {
      const q = new URLSearchParams({ limit: String(limite), offset: String(offset) })
      if (esporte) q.set('sport', esporte)
      return api<ResumoTreino[]>(`/activities?${q}`)
    },
    placeholderData: (anterior) => anterior,
  })

export const useTreino = (id: number) =>
  useQuery({ queryKey: ['treinos', 'detalhe', id], queryFn: () => api<DetalheTreino>(`/activities/${id}`) })

export const useAmostras = (id: number) =>
  useQuery({
    queryKey: ['treinos', 'amostras', id],
    queryFn: () => api<Amostra[]>(`/activities/${id}/samples?every_s=5`),
    staleTime: Infinity, // amostras de um treino não mudam
  })

export const usePlanoAtivo = () =>
  useQuery({ queryKey: ['planos', 'ativo'], queryFn: () => ouNulo(api<Plano>('/planos/ativo')) })

export const useAderenciaAtiva = () =>
  useQuery({ queryKey: ['planos', 'ativo', 'aderencia'], queryFn: () => ouNulo(api<Aderencia>('/planos/ativo/aderencia')) })

export const usePlano = (id: number) =>
  useQuery({ queryKey: ['planos', id], queryFn: () => api<Plano>(`/planos/${id}`) })

export const useAderencia = (id: number) =>
  useQuery({ queryKey: ['planos', id, 'aderencia'], queryFn: () => api<Aderencia>(`/planos/${id}/aderencia`) })

export const usePlanos = () => useQuery({ queryKey: ['planos', 'lista'], queryFn: () => api<Plano[]>('/planos') })

export const useConversas = () =>
  useQuery({ queryKey: ['conversas'], queryFn: () => api<ConversaResumo[]>('/chat/conversas') })

export const useConversa = (id: number | null) =>
  useQuery({
    queryKey: ['conversas', id],
    queryFn: () => api<Conversa>(`/chat/conversas/${id}`),
    enabled: id != null,
  })
