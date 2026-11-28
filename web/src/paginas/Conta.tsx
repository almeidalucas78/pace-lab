import { useQueryClient } from '@tanstack/react-query'
import { useState, type FormEvent } from 'react'
import { api, ErroApi, lerSessao } from '../api/cliente'
import { usePerfil } from '../api/consultas'
import { sair } from '../api/sessao'
import type { Perfil, RelatorioImportacao } from '../api/tipos'
import { Estado } from '../componentes/Estado'
import { useDescreverPagina } from '../contexto'

const SENHA_MINIMA = 8

const mensagem = (e: unknown) =>
  e instanceof ErroApi && e.status === 0 ? 'Sem conexão com o servidor. Tente de novo.'
    : e instanceof Error ? e.message : String(e)

/** Conta: quem entrou, FC e fuso, importação do Strava, senha e sair (fase 9, etapa 7). */
export function Conta() {
  useDescreverPagina('o usuário está na página da conta (FC, fuso, importação do Strava, senha)')
  const usuario = lerSessao()
  return (
    <div className="pilha" style={{ maxWidth: 680 }}>
      <div>
        <h1>Conta</h1>
        <p className="subtitulo">
          {usuario ? <>{usuario.nome ? `${usuario.nome} · ` : ''}{usuario.email}</> : 'Conectado.'}
        </p>
      </div>
      <Coracao />
      <ImportarStrava />
      {usuario && <TrocarSenha temSenha={usuario.senha} />}
      <Saida />
    </div>
  )
}

function Coracao() {
  const perfil = usePerfil()
  return (
    <section className="cartao pilha">
      <h2>Frequência cardíaca e fuso</h2>
      <Estado consulta={perfil}>{(p) => <FormCoracao perfil={p} />}</Estado>
    </section>
  )
}

const FUSOS: string[] = (() => {
  try {
    return Intl.supportedValuesOf('timeZone')
  } catch {
    return []
  }
})()

function FormCoracao({ perfil }: { perfil: Perfil }) {
  const qc = useQueryClient()
  const [fcMax, setFcMax] = useState(perfil.fc_max_origem === 'configurada' && perfil.fc_max ? String(Math.round(perfil.fc_max)) : '')
  const [fcRepouso, setFcRepouso] = useState(perfil.fc_repouso ? String(perfil.fc_repouso) : '')
  const [fuso, setFuso] = useState(perfil.fuso)
  const [aviso, setAviso] = useState<{ ok: boolean; texto: string } | null>(null)
  const [salvando, setSalvando] = useState(false)
  const opcoesFuso = FUSOS.includes(fuso) ? FUSOS : [fuso, ...FUSOS]

  async function salvar(ev: FormEvent) {
    ev.preventDefault()
    setSalvando(true)
    setAviso(null)
    try {
      const novo = await api<Perfil>('/perfil/ajustes', {
        method: 'POST',
        body: JSON.stringify({ fc_max: Number(fcMax) || 0, fc_repouso: Number(fcRepouso) || 0, fuso }),
      })
      qc.setQueryData(['perfil'], novo)
      await qc.invalidateQueries() // zonas, carga e datas mudam com FC e fuso
      setAviso({ ok: true, texto: 'Salvo. Zonas e carga foram recalculadas.' })
    } catch (e) {
      setAviso({ ok: false, texto: mensagem(e) })
    } finally {
      setSalvando(false)
    }
  }

  const estimada = perfil.fc_max_origem === 'estimada' && perfil.fc_max ? Math.round(perfil.fc_max) : null
  return (
    <form className="pilha" onSubmit={salvar}>
      <div className="grade-campos">
        <label className="rotulo">
          FC máxima (bpm)
          <input className="campo" type="number" inputMode="numeric" min={120} max={240} value={fcMax}
                 placeholder={estimada ? `estimada: ${estimada}` : 'estimar pelos treinos'}
                 onChange={(e) => setFcMax(e.target.value)} />
        </label>
        <label className="rotulo">
          FC de repouso (bpm)
          <input className="campo" type="number" inputMode="numeric" min={30} max={120} value={fcRepouso}
                 placeholder="opcional" onChange={(e) => setFcRepouso(e.target.value)} />
        </label>
        <label className="rotulo">
          Fuso horário
          {opcoesFuso.length > 1 ? (
            <select className="campo" value={fuso} onChange={(e) => setFuso(e.target.value)}>
              {opcoesFuso.map((f) => <option key={f} value={f}>{f.replaceAll('_', ' ')}</option>)}
            </select>
          ) : (
            <input className="campo" value={fuso} onChange={(e) => setFuso(e.target.value)} />
          )}
        </label>
      </div>
      <p className="fraco pequeno" style={{ margin: 0 }}>
        Deixe a FC máxima vazia para estimar pelos seus treinos. Com um valor medido em teste, as zonas ficam mais certas.
      </p>
      {aviso && <div className={aviso.ok ? 'ok-caixa' : 'erro-caixa'} role="status">{aviso.texto}</div>}
      <div><button className="botao" disabled={salvando}>{salvando ? 'Salvando...' : 'Salvar'}</button></div>
    </form>
  )
}

