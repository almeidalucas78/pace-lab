# 0012. Painel no celular: Tailscale, PWA, QR code e dados guardados

- Status: aceita
- Data: 2026-11-09

## Contexto
A fase 6 leva o painel ao celular, com o PC ligado (ADR 0009). Instalar como app (PWA) exige HTTPS e manifest com ícones de 192 e 512 px (web.dev/articles/install-criteria). O `tailscale serve` dá HTTPS só dentro do tailnet (tailscale.com/kb/1242); ativar HTTPS publica o nome da máquina e do tailnet num registro público de certificados (tailscale.com/kb/1153).

## Decisão
- **Acesso:** Tailscale com `tailscale serve --bg 8000`; o serviço continua escutando só em 127.0.0.1. Nomes neutros na máquina e no tailnet antes de ativar o HTTPS.
- **Token:** o painel do PC mostra um QR code com `PAINEL_URL_CELULAR#token=...`; o fragmento não vai ao servidor; o painel salva o token e limpa a URL.
- **Dados no celular:** o usuário escolheu guardar os dados já vistos (cache do TanStack Query no IndexedDB, validade de 30 dias). Sem o PC, mostra os dados guardados com a hora deles; chat e alterações precisam do PC. Sair apaga o cache.
- **Atualização:** sem push em tempo real. Busca ao abrir, ao voltar para o app e ao puxar a tela; o chat invalida o que grava.
- **Navegação:** no celular, barra inferior (Visão geral, Treinos, Plano, Chat) e chat em tela cheia; no PC, nada muda.
- **App:** nome "Pace Lab", ícone atual (pode mudar depois).

## Consequências
- O celular passa a ter dados de saúde e traçados de GPS guardados, protegidos pelo bloqueio de tela.
- Respostas da API guardadas no celular precisam ser compatíveis entre versões: ao mudar o formato de uma resposta, subir a versão do cache (`buster`) para descartar o antigo.
