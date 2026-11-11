// Aviso de versão nova do app Android, com o plugin nativo simulado (o Kotlin só roda no celular).
import { act } from 'react'
import { createRoot } from 'react-dom/client'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { salvarToken } from '../api/cliente'
import type { EventoInstalacao, PluginAtualizacao } from '../atualizacao'
import { AtualizacaoApp } from './AtualizacaoApp'

;(globalThis as { IS_REACT_ACT_ENVIRONMENT?: boolean }).IS_REACT_ACT_ENVIRONMENT = true

vi.mock('@capacitor/app', () => ({
  App: { addListener: vi.fn(async () => ({ remove: vi.fn() })), getInfo: vi.fn() },
}))

const espera = () => act(async () => { await new Promise((r) => setTimeout(r, 20)) })

function pluginFalso(permitido = true) {
  const ouvintes: Record<string, (e: unknown) => void> = {}
  const plugin = {
    podeInstalar: vi.fn(async () => ({ permitido })),
    abrirPermissao: vi.fn(async () => {}),
    instalar: vi.fn(async () => {}),
    addListener: vi.fn(async (ev: string, f: (e: unknown) => void) => {
      ouvintes[ev] = f
      return { remove: vi.fn(async () => {}) }
    }),
  }
  return { plugin: plugin as unknown as PluginAtualizacao & typeof plugin, ouvintes }
}

function versaoNoPc(codigo: number | null) {
  vi.spyOn(globalThis, 'fetch').mockImplementation(async () =>
    new Response(JSON.stringify({ codigo, nome: `0.7.${codigo}`, tamanho: 9_437_184, sha256: 'abc' }), { status: 200 }))
}

let raiz: ReturnType<typeof createRoot> | null = null
async function montar(plugin: PluginAtualizacao, instalada = 10) {
  const div = document.createElement('div')
  document.body.appendChild(div)
  raiz = createRoot(div)
  await act(async () => { raiz!.render(<AtualizacaoApp plugin={plugin} instalada={async () => instalada} />) })
  await espera()
  return div
}

async function clicar(div: HTMLElement, rotulo: string) {
  const botao = [...div.querySelectorAll('button')].find((b) => b.textContent === rotulo)!
  await act(async () => { botao.click() })
  await espera()
}

beforeEach(() => {
  localStorage.clear()
  salvarToken('t')
})
afterEach(() => {
  act(() => raiz?.unmount())
  document.body.innerHTML = ''
  vi.restoreAllMocks()
})

describe('atualização do app', () => {
  it('não mostra nada quando a versão instalada é a mais nova', async () => {
    versaoNoPc(10)
    const div = await montar(pluginFalso().plugin)
    expect(globalThis.fetch).toHaveBeenCalled()
    expect(div.innerHTML).toBe('')
  })

  it('oferece a versão nova, baixa com token e hash e pede confirmação', async () => {
    versaoNoPc(12)
    const { plugin, ouvintes } = pluginFalso()
    const div = await montar(plugin)
    expect(div.textContent).toContain('Versão nova do app: 0.7.12 (9,0 MB)')
    await clicar(div, 'Atualizar')
    expect(plugin.instalar).toHaveBeenCalledWith({ url: '/api/app/apk', token: 't', sha256: 'abc' })
    expect(div.textContent).toContain('Confirme a instalação')
    act(() => ouvintes.instalacao({ status: 'falhou', mensagem: 'cancelado' } satisfies EventoInstalacao))
    expect(div.textContent).toContain('Não foi possível atualizar: cancelado')
  })

  it('sem permissão de instalar apps, abre a configuração do Android', async () => {
    versaoNoPc(12)
    const { plugin } = pluginFalso(false)
    const div = await montar(plugin)
    await clicar(div, 'Atualizar')
    expect(plugin.abrirPermissao).toHaveBeenCalled()
    expect(plugin.instalar).not.toHaveBeenCalled()
    expect(div.textContent).toContain('Permita que o Pace Lab instale apps')
  })

  it('PC fora do ar: fica quieto', async () => {
    vi.spyOn(globalThis, 'fetch').mockRejectedValue(new TypeError('Failed to fetch'))
    const div = await montar(pluginFalso().plugin)
    expect(div.innerHTML).toBe('')
  })
})
