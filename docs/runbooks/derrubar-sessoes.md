# Runbook: tirar o acesso de todos os aparelhos

Quando um aparelho conectado foi perdido ou roubado, ou há suspeita de acesso indevido.

## Hoje (token único, ADR 0011)
1. Trocar o `API_TOKEN` no `.env` (passo 1 de [segredo-vazado.md](segredo-vazado.md)) e reiniciar o serviço: todo aparelho conectado perde o acesso na hora.
2. No painel do Tailscale (login.tailscale.com, Machines), remover o aparelho perdido da rede.
3. Reconectar os aparelhos que ficam, pelo QR code da página Conectar celular.

## A partir da fase 9 (contas e sessões, ADR 0015)
A tela de conta terá "sair de todos os aparelhos", que apaga as sessões no servidor. Este runbook ganha o comando equivalente no servidor, para quando a pessoa não consegue entrar.