function ImportarStrava() {
  const qc = useQueryClient()
  const [arquivo, setArquivo] = useState<File | null>(null)
  const [enviando, setEnviando] = useState(false)
  const [resultado, setResultado] = useState<RelatorioImportacao | null>(null)
  const [erro, setErro] = useState<string | null>(null)

  async function enviar(ev: FormEvent) {
    ev.preventDefault()
    if (!arquivo) return
    setEnviando(true)
    setErro(null)
    setResultado(null)
    try {
      const r = await api<RelatorioImportacao>('/importar/strava', {
        method: 'POST',
        body: arquivo,
        headers: { 'Content-Type': 'application/zip' },
      })
      setResultado(r)
      await qc.invalidateQueries()
    } catch (e) {
      setErro(mensagem(e))
    } finally {
      setEnviando(false)
    }
  }

  return (
    <section className="cartao pilha">
      <h2>Importar do Strava</h2>
      <p className="fraco" style={{ margin: 0 }}>
        No site do Strava, em <strong>Configurações &gt; Minha conta</strong>, peça o arquivo com todos os seus dados.
        O Strava manda um link por e-mail (pode levar algumas horas). Envie aqui o <code>.zip</code> baixado.
        Mandar de novo só atualiza: nada fica duplicado.
      </p>
      <form className="linha" onSubmit={enviar}>
        <input className="campo" type="file" accept=".zip,application/zip"
               onChange={(e) => { setArquivo(e.target.files?.[0] ?? null); setResultado(null); setErro(null) }} />
        <button className="botao" disabled={!arquivo || enviando}>{enviando ? 'Importando...' : 'Enviar'}</button>
      </form>
      {enviando && <p className="fraco pequeno" style={{ margin: 0 }}>Pode levar alguns minutos. Deixe esta página aberta.</p>}
      {resultado && (
        <div className="ok-caixa" role="status">
          {resultado.atividades} treinos no arquivo: {resultado.novas ?? 0} novos e {resultado.atualizadas ?? 0} atualizados.
          {resultado.erros.length > 0 && ` ${resultado.erros.length} arquivos de treino não puderam ser lidos.`}
        </div>
      )}
      {erro && <div className="erro-caixa" role="alert">{erro}</div>}
    </section>
  )
}

function TrocarSenha({ temSenha }: { temSenha: boolean }) {
  const [atual, setAtual] = useState('')
  const [nova, setNova] = useState('')
  const [confirma, setConfirma] = useState('')
  const [aviso, setAviso] = useState<{ ok: boolean; texto: string } | null>(null)
  const [salvando, setSalvando] = useState(false)
  const problema = nova.length > 0 && nova.length < SENHA_MINIMA ? `A senha precisa ter pelo menos ${SENHA_MINIMA} caracteres.`
    : confirma.length > 0 && confirma !== nova ? 'As senhas não são iguais.' : null

  async function salvar(ev: FormEvent) {
    ev.preventDefault()
    setSalvando(true)
    setAviso(null)
    try {
      await api('/auth/trocar-senha', { method: 'POST', body: JSON.stringify({ atual: temSenha ? atual : null, nova }) })
      setAtual('')
      setNova('')
      setConfirma('')
      setAviso({ ok: true, texto: 'Senha trocada. Os outros aparelhos precisam entrar de novo.' })
    } catch (e) {
      setAviso({ ok: false, texto: mensagem(e) })
    } finally {
      setSalvando(false)
    }
  }

  return (
    <section className="cartao pilha">
      <h2>{temSenha ? 'Trocar senha' : 'Criar senha'}</h2>
      {!temSenha && <p className="fraco" style={{ margin: 0 }}>Sua conta entra pelo Google. Uma senha deixa entrar também sem ele.</p>}
      <form className="pilha" onSubmit={salvar}>
        <div className="grade-campos">
          {temSenha && (
            <label className="rotulo">
              Senha atual
              <input className="campo" type="password" autoComplete="current-password" value={atual}
                     onChange={(e) => setAtual(e.target.value)} />
            </label>
          )}
          <label className="rotulo">
            Senha nova
            <input className="campo" type="password" autoComplete="new-password" value={nova} maxLength={128}
                   onChange={(e) => setNova(e.target.value)} />
          </label>
          <label className="rotulo">
            Repita a senha nova
            <input className="campo" type="password" autoComplete="new-password" value={confirma} maxLength={128}
                   onChange={(e) => setConfirma(e.target.value)} />
          </label>
        </div>
        {(problema || aviso) && (
          <div className={!problema && aviso?.ok ? 'ok-caixa' : 'erro-caixa'} role="status">{problema ?? aviso?.texto}</div>
        )}
        <div>
          <button className="botao" disabled={salvando || !!problema || !nova || confirma !== nova || (temSenha && !atual)}>
            {salvando ? 'Salvando...' : 'Salvar senha'}
          </button>
        </div>
      </form>
    </section>
  )
}

function Saida() {
  const qc = useQueryClient()
  const [saindo, setSaindo] = useState(false)
  async function fazer(todos: boolean) {
    setSaindo(true)
    await sair(qc, todos)
  }
  return (
    <section className="cartao pilha">
      <h2>Sair</h2>
      <p className="fraco" style={{ margin: 0 }}>Sair apaga também os dados guardados neste aparelho.</p>
      <div className="linha">
        <button className="botao-sec" disabled={saindo} onClick={() => fazer(false)}>Sair deste aparelho</button>
        <button className="botao-sec" disabled={saindo} onClick={() => fazer(true)}>Sair de todos os aparelhos</button>
      </div>
    </section>
  )
}
