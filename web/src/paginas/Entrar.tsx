import { useQuery, useQueryClient } from '@tanstack/react-query'
import { useEffect, useState, type FormEvent } from 'react'
import { api, ErroApi } from '../api/cliente'
import { entrouComo } from '../api/sessao'
import type { Usuario } from '../api/tipos'

const SENHA_MINIMA = 8 // a mesma do servidor (auth/senhas.py)

const ERROS_GOOGLE: Record<string, string> = {
  google_cancelado: 'O login com o Google foi cancelado.',
  google_sem_convite: 'Esta conta Google não está na lista de convidados.',
  google_falhou: 'Não deu para entrar com o Google. Tente de novo.',
}

/** `?erro_login=` da volta do Google: mostra a mensagem e tira da barra de endereço. */
function erroDaUrl(): string | null {
  const params = new URLSearchParams(window.location.search)
  const codigo = params.get('erro_login')
  if (!codigo) return null
  params.delete('erro_login')
  const resto = params.toString()
  window.history.replaceState(null, '', window.location.pathname + (resto ? `?${resto}` : ''))
  return ERROS_GOOGLE[codigo] ?? 'Não deu para entrar. Tente de novo.'
}

interface Resposta { usuario: Usuario }

/**
 * Tela de entrar e de criar conta no navegador (fase 9, ADR 0017). O login fica num cookie seguro.
 * `paraApp`: aberta pelo app Android; depois de entrar, o login volta para ele (ConectarApp).
 */
export function Entrar({ paraApp = false }: { paraApp?: boolean }) {
  const qc = useQueryClient()
  const [criando, setCriando] = useState(false)
  const [email, setEmail] = useState('')
  const [nome, setNome] = useState('')
  const [senha, setSenha] = useState('')
  const [confirma, setConfirma] = useState('')
  const [erro, setErro] = useState<string | null>(erroDaUrl)
  const [enviando, setEnviando] = useState(false)
  const opcoes = useQuery({
    queryKey: ['auth', 'opcoes'],
    queryFn: () => api<{ google: boolean }>('/auth/opcoes'),
    staleTime: Infinity,
  })

  // Voltando do Google (ou com a sessão ainda válida no cookie): o servidor diz quem entrou.
  useEffect(() => {
    let vivo = true
    api<Usuario>('/auth/eu').then((u) => { if (vivo) void entrouComo(qc, u) }).catch(() => {})
    return () => { vivo = false }
  }, [qc])

  const problema = criando
    ? senha.length > 0 && senha.length < SENHA_MINIMA ? `A senha precisa ter pelo menos ${SENHA_MINIMA} caracteres.`
      : confirma.length > 0 && confirma !== senha ? 'As senhas não são iguais.' : null
    : null
  const pronto = email.trim().length > 3 && senha.length > 0 && !problema && (!criando || confirma === senha)

  async function enviar(ev: FormEvent) {
    ev.preventDefault()
    setEnviando(true)
    setErro(null)
    try {
      const corpo = criando
        ? { email: email.trim(), senha, nome: nome.trim() || null }
        : { email: email.trim(), senha }
      const r = await api<Resposta>(criando ? '/auth/cadastro' : '/auth/entrar', {
        method: 'POST',
        body: JSON.stringify(corpo),
      })
      await entrouComo(qc, r.usuario)
    } catch (e) {
      setErro(e instanceof ErroApi && e.status === 0
        ? 'Não consegui falar com o servidor. Confira a internet e tente de novo.'
        : e instanceof Error ? primeiraMaiuscula(e.message) : String(e))
    } finally {
      setEnviando(false)
    }
  }

  function trocarModo() {
    setCriando(!criando)
    setErro(null)
    setConfirma('')
  }

  return (
    <div style={{ display: 'grid', placeItems: 'center', minHeight: '100vh', padding: 16 }}>
      <form className="cartao pilha" style={{ width: 'min(420px, 100%)' }} onSubmit={enviar}>
        <div className="linha" style={{ gap: 8 }}>
          <img src="/favicon.svg" width={28} height={28} alt="" />
          <h1 style={{ margin: 0 }}>Pace Lab</h1>
        </div>
        <p className="fraco" style={{ margin: 0 }}>
          {criando ? 'Criar conta' : 'Entre na sua conta'}{paraApp && ' para usar no app Pace Lab'}
        </p>

        {opcoes.data?.google && (
          <>
            <a className="botao-sec botao-google" href="/api/auth/google/iniciar">Entrar com Google</a>
            <div className="separador"><span>ou</span></div>
          </>
        )}

        <label className="rotulo">
          E-mail
          <input className="campo" type="email" autoComplete="email" value={email} required
                 onChange={(e) => setEmail(e.target.value)} autoFocus />
        </label>
        {criando && (
          <label className="rotulo">
            Nome (opcional)
            <input className="campo" type="text" autoComplete="name" value={nome} maxLength={120}
                   onChange={(e) => setNome(e.target.value)} />
          </label>
        )}
        <label className="rotulo">
          Senha
          <input className="campo" type="password" value={senha} required maxLength={128}
                 autoComplete={criando ? 'new-password' : 'current-password'}
                 onChange={(e) => setSenha(e.target.value)} />
        </label>
        {criando && (
          <label className="rotulo">
            Repita a senha
            <input className="campo" type="password" autoComplete="new-password" value={confirma} maxLength={128}
                   onChange={(e) => setConfirma(e.target.value)} />
          </label>
        )}
        {criando && <p className="fraco pequeno" style={{ margin: 0 }}>
          Pelo menos {SENHA_MINIMA} caracteres. Uma frase com algumas palavras é fácil de lembrar e difícil de adivinhar.
        </p>}
        {(problema || erro) && <div className="erro-caixa" role="alert">{problema ?? erro}</div>}
        <button className="botao" disabled={!pronto || enviando}>
          {enviando ? 'Conferindo...' : criando ? 'Criar conta' : 'Entrar'}
        </button>
        <button type="button" className="link-botao" onClick={trocarModo}>
          {criando ? 'Já tenho conta: entrar' : 'Não tem conta? Criar conta'}
        </button>
        {criando && <p className="fraco pequeno" style={{ margin: 0 }}>
          Por enquanto o cadastro é só para convidados.
        </p>}
      </form>
    </div>
  )
}

const primeiraMaiuscula = (s: string) => (s ? s[0].toUpperCase() + s.slice(1) : s)
