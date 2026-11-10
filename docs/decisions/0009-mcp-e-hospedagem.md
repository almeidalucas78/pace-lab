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
- Reconfirmado em 09/11/2026, depois de comparar com abrir porta no roteador, túnel público (Cloudflare Tunnel, ngrok), hospedagem paga e créditos temporários (DigitalOcean: US$ 200 por 60 dias; não há servidor grátis permanente lá). Tailscale ganhou por ser grátis, não deixar o painel público e dar HTTPS para instalar o app no celular.
- Para a fase 7, o usuário prefere a Oracle Cloud Always Free. Pesquisado em 09/11/2026: o limite grátis do Ampere A1 caiu para 2 núcleos e 12 GB em 2026, sem anúncio público, e a Oracle recolhe máquinas ociosas por 7 dias (CPU, rede e memória abaixo de 20%). Exige backup automático do banco e reavaliar na hora de hospedar.
- `treino mcp --http` existe mas não tem autenticação: só em 127.0.0.1 até a fase de hospedagem.
