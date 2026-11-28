import { QueryClient } from '@tanstack/react-query'
import { PersistQueryClientProvider } from '@tanstack/react-query-persist-client'
import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter } from 'react-router'
import { App as AppNativo } from '@capacitor/app'
import { carregarTokens, ErroApi } from './api/cliente'
import { concluirLoginApp } from './api/loginApp'
import { opcoesPersistencia } from './api/persistencia'
import { App } from './App'
import { ErroTela } from './componentes/ErroTela'
import { ProvedorContexto } from './contexto'
import './estilo.css'
import { guardarDesafioDaUrl } from './paginas/ConectarApp'
import { ehApp } from './plataforma'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 60_000,
      // Infinity = não descarta da memória (sem timer). Não usar VALIDADE_MS: 30 dias passa do limite do
      // setTimeout (~24,8 dias), o timer dispara na hora e os dados restaurados do aparelho sumiam.
      gcTime: Infinity,
      refetchOnWindowFocus: true, // voltar para o app busca dados novos
      retry: (falhas, erro) => !(erro instanceof ErroApi && erro.status < 500 && erro.status !== 0) && falhas < 2,
    },
  },
})

if (!ehApp()) guardarDesafioDaUrl() // navegador do celular aberto pelo app para entrar (/entrar-app)
else {
  // volta do login feito no navegador: pacelab://entrou?codigo=...
  AppNativo.getLaunchUrl().then((l) => { if (l?.url) void concluirLoginApp(l.url, queryClient) })
  AppNativo.addListener('appUrlOpen', (e) => { void concluirLoginApp(e.url, queryClient) })
}

// No app, os tokens vêm do cofre do Android antes da primeira tela (senão ela pediria login à toa).
void carregarTokens().finally(() => createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <PersistQueryClientProvider client={queryClient} persistOptions={opcoesPersistencia()}>
      <BrowserRouter>
        <ProvedorContexto>
          <ErroTela area="o painel">
            <App />
          </ErroTela>
        </ProvedorContexto>
      </BrowserRouter>
    </PersistQueryClientProvider>
  </StrictMode>,
))
