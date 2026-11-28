// Cofre do Android para os tokens de login (android/.../CofrePlugin.kt, ADR 0015): AES-GCM com chave no Keystore.
import { registerPlugin } from '@capacitor/core'

export interface PluginCofre {
  ler(opcoes: { chave: string }): Promise<{ valor?: string | null }>
  gravar(opcoes: { chave: string; valor: string }): Promise<void>
  apagar(opcoes: { chave: string }): Promise<void>
}

export const cofre = registerPlugin<PluginCofre>('Cofre')
