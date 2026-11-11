// Onde o painel está rodando: navegador (PC ou celular) ou app Android (Capacitor, ADR 0013).
import { Capacitor } from '@capacitor/core'

export const ehApp = (): boolean => Capacitor.isNativePlatform()
