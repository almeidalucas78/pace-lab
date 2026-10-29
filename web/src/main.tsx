import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter } from 'react-router'
import { ErroApi } from './api/cliente'
import { App } from './App'
import { ProvedorContexto } from './contexto'
import './estilo.css'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 60_000,
      refetchOnWindowFocus: false,
      retry: (falhas, erro) => !(erro instanceof ErroApi && erro.status < 500) && falhas < 2,
    },
  },
})

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <ProvedorContexto>
          <App />
        </ProvedorContexto>
      </BrowserRouter>
    </QueryClientProvider>
  </StrictMode>,
)
