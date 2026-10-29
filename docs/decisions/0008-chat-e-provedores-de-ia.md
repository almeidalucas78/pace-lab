# 0008. Ferramentas compartilhadas e provedores de IA intercambiáveis

- Status: aceita
- Data: 2026-10-27 (detalhes de implementação em 2026-10-28)

## Contexto
O chat do painel e os clientes MCP (Claude Desktop/Code, agy) precisam das mesmas capacidades. O usuário assina Claude e Gemini Pro; a assinatura Gemini Pro não dá cota de API.

## Decisão
- Um registro único de ferramentas (`treino/ia/ferramentas.py`) serve o MCP, o Claude e o Gemini. As ferramentas devolvem fichas resumidas, nunca dados brutos.
- Provedores por configuração (`IA_PROVEDOR`):
  - Claude via Claude Agent SDK com o login do Claude Code do PC (consome a assinatura). Ao hospedar, trocar para chave de API.
  - Gemini via chave gratuita do Google AI Studio (os limites aparecem no painel do AI Studio; requisições do plano gratuito podem ser usadas pelo Google para melhorar produtos).
- O Claude do chat não tem acesso a arquivos nem comandos (`tools=[]`, `setting_sources=[]`).
- Planos nascem da conversa; o Python calcula, a IA interpreta.

## Consequências
- A documentação oficial do Agent SDK (conferida em 28/10/2026) só descreve chave de API e diz que, salvo aprovação, desenvolvedores não podem oferecer login do claude.ai ou limites de assinatura em produtos. O uso aqui é do próprio assinante no próprio PC, caso que a documentação não trata explicitamente. Nunca expor o chat com login de assinatura para outras pessoas.
- Cada conversa fica presa ao provedor em que começou.
