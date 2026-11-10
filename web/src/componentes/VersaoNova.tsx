import { useRegisterSW } from 'virtual:pwa-register/react'

/** Registra o service worker (app instalável) e avisa quando há versão nova do painel. */
export function VersaoNova() {
  const { needRefresh: [temVersaoNova, setTemVersaoNova], updateServiceWorker } = useRegisterSW()
  if (!temVersaoNova) return null
  return (
    <div className="aviso-versao">
      <span>Há uma versão nova do painel.</span>
      <button className="botao" onClick={() => updateServiceWorker(true)}>Atualizar agora</button>
      <button className="botao-sec" onClick={() => setTemVersaoNova(false)}>Depois</button>
    </div>
  )
}
