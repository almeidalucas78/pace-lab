# Treino

Painel pessoal de corrida. Importa o histórico do Strava, puxa os treinos novos do celular (Health Connect), calcula métricas, expõe uma API e conversa com você sobre os treinos (Claude ou Gemini, no chat ou via MCP).

## Instalar no Windows

Pré-requisito: Python 3.11 ou mais novo ([python.org](https://www.python.org/downloads/), marque "Add python.exe to PATH").

No PowerShell, dentro da pasta do projeto:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
copy .env.example .env
```

Se o PowerShell bloquear o `Activate.ps1`, rode uma vez:
`Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`.

Depois edite o `.env`: troque o `API_TOKEN` e, se souber, preencha `FC_MAX` e `FC_REPOUSO`.

## Importar o histórico do Strava

Pode apontar para o `.zip` do export direto, sem descompactar:

```powershell
treino importar-strava "C:\Users\voce\Downloads\export_12345.zip"
```

Pode rodar de novo quando quiser: atualiza o que já existe, sem duplicar.

## Comandos

| Comando | O que faz |
|---|---|
| `treino resumo` | Visão geral, volume semanal de corrida e fitness/fadiga/forma de hoje |
| `treino atividades --limite 20` | Últimos treinos (`--esporte todos` para incluir musculação etc.) |
| `treino atividade 356` | Detalhe de um treino: parciais por km, zonas de FC, qualidade dos dados |
| `treino fc` | FC máxima usada nos cálculos e se é configurada ou estimada |
| `treino recalcular` | Refaz zonas, carga e duplicatas (rode após mudar o `.env`) |
| `treino servico` | Sobe a API com a sincronização automática do celular (é o que o `iniciar-treino.bat` roda) |
| `treino api` | Sobe a API em http://127.0.0.1:8000 sem sincronização (documentação em `/docs`) |
| `treino sincronizar` | Puxa agora os treinos do celular |
| `treino status-sync` | Última sincronização com o celular e último erro |
| `treino chat` | Conversa com o treinador no terminal (`--provedor gemini`, `--conversa 3` para continuar) |
| `treino mcp` | Servidor MCP por stdio (para Claude Desktop, Claude Code e agy); `--http` serve em http://127.0.0.1:8001/mcp |

## Treinos novos pelo celular (Health Connect)

Os treinos novos chegam pelo app **HC Webhook** (Play Store), com o **servidor HTTP local** ligado. O PC puxa os dados pela Wi-Fi; o celular não precisa enviar nada.

1. No app: ative o servidor local (porta padrão 8787), ative o token e libere no Health Connect os tipos **exercício, frequência cardíaca, distância e calorias**.
2. No `.env`: preencha `HC_URL` com o endereço do celular na Wi-Fi (ex.: `http://192.168.0.20:8787`) e `HC_TOKEN` com o token do app.
3. Abra o `iniciar-treino.bat` (dois cliques). Ele sobe o serviço, sincroniza na hora e repete a cada `SYNC_INTERVALO_MIN` enquanto a janela estiver aberta. Treino novo gera notificação do Windows.

Detalhes:
- Cada leitura pede tudo desde a última leitura bem-sucedida, voltando 48 h a mais (o relógio às vezes passa os dados para o Health Connect com atraso). Se o celular estiver fora da rede, a janela não avança e a próxima rodada recupera.
- O mesmo treino no Strava e no Health Connect (mesmo esporte, até 10 min de diferença): **vale o do Strava**; o do Health Connect fica marcado como duplicata.
- Segundo a documentação do app, a sessão de exercício não traz GPS, velocidade nem potência. Parciais por km só saem se os registros de distância vierem em intervalos curtos (até 2 min); senão o treino fica só com totais, zonas e carga.

## Chat com o treinador (IA)

O chat usa ferramentas que consultam o banco e devolvem fichas resumidas: último treino, detalhe de um treino, lista, resumo por semana, carga atual, perfil (FC máxima e zonas), sensações e status da sincronização. A IA interpreta e propõe; os números vêm sempre do Python.

- Terminal: `treino chat`. API: `POST /chat` com `{"mensagem": "...", "conversa_id": null, "provedor": "claude"}`; conversas em `GET /chat/conversas`.
- **Claude** (`IA_PROVEDOR=claude`): usa o Claude Code embutido no pacote `claude-agent-sdk`. Sem `ANTHROPIC_API_KEY` no ambiente, ele usa o login do Claude Code que já existe neste PC e consome os limites da sua assinatura. O modelo fica em `CLAUDE_MODELO`. O Claude do chat não tem acesso a arquivos nem a comandos: só às ferramentas de treino.
- **Gemini** (`IA_PROVEDOR=gemini`): precisa de `GEMINI_API_KEY` (chave gratuita do [Google AI Studio](https://aistudio.google.com/apikey)). No plano gratuito, o Google pode usar as requisições para melhorar os produtos; os limites aparecem no painel do AI Studio.
- Cada conversa fica com o provedor em que começou. As mensagens ficam no banco (`conversations`, `chat_messages`).
- Quando você conta como se sentiu ("pernas pesadas hoje"), a IA registra em `sensations` e passa a considerar nas próximas respostas.

## Ferramentas via MCP (Claude Desktop, Claude Code, agy)

As mesmas ferramentas do chat, para usar fora do painel. Troque o caminho pelo da sua pasta.

**Claude Code:**

```powershell
claude mcp add treino -- "D:\estudos\Programação	reino-app	reino-app\.venv\Scripts	reino.exe" mcp
```

**Claude Desktop** (`claude_desktop_config.json`) e **Antigravity CLI** (`~/.gemini/config/mcp_config.json`; confira no seu agy se o caminho é esse) usam o mesmo formato:

```json
{
  "mcpServers": {
    "treino": {
      "command": "D:\estudos\Programação\treino-app\treino-app\.venv\Scripts\treino.exe",
      "args": ["mcp"]
    }
  }
}
```

O `.env` e o banco são encontrados pela pasta do projeto, então não importa de onde o cliente abre o processo.

## Como os dados são tratados

- **Totais vêm do Strava.** Distância, tempo em movimento e FC média são os do resumo oficial. Os arquivos de cada treino complementam com parciais, zonas e gráficos.
- **Horários:** o export vem em UTC; o sistema guarda em UTC e mostra no fuso do `.env`.
- **Cadência:** o Strava exporta a de corrida por perna; aqui ela aparece em passos por minuto totais.
- **FC:** leituras fora de 30 a 230 bpm e picos isolados são descartados (o valor original fica guardado). Quando a FC parece "colada" na cadência, o treino é marcado como `suspeita_cadencia`, sem apagar nada.
- **FC máxima:** se `FC_MAX` estiver vazio, o sistema estima pelo maior valor sustentado por 30 s nos seus treinos. É só uma estimativa: zonas e carga dependem dela.
- **Carga (TRIMP de Edwards):** minutos em cada zona x peso da zona (1 a 5). Treinos sem arquivo usam a FC média. Fitness = média exponencial de 42 dias, fadiga = 7 dias, forma = fitness menos fadiga. Só corrida, caminhada e pedalada entram na carga diária.
- **Duplicatas:** dois treinos do mesmo esporte com menos de 10 min de diferença são marcados; o que fica fora dos totais é o de fonte menos confiável (Health Connect perde para o Strava) ou, na mesma fonte, o segundo.
- **Banco:** o esquema é versionado com Alembic. Os comandos atualizam o banco sozinhos ao iniciar; um banco da fase 1 é reconhecido e migrado sem perder dados.

## Estrutura

```
treino/
  config.py        configurações (.env)
  db/              modelos e conexão (SQLite hoje, Postgres trocando DATABASE_URL)
  migrations/      migrações do Alembic (gerar nova: `alembic revision --autogenerate -m "..."`)
  ingest/          leitura de GPX, TCX, FIT, JSON, do activities.csv e do HC Webhook
  core/            cálculos puros: parciais, limpeza de FC, zonas, carga
  services.py      regras e consultas usadas pela CLI, pela API, pelo agendador, pelo MCP e pelo chat
  ia/              ferramentas da IA (registro único), servidor MCP, provedores Claude e Gemini, chat
  scheduler.py     sincronização periódica dentro do serviço
  notify.py        notificações do Windows (só log em servidor)
  api/             FastAPI com token
  cli.py           comandos `treino ...`
tests/             testes com dados sintéticos (`pytest`)
```

## Documentação do projeto

- [docs/ROADMAP.md](docs/ROADMAP.md): fases, status e pendências
- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md): camadas, fluxos de dados, tabelas e como escalar
- [docs/decisions/](docs/decisions/README.md): decisões e por que foram tomadas
- [CHANGELOG.md](CHANGELOG.md): o que mudou em cada versão

## Próximas fases

4. Planos de treino e aderência
5. Painel web
