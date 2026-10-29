/// <reference types="vitest/config" />
import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// No desenvolvimento (`npm run dev`) o painel roda em :5173 e repassa /api para o backend (`treino api`).
// Em uso normal, `treino servico` serve o build (web/dist) e a API no mesmo endereço.
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: { '/api': 'http://127.0.0.1:8000' },
  },
  test: {
    environment: 'jsdom',
  },
})
