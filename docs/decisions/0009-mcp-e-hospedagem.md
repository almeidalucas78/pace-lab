# 0009. MCP local agora, remoto ao hospedar; Tailscale antes disso

- Status: aceita
- Data: 2026-10-27

## Contexto
O Claude no celular só acessa MCP remoto público. Sem custo de hospedagem por enquanto.

## Decisão
- Agora: MCP local por stdio (`treino mcp`) no Claude Desktop/Code e no Antigravity CLI (`agy`, que substituiu o Gemini CLI).
- Acesso pelo celular antes de hospedar: Tailscale (plano pessoal gratuito), com o PC ligado.
- Hospedagem futura: Docker Compose, Postgres, HC Webhook enviando webhook para a API, MCP via HTTP como conector customizado no claude.ai.

## Consequências
- `treino mcp --http` existe mas não tem autenticação: só em 127.0.0.1 até a fase de hospedagem.
