import { useEffect, useState } from 'react'
import { NavLink, Route, Routes } from 'react-router'
import { lerToken, salvarToken } from './api/cliente'
import { Chat } from './componentes/Chat'
import { Plano } from './paginas/Plano'
import { Token } from './paginas/Token'
import { Treino } from './paginas/Treino'
import { Treinos } from './paginas/Treinos'
import { VisaoGeral } from './paginas/VisaoGeral'

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
  const [chatAberto, setChatAberto] = useState(false)
  if (!token) return <Token />

  return (
    <div className={`app ${chatAberto ? 'com-chat' : ''}`}>
      <nav className="menu">
        <div className="marca"><img src="/favicon.svg" width={22} height={22} alt="" /> Pace Lab</div>
        <NavLink to="/" end>Visão geral</NavLink>
        <NavLink to="/treinos">Treinos</NavLink>
        <NavLink to="/plano">Plano</NavLink>
        <div className="rodape">
          <button className={chatAberto ? 'botao-sec' : 'botao'} onClick={() => setChatAberto(!chatAberto)}>
            {chatAberto ? 'Fechar chat' : 'Treinador (chat)'}
          </button>
          <button className="botao-sec pequeno" onClick={() => salvarToken(null)}>Sair</button>
        </div>
      </nav>
      <main className="conteudo">
        <Routes>
          <Route path="/" element={<VisaoGeral />} />
          <Route path="/treinos" element={<Treinos />} />
          <Route path="/treinos/:id" element={<Treino />} />
          <Route path="/plano" element={<Plano />} />
          <Route path="/plano/:id" element={<Plano />} />
          <Route path="*" element={<div className="vazio">Página não encontrada.</div>} />
        </Routes>
      </main>
      {chatAberto && <Chat fechar={() => setChatAberto(false)} />}
    </div>
  )
}
