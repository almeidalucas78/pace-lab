import { QueryClient } from '@tanstack/react-query'
import { PersistQueryClientProvider } from '@tanstack/react-query-persist-client'
import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter } from 'react-router'
import { App as AppNativo } from '@capacitor/app'
import { conectarPorLink, ErroApi, lerTokenDaUrl } from './api/cliente'
import { opcoesPersistencia } from './api/persistencia'
import { App } from './App'
import { ErroTela } from './componentes/ErroTela'
import { ProvedorContexto } from './contexto'
import './estilo.css'
import { ehApp } from './plataforma'

lerTokenDaUrl() // celular aberto pelo QR code do "Conectar celular"

if (ehApp()) {
  // app aberto pelo link pacelab://conectar (página /abrir-app): guarda endereço do PC e token
  AppNativo.getLaunchUrl().then((l) => { if (l?.url) conectarPorLink(l.url) })
  AppNativo.addListener('appUrlOpen', (e) => { conectarPorLink(e.url) })
}

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

createRoot(document.getElementById('root')!).render(
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
)
