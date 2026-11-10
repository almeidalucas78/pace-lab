/// <reference types="vitest/config" />
import { fileURLToPath } from 'node:url'
import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'
import { VitePWA } from 'vite-plugin-pwa'

// No desenvolvimento (`npm run dev`) o painel roda em :5173 e repassa /api para o backend (`treino api`).
// Em uso normal, `treino servico` serve o build (web/dist) e a API no mesmo endereço.
export default defineConfig({
  plugins: [
    react(),
    // App instalável (ADR 0012). O service worker guarda só as telas; os dados ficam no IndexedDB
    // (web/src/api/persistencia.ts). Nunca guarda /api nem as imagens do mapa.
    VitePWA({
      registerType: 'prompt', // versão nova do painel: pergunta antes de recarregar
      includeAssets: ['favicon.svg', 'favicon.ico', 'apple-touch-icon-180x180.png'],
      manifest: {
        name: 'Pace Lab',
        short_name: 'Pace Lab',
        description: 'Seus treinos de corrida, carga, plano e o treinador.',
        lang: 'pt-BR',
        start_url: '/',
        scope: '/',
        display: 'standalone',
        background_color: '#0f1216',
        theme_color: '#2563eb',
        icons: [
          { src: 'pwa-64x64.png', sizes: '64x64', type: 'image/png' },
          { src: 'pwa-192x192.png', sizes: '192x192', type: 'image/png' },
          { src: 'pwa-512x512.png', sizes: '512x512', type: 'image/png' },
          { src: 'maskable-icon-512x512.png', sizes: '512x512', type: 'image/png', purpose: 'maskable' },
        ],
      },
      workbox: {
        globPatterns: ['**/*.{js,css,html,svg,png,ico}'],
        navigateFallback: '/index.html',
        navigateFallbackDenylist: [/^\/api/],
      },
    }),
  ],
  server: {
    proxy: { '/api': 'http://127.0.0.1:8000' },
  },
  // mapas de código-fonte: erros no console do navegador mostram os nomes reais do código
  build: { sourcemap: true },
  test: {
    environment: 'jsdom',
    // o módulo virtual do PWA só existe no build; nos testes usa um substituto
    alias: { 'virtual:pwa-register/react': fileURLToPath(new URL('./src/teste/pwa-register.ts', import.meta.url)) },
  },
})
