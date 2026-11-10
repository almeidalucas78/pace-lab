// Substitui o módulo virtual `virtual:pwa-register/react` nos testes (ele só existe no build do vite-plugin-pwa).
import { useState } from 'react'

export function useRegisterSW() {
  return {
    needRefresh: useState(false),
    offlineReady: useState(false),
    updateServiceWorker: async () => {},
  }
}
