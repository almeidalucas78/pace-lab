// Entrar e sair no navegador: marca quem entrou e cuida dos dados guardados no aparelho (ADR 0012).

import type { QueryClient } from '@tanstack/react-query'
import { ehApp } from '../plataforma'
import { api, salvarSessao, salvarToken, ultimaConta } from './cliente'
import { apagarDadosGuardados } from './persistencia'
import type { Usuario } from './tipos'

/** Depois do login: se a última conta deste aparelho era outra, apaga os dados dela antes de mostrar a nova. */
export async function entrouComo(qc: QueryClient, u: Usuario): Promise<void> {
  const anterior = ultimaConta()
  if (anterior !== null && anterior !== u.id) await apagarDadosGuardados(qc)
  salvarSessao(u)
}

/** Encerra a sessão no servidor (apaga os cookies) e os dados guardados neste aparelho. */
export async function sair(qc: QueryClient, todos = false): Promise<void> {
  if (!ehApp()) {
    try {
      await api(todos ? '/auth/sair-de-todos' : '/auth/sair', { method: 'POST' })
    } catch {
      // sem rede ou sessão já vencida: sai deste aparelho mesmo assim
    }
  }
  await apagarDadosGuardados(qc)
  if (ehApp()) salvarToken(null)
  else salvarSessao(null)
}
