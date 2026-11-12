# 0015. Endereço público pelo Tailscale Funnel, sessões com cookie seguro e testes em SQLite e Postgres

- Status: aceita
- Data: 2026-11-11

## Contexto
Com o servidor na Oracle e contas de usuário (0014), o celular, o login com Google e os programas precisam de HTTPS na internet; o login precisa ser guardado com segurança; e os testes precisam pegar diferenças entre o SQLite do dia a dia e o Postgres do servidor. Verificado em 11/11/2026:
- Tailscale Funnel (tailscale.com/kb/1223/funnel): publica uma porta (443, 8443 ou 10000) em `https://<máquina>.<tailnet>.ts.net`; o tráfego passa pelos servidores do Tailscale, mas a criptografia termina no nosso servidor (o Tailscale não lê); certificado gerado sozinho; exige MagicDNS e HTTPS ligados; limite de banda não informado; "disponível em todos os planos".
- Google para apps desktop e móveis: login no navegador do sistema; tela do Google dentro de janela de app é recusada (developers.google.com/identity/protocols/oauth2/native-app).
- O PC do usuário tem Docker 29.6. O repositório no GitHub é privado; o GitHub Free dá US$ 12/mês de computação para Actions em repositório privado, sem cartão até esse limite (docs.github.com, GitHub Actions billing).

## Decisão
- **Endereço público:** Tailscale Funnel no servidor agora. Domínio próprio com IP público e Caddy quando o app for para outras pessoas (fase 12); a troca é só configuração.
- **Sessão no navegador:** cookie `HttpOnly`, `Secure` e `SameSite`, com token de acesso curto (cerca de 15 min) e de renovação longo (cerca de 30 dias) trocado a cada uso, guardado no servidor só como hash, com detecção de reuso; "sair" e "sair de todos os aparelhos". Nada de token no `localStorage`.
- **App Android e desktop:** login pela tela do próprio Pace Lab aberta no navegador do sistema, voltando ao app com um código de uso único (`pacelab://` no Android; endereço `127.0.0.1` no desktop); tokens no cofre do sistema (Keystore no Android, cofre do Windows no Electron). Um único cadastro de app no Google.
- **Testes:** a mesma bateria roda em SQLite (rápida, no dia a dia) e em Postgres num contêiner Docker local (antes de fechar etapas e de cada commit).

## Consequências
- Dependemos do Tailscale para o endereço público até a fase 12; se ele mudar a regra do Funnel, troca-se para domínio próprio.
- O painel web muda o jeito de autenticar (cookie em vez de cabeçalho); o app e o desktop continuam com cabeçalho `Authorization`. A API aceita os dois.
- Testes em Postgres exigem o Docker aberto; também rodam no GitHub Actions, num job com Postgres (fase 8, fundação de engenharia).
