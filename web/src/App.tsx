import { useQueryClient } from '@tanstack/react-query'
import { lazy, Suspense, useEffect, useState } from 'react'
import { NavLink, Route, Routes } from 'react-router'
import { lerToken, salvarToken } from './api/cliente'
import { apagarDadosGuardados } from './api/persistencia'
import { AvisoConexao, BotaoAtualizar } from './componentes/Conexao'
import { ErroTela } from './componentes/ErroTela'
import { Sincronizacao } from './componentes/Sincronizacao'
import { VersaoNova } from './componentes/VersaoNova'
import { AbrirApp } from './paginas/AbrirApp'
import { Token } from './paginas/Token'
import { ehApp } from './plataforma'

// Cada página (e o chat) vira um arquivo separado: gráficos, mapa e markdown só carregam quando abertos.
const VisaoGeral = lazy(() => import('./paginas/VisaoGeral').then((m) => ({ default: m.VisaoGeral })))
const Treinos = lazy(() => import('./paginas/Treinos').then((m) => ({ default: m.Treinos })))
const Treino = lazy(() => import('./paginas/Treino').then((m) => ({ default: m.Treino })))
const Plano = lazy(() => import('./paginas/Plano').then((m) => ({ default: m.Plano })))
const Conectar = lazy(() => import('./paginas/Conectar').then((m) => ({ default: m.Conectar })))
const Chat = lazy(() => import('./componentes/Chat').then((m) => ({ default: m.Chat })))

const carregando = <div className="carregando">Carregando...</div>

function useToken() {
  const [token, setToken] = useState(lerToken)
  useEffect(() => {
    const atualizar = () => setToken(lerToken())
    window.addEventListener('pace-lab:token', atualizar)
    return () => window.removeEventListener('pace-lab:token', atualizar)
  }, [])
  return token
}

export function App() {
  const token = useToken()
  const qc = useQueryClient()
  const [chatAberto, setChatAberto] = useState(false)
  // página pública: leva endereço e token do navegador do celular para o app Android
  if (window.location.pathname === '/abrir-app' && !ehApp()) return <AbrirApp />
  if (!token) return <Token />

  async function sair() {
    await apagarDadosGuardados(qc) // dados guardados neste aparelho também saem
    salvarToken(null)
  }

  return (
    <div className={`app ${chatAberto ? 'com-chat' : ''}`}>
      <nav className="menu">
        <div className="marca"><img src="/favicon.svg" width={22} height={22} alt="" /> Pace Lab</div>
        <NavLink to="/" end>Visão geral</NavLink>
        <NavLink to="/treinos">Treinos</NavLink>
        <NavLink to="/plano">Plano</NavLink>
        <NavLink to="/conectar">Conectar celular</NavLink>
        <div className="rodape">
          <button className={chatAberto ? 'botao-sec' : 'botao'} onClick={() => setChatAberto(!chatAberto)}>
            {chatAberto ? 'Fechar chat' : 'Treinador (chat)'}
          </button>
          <button className="botao-sec pequeno" onClick={sair}>Sair</button>
        </div>
      </nav>

      <main className="conteudo">
        <div className="topo-celular">
          <div className="marca"><img src="/favicon.svg" width={22} height={22} alt="" /> Pace Lab</div>
          <div className="linha" style={{ gap: 6 }}>
            <BotaoAtualizar />
            <button className="botao-sec pequeno" onClick={sair}>Sair</button>
          </div>
        </div>
        {ehApp() && <Sincronizacao />}
        <AvisoConexao />
        <ErroTela area="a página">
        <Suspense fallback={carregando}>
          <Routes>
            <Route path="/" element={<VisaoGeral />} />
            <Route path="/treinos" element={<Treinos />} />
            <Route path="/treinos/:id" element={<Treino />} />
            <Route path="/plano" element={<Plano />} />
            <Route path="/plano/:id" element={<Plano />} />
            <Route path="/chat" element={<Chat pagina />} />
            <Route path="/conectar" element={<Conectar />} />
            <Route path="*" element={<div className="vazio">Página não encontrada.</div>} />
          </Routes>
        </Suspense>
        </ErroTela>
      </main>

      {chatAberto && (
        <ErroTela area="o chat">
          <Suspense fallback={null}><Chat fechar={() => setChatAberto(false)} /></Suspense>
        </ErroTela>
      )}

      <nav className="barra-inferior">
        <NavLink to="/" end>Visão geral</NavLink>
        <NavLink to="/treinos">Treinos</NavLink>
        <NavLink to="/plano">Plano</NavLink>
        <NavLink to="/chat">Chat</NavLink>
      </nav>
      {!ehApp() && <VersaoNova /> /* no app os arquivos vêm no APK; atualização é pelo app */}
    </div>
  )
}
