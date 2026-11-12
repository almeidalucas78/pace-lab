# Pace Lab

Painel pessoal de corrida. Importa o histórico do Strava, recebe os treinos novos do app Android (Samsung Health, com GPS), calcula métricas, mostra tudo num painel web com gráficos e mapa, e conversa com você sobre os treinos (Claude ou Gemini, no painel, no terminal ou via MCP).

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

### Painel web (uma vez, e de novo quando o front mudar)

Pré-requisito: Node.js 18 ou mais novo ([nodejs.org](https://nodejs.org/)).

```powershell
cd web
npm install
npm run build
```

## Usar no dia a dia

Dois cliques em `iniciar-treino.bat`. Ele sobe o serviço e abre o painel em http://127.0.0.1:8000. Na primeira vez o painel pede o `API_TOKEN` do `.env` (fica salvo no navegador). Feche a janela do serviço para parar.

- **Visão geral:** fitness, fadiga e forma; gráfico de 90 dias; volume semanal; última corrida; semana do plano.
- **Treinos:** lista por esporte e, em cada treino, mapa, gráficos de FC, ritmo e altitude, parciais, zonas e sensações.
- **Plano:** sessões por semana com a situação de cada uma (feita, perdida, no alvo) e histórico de planos.
- **Treinador (chat):** abre ao lado de qualquer página. Se você estiver num treino ou no plano, a IA já sabe do que se trata.

O mapa usa as imagens do OpenStreetMap: o traçado do GPS não sai do PC, mas o navegador baixa as imagens da região exibida.

### No celular

Com o Tailscale (grátis), o painel abre no celular de qualquer lugar, enquanto o PC estiver ligado, e pode ser instalado como app. O passo a passo está em [docs/celular.md](docs/celular.md): instalar o Tailscale no PC e no celular, ativar o HTTPS, rodar `tailscale serve --bg 8000`, preencher `PAINEL_URL_CELULAR` no `.env` e ler o QR code da página **Conectar celular**.

No celular a navegação fica numa barra embaixo (Visão geral, Treinos, Plano, Chat). Os dados já vistos ficam guardados no aparelho por até 30 dias: com o PC desligado, o app mostra o que tinha com o aviso "PC fora do ar". **Sair** apaga tudo do aparelho.

### Mexer no painel (desenvolvimento)

Dois terminais: `.\.venv\Scripts\treino.exe api` e, na pasta `web`, `npm run dev`. Abra http://localhost:5173: o painel recarrega a cada alteração e repassa `/api` para o backend. Testes do front: `npm test`; o `npm run build` também confere os tipos.

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
| `treino servico` | Sobe o painel e a API para o app do celular (é o que o `iniciar-treino.bat` roda) |
| `treino api` | Igual ao `servico` (documentação da API em `/api/docs`) |
| `treino publicar-app` | Publica o APK compilado; o app no celular oferece a atualização |
| `treino reprocessar-app` | Refaz parciais, mapa e zonas dos treinos do app com o conversor atual |
| `treino status-sync` | Última vez que o app enviou treinos e último erro |
| `treino plano` | Plano ativo com a situação de cada sessão (`treino plano 3`, `--listar` para o histórico) |
| `treino chat` | Conversa com o treinador no terminal (`--provedor gemini`, `--conversa 3` para continuar) |
| `treino mcp` | Servidor MCP por stdio (para Claude Desktop, Claude Code e agy); `--http` serve em http://127.0.0.1:8001/mcp |

## Treinos novos pelo app Android (Samsung Health)

O app **Pace Lab** no celular lê os treinos do Samsung Health (com GPS, FC, velocidade e cadência) e os envia ao PC pelo Tailscale: ao abrir o app, ao voltar para ele e no botão **Sincronizar**. O PC precisa estar ligado com o `iniciar-treino.bat` aberto; se não estiver, o app tenta de novo na próxima vez, sem perder nada. Treino novo gera notificação do Windows. Instalação, modo desenvolvedor do Samsung Health e atualização do app: `docs/celular.md`.

- O mesmo treino no Strava e no Samsung Health (mesmo esporte, até 10 min de diferença): **vale o do Strava**; o outro fica marcado como duplicata.
- Esteira e musculação não têm GPS: a distância sai da velocidade do relógio e o treino não tem mapa.

## Chat com o treinador (IA)

O chat usa ferramentas que consultam o banco e devolvem fichas resumidas: último treino, detalhe de um treino, lista, resumo por semana, carga atual, perfil (FC máxima e zonas), sensações, status da sincronização e planos de treino (salvar, consultar, ajustar, aderência). A IA interpreta e propõe; os números vêm sempre do Python.

- Terminal: `treino chat`. Painel: botão "Treinador (chat)". API: `POST /api/chat` com `{"mensagem": "...", "conversa_id": null, "provedor": "claude", "contexto": null}`; conversas em `GET /api/chat/conversas`.
- **Claude** (`IA_PROVEDOR=claude`): usa o Claude Code embutido no pacote `claude-agent-sdk`. Sem `ANTHROPIC_API_KEY` no ambiente, ele usa o login do Claude Code que já existe neste PC e consome os limites da sua assinatura. O modelo fica em `CLAUDE_MODELO`. O Claude do chat não tem acesso a arquivos nem a comandos: só às ferramentas de treino.
- **Gemini** (`IA_PROVEDOR=gemini`): se o modelo principal (`GEMINI_MODELO`) estiver sobrecarregado, a resposta usa `GEMINI_MODELO_RESERVA`. Precisa de `GEMINI_API_KEY` (chave gratuita do [Google AI Studio](https://aistudio.google.com/apikey)). No plano gratuito, o Google pode usar as requisições para melhorar os produtos; os limites aparecem no painel do AI Studio.
- Cada conversa fica com o provedor em que começou. As mensagens ficam no banco (`conversations`, `chat_messages`).
- Quando você conta como se sentiu ("pernas pesadas hoje"), a IA registra em `sensations` e passa a considerar nas próximas respostas.

## Planos de treino

Peça no chat, por exemplo: "Quero correr 10 km em 50 min em dezembro, posso treinar segunda, quarta e sábado". O treinador pergunta o que faltar, mostra o plano dia a dia e **só salva depois que você confirmar**. Cada sessão pode ter metas opcionais (distância, duração, faixa de ritmo, zona de FC, esforço).

- "Como estou indo no plano?": a IA consulta a aderência. Cada sessão aparece como feita, feita em dia vizinho, perdida, futura ou cancelada, comparada com as metas; treinos fora do plano aparecem como extras.
- Ajustes pequenos ("passa o longão para domingo") editam a sessão; mudanças grandes criam um plano novo, e o anterior fica no histórico.
- No terminal: `treino plano`. No painel: página Plano. Na API: `GET /api/planos`, `GET /api/planos/ativo`, `GET /api/planos/{id}`, `GET /api/planos/{id}/aderencia`.
- Treinos que chegam depois (celular ou novo export do Strava) entram na aderência sozinhos.

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
  ingest/          leitura de GPX, TCX, FIT, JSON, do activities.csv e dos treinos enviados pelo app Android
  core/            cálculos puros: parciais, limpeza de FC, zonas, carga
  services.py      regras e consultas usadas pela CLI, pela API, pelo MCP e pelo chat
  ia/              ferramentas da IA (registro único), servidor MCP, provedores Claude e Gemini, chat
  notify.py        notificações do Windows (só log em servidor)
  api/             FastAPI com token (rotas em /api) e o painel compilado na raiz
  cli.py           comandos `treino ...`
tests/             testes com dados sintéticos (`pytest`)
web/               painel React + TypeScript + Vite (só fala com a API)
  src/api/         cliente com o token, tipos das respostas, consultas
  src/paginas/     Visão geral, Treinos, Treino, Plano
  src/componentes/ gráficos, mapa, semanas do plano, chat lateral
```

## Documentação do projeto

- [AGENTS.md](AGENTS.md): regras do projeto para pessoas e para qualquer IA (Claude, Gemini)
- [CONTRIBUTING.md](CONTRIBUTING.md): montar o ambiente e rodar as checagens
- [docs/processo.md](docs/processo.md): fluxo de trabalho (fases, issues, pull requests)
- [docs/ROADMAP.md](docs/ROADMAP.md): fases, status e pendências
- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md): camadas, fluxos de dados, tabelas e como escalar
- [docs/decisions/](docs/decisions/README.md): decisões e por que foram tomadas
- [CHANGELOG.md](CHANGELOG.md): o que mudou em cada versão
- [SECURITY.md](SECURITY.md): como relatar um problema de segurança

O código está visível, mas sem licença aberta: todos os direitos reservados.
