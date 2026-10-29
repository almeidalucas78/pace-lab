# Decisões (ADRs)

Um arquivo por decisão importante, no formato curto abaixo. Decisões não são apagadas: quando mudam, o arquivo antigo recebe `Status: substituída por NNNN` e a nova decisão ganha arquivo próprio.

Regra do projeto: decisão com status **aceita** não é reaberta sem perguntar ao usuário.

| Nº | Decisão | Status |
|---|---|---|
| [0001](0001-sem-api-do-strava.md) | Strava só pelo export completo, nunca pela API | aceita (reavaliação pedida) |
| [0002](0002-health-connect-por-pull.md) | Treinos novos do Health Connect, com o PC puxando do celular | aceita |
| [0003](0003-deduplicacao-strava-prevalece.md) | Deduplicação por horário e esporte; Strava prevalece | aceita |
| [0004](0004-stack.md) | Python + FastAPI + SQLAlchemy; React + TypeScript + Vite | aceita |
| [0005](0005-arquitetura-em-camadas.md) | Camadas core, ingest, services e interfaces | aceita |
| [0006](0006-agendador-no-servico.md) | Agendador dentro do serviço, iniciado à mão | aceita |
| [0007](0007-migracoes-alembic.md) | Migrações com Alembic | aceita |
| [0008](0008-chat-e-provedores-de-ia.md) | Ferramentas compartilhadas e provedores de IA intercambiáveis | aceita |
| [0009](0009-mcp-e-hospedagem.md) | MCP local agora, remoto ao hospedar; Tailscale antes disso | aceita |

## Modelo

```markdown
# NNNN. Título curto

- Status: proposta | aceita | substituída por NNNN | abandonada
- Data: AAAA-MM-DD

## Contexto
O problema e as restrições, com o que foi verificado (e onde).

## Decisão
O que foi decidido, em frases diretas.

## Consequências
O que fica mais fácil, o que fica mais difícil, o que precisa ser revisto e quando.
```
