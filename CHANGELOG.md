# Changelog

O que mudou em cada fase, escrito para o usuário. Formato inspirado no [Keep a Changelog](https://keepachangelog.com/pt-BR/1.1.0/). Detalhes técnicos ficam no git log.

## [Não lançado]

### Corrigido
- Gemini: a chamada agora tem tempo limite (antes podia ficar presa vários minutos) e, quando o modelo principal está sobrecarregado (erro 503/504 do Google), a resposta usa o modelo de reserva (`GEMINI_MODELO_RESERVA`). A troca só acontece se nenhuma ferramenta já rodou, para não gravar nada duas vezes.

## [0.4.0] - 2026-10-28 (fase 4)

### Adicionado
- Planos de treino montados no chat: o treinador mostra, você confirma e ele salva. Ajustes pontuais e planos novos que substituem o anterior.
- Aderência ao plano: sessão feita, feita em dia vizinho, perdida, futura ou cancelada, comparada com distância, duração, ritmo e zona de FC; treinos extras; resumo por semana.
- Comando `treino plano` e rotas `/planos` na API.
- 7 ferramentas novas para a IA (também no MCP): `salvar_plano`, `plano_atual`, `aderencia_plano`, `alterar_sessao`, `adicionar_sessao`, `arquivar_plano`, `listar_planos`.
- Documentação do projeto: `docs/ARCHITECTURE.md`, `docs/ROADMAP.md`, `docs/dados.md` e decisões em `docs/decisions/`.
- Skills `/planejar-fase` e `/fechar-fase` para o ritual de cada fase.
- Regras do Claude Code por pasta em `.claude/rules/`.

## [0.3.0] - 2026-10-28 (fase 3)

### Adicionado
- Chat com o treinador: `treino chat` e `POST /chat`, com Claude (login do Claude Code do PC) ou Gemini (chave do AI Studio).
- Servidor MCP (`treino mcp`) com as mesmas 9 ferramentas do chat, para Claude Desktop, Claude Code e agy.
- Registro de sensações pelo chat (cansaço, dor, esforço percebido).
- Conversas salvas no banco e retomadas pelo id.

### Alterado
- `.env` e banco são encontrados pela pasta do projeto, de qualquer lugar.

## [0.2.0] - 2026-10-27 (fase 2)

### Adicionado
- Sincronização com o celular pelo HC Webhook: `treino servico`, `treino sincronizar`, `treino status-sync`, `iniciar-treino.bat`.
- Notificação do Windows quando chega treino novo.
- Migrações de banco com Alembic (o banco existente foi migrado sem perder dados).

### Alterado
- Duplicatas passam a considerar a fonte: o Strava prevalece sobre o Health Connect.

## [0.1.0] - 2026-10-27 (fase 1)

### Adicionado
- Importação do export do Strava (pasta ou .zip), com GPX, TCX e FIT.
- Parciais por km, zonas de FC, carga TRIMP, fitness, fadiga e forma.
- CLI `treino` e API com token.
