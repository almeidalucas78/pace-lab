import { lazy, Suspense, useEffect, useState } from 'react'
import { NavLink, Route, Routes } from 'react-router'
import { entrou, lerSessao } from './api/cliente'
import { AvisoConexao, BotaoAtualizar } from './componentes/Conexao'
import { ErroTela } from './componentes/ErroTela'
import { AtualizacaoApp } from './componentes/AtualizacaoApp'
import { Sincronizacao } from './componentes/Sincronizacao'
import { VersaoNova } from './componentes/VersaoNova'
import { AbrirApp } from './paginas/AbrirApp'
import { Entrar } from './paginas/Entrar'
import { Token } from './paginas/Token'
import { ehApp } from './plataforma'

// Cada página (e o chat) vira um arquivo separado: gráficos, mapa e markdown só carregam quando abertos.
const VisaoGeral = lazy(() => import('./paginas/VisaoGeral').then((m) => ({ default: m.VisaoGeral })))
const Treinos = lazy(() => import('./paginas/Treinos').then((m) => ({ default: m.Treinos })))
const Treino = lazy(() => import('./paginas/Treino').then((m) => ({ default: m.Treino })))
const Plano = lazy(() => import('./paginas/Plano').then((m) => ({ default: m.Plano })))
const Conectar = lazy(() => import('./paginas/Conectar').then((m) => ({ default: m.Conectar })))
const Conta = lazy(() => import('./paginas/Conta').then((m) => ({ default: m.Conta })))
const Chat = lazy(() => import('./componentes/Chat').then((m) => ({ default: m.Chat })))

const carregando = <div className="carregando">Carregando...</div>

/** Se há alguém logado: token no app, marca da sessão no navegador (o login em si fica no cookie). */
function useEntrou() {
  const [sim, setSim] = useState(entrou)
  useEffect(() => {
    const atualizar = () => setSim(entrou())
    window.addEventListener('pace-lab:token', atualizar)
    window.addEventListener('pace-lab:sessao', atualizar)
    return () => {
      window.removeEventListener('pace-lab:token', atualizar)
      window.removeEventListener('pace-lab:sessao', atualizar)
    }
  }, [])
  return sim
}

export function App() {
  const logado = useEntrou()
  const [chatAberto, setChatAberto] = useState(false)
  // página pública: leva endereço e token do navegador do celular para o app Android
  if (window.location.pathname === '/abrir-app' && !ehApp()) return <AbrirApp />
  if (!logado) return ehApp() ? <Token /> : <Entrar />
  const usuario = ehApp() ? null : lerSessao()

  return (
    <div className={`app ${chatAberto ? 'com-chat' : ''}`}>
      <nav className="menu">
        <div className="marca"><img src="/favicon.svg" width={22} height={22} alt="" /> Pace Lab</div>
        <NavLink to="/" end>Visão geral</NavLink>
        <NavLink to="/treinos">Treinos</NavLink>
        <NavLink to="/plano">Plano</NavLink>
        <NavLink to="/conectar">Conectar celular</NavLink>
        <NavLink to="/conta" title={usuario?.email}>Conta</NavLink>
        <div className="rodape">
          <button className={chatAberto ? 'botao-sec' : 'botao'} onClick={() => setChatAberto(!chatAberto)}>
            {chatAberto ? 'Fechar chat' : 'Treinador (chat)'}
          </button>
          {usuario && <div className="fraco pequeno email-menu" title={usuario.email}>{usuario.email}</div>}
        </div>
      </nav>

      <main className="conteudo">
        <div className="topo-celular">
          <div className="marca"><img src="/favicon.svg" width={22} height={22} alt="" /> Pace Lab</div>
          <div className="linha" style={{ gap: 6 }}>
            <BotaoAtualizar />
            <NavLink to="/conta" className="botao-sec pequeno">Conta</NavLink>
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
            <Route path="/conta" element={<Conta />} />
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
      {ehApp() ? <AtualizacaoApp /> : <VersaoNova /> /* no app os arquivos vêm no APK; atualização baixa um APK novo do PC */}
    </div>
  )
}
