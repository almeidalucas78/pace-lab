# Fase 9: Pace Lab na nuvem com contas (Oracle, Postgres e login com Google)

- Status: planejada
- Planejada em: 2026-11-11 · Concluída em: -

## Objetivo
O Pace Lab passa a morar num servidor da Oracle, ligado 24 h, sem custo. O usuário entra com a conta Google (ou e-mail e senha) no painel web e no app Android; o celular envia os treinos direto para o servidor, com o PC desligado; todos os dados atuais aparecem na conta dele. O sistema já nasce com cada pessoa vendo só os próprios dados, pronto para outras pessoas no futuro. O `.bat` deixa de ser necessário.

## Fora do escopo
- Pace Lab Desktop (Electron), tela de provedores de IA, IA local e Claude pela assinatura: **fase 10**.
- Musculação do Hevy: **fase 11** (decisões já tomadas: CSV do Hevy compartilhado pelo app; séries juntadas ao treino do relógio).
- Conector MCP com OAuth, LGPD (termo, exportar e apagar conta), cadastro aberto: **fase 12**.
- Fundação de engenharia (CI, processo, GitHub, qualidade): **fase 8**, feita antes desta.
- Leitura do Samsung Health com o app fechado.

## Decisões tomadas (ADR 0014, 11/11/2026)
Oracle Always Free; Postgres com os dados migrados; contas com login por Google e por e-mail e senha; dados separados por usuário; app Android com login; desktop em Electron na fase 10; custo zero.

## Verificado antes de propor (11/11/2026)
- **Login com Google:** em app web, fluxo de código no servidor; em desktop, navegador do sistema + `127.0.0.1` + PKCE; tela do Google dentro de janela de app é recusada (developers.google.com/identity/protocols/oauth2/native-app). Só com `openid`, `email` e `profile`, o projeto em modo de teste aceita qualquer conta com aviso de "em teste"; páginas do Google divergem sobre isso, então será testado no projeto real (OAuth app state overview; support.google.com/cloud/answer/15549945).
- **Oracle Always Free:** A1 com 2 OCPUs e 12 GB, 200 GB de disco, 10 TB/mês de saída; máquina ociosa por 7 dias pode ser recolhida (docs.oracle.com, Always Free Resources). Cadastro, região e backup no armazenamento de objetos da Oracle: a conferir na etapa 1.
- **Samsung Health:** leitura só no aparelho; API de nuvem só para parceiros (developer.samsung.com). O app Android continua lendo e enviando.
- **Bibliotecas** de login (Google e senha) e de tokens: versões e assinaturas conferidas no PyPI e na documentação na etapa em que entrarem.
- Pesquisas anteriores desta fase (Hevy, IA local, conector, hospedagens): guardadas para as fases 10 a 12 no ROADMAP.

## Decisões (todas respondidas em 11/11/2026)
1. **Endereço público do servidor** (**aceita em 11/11/2026: Funnel agora, domínio na fase 12; ADR 0015**) (o login do Google e o celular fora de casa precisam de HTTPS na internet):
   - (a) **Tailscale Funnel** no servidor: endereço `https://<máquina>.<tailnet>.ts.net`, grátis, sem domínio; limite de banda não informado.
   - (b) **IP público da Oracle + Caddy** com certificado gratuito: exige um domínio (pago, uns R$ 40/ano em `.com.br`) ou um subdomínio grátis.
   - Recomendação: (a) agora, por ser grátis e simples; trocar por domínio quando for para outras pessoas. O Google aceitar o endereço `ts.net` como retorno do login será testado na etapa 2.
2. **Como o painel web guarda o login:** **aceita em 11/11/2026 (ADR 0015).** cookie seguro (`HttpOnly`, `Secure`, `SameSite`) no navegador, que JavaScript nenhum consegue ler; no app Android, token no armazenamento seguro do Android. Hoje o token fica no `localStorage`, que é mais exposto.
3. **Login com Google no app Android:** **aceita em 11/11/2026 (ADR 0015).** o app abre o login do próprio Pace Lab no navegador do celular (Custom Tabs) e volta pelo link `pacelab://`, com um código de uso único. Assim existe uma tela de login só (a do servidor), usada pelo web, pelo Android e depois pelo desktop, e um cadastro de app só no Google.
4. **Testes com Postgres:** **aceita em 11/11/2026: SQLite no dia a dia e Postgres no Docker local antes de fechar etapas e commits (ADR 0015).** Os testes continuam rápidos com SQLite no PC e ganham uma rodada contra Postgres (no servidor ou num Postgres local). Recomendação: as duas.

## Mudanças no banco
- **Troca de SQLite por Postgres** (previsto no ADR 0004), migrações do Alembic ajustadas para rodar nos dois.
- **Tabelas novas:** `users` (id, e-mail, nome, `google_sub`, hash da senha, FC máxima e preferências que hoje estão no `.env`, criado em) e `auth_sessions` (tokens de renovação guardados só como hash, aparelho, validade, revogado).
- **Dono em todo dado:** `user_id` em `activities`, `sensations`, `conversations`, `training_plans`, `sync_state` e `daily_load` (as outras tabelas herdam pelo treino, conversa ou plano). Chaves únicas passam a incluir o usuário (ex.: `(user_id, source, source_id)`; `daily_load` por `(user_id, day)`).
- **Risco:** é a mudança mais cara de desfazer até agora. Mitigação: o SQLite atual fica intacto como backup (e mais uma cópia em `D:\dados\strava\`); a migração é um script que conta linhas por tabela antes e depois e compara totais (km, carga, treinos por ano); só depois de conferido o app passa a enviar para o servidor.

## Etapas
1. [ ] **Servidor**: conta Oracle (o usuário cria; eu guio), máquina A1 Ubuntu, só acesso por chave SSH, firewall, atualizações automáticas de segurança, Docker Compose (API + Postgres; Postgres sem porta aberta para fora), Tailscale e endereço público (decisão 1). Guia em `docs/servidor.md`.
2. [ ] **Contas e login**: modelos `users` e `auth_sessions`, cadastro e login por e-mail e senha (hash Argon2, limite de tentativas), login com Google (projeto no Google Cloud, escopos básicos), tokens de acesso curtos e de renovação com rotação, sair e sair de todos os aparelhos; testes.
3. [ ] **Dados por usuário**: `user_id` nos modelos e migração; `services.py`, rotas e ferramentas da IA recebem o usuário; FC máxima e preferências por usuário; testes que provam que o usuário A não lê nem altera nada do B (treinos, planos, conversas, carga).
4. [ ] **Postgres**: Alembic rodando em Postgres, testes também contra Postgres (Docker local e um job com Postgres no CI da fase 8), ajustes de tipos (datas com fuso, JSON).
5. [ ] **Migração dos dados**: script SQLite → Postgres na conta do usuário, com conferência de contagens e totais; backup antes; relatório.
6. [ ] **Backup**: `pg_dump` diário guardado fora da máquina (armazenamento da Oracle e/ou cópia para o PC), retenção de 7 diários e 4 semanais, **restauração testada**.
7. [ ] **Painel web**: telas de entrar, criar conta e "Entrar com Google"; menu da conta e sair; fim do pedido de `API_TOKEN`; cookie seguro; importação do export do Strava pelo painel (envio do `.zip`), no lugar do comando no PC.
8. [ ] **App Android**: login (navegador do celular + `pacelab://`), token no armazenamento seguro, envio dos treinos para o servidor, atualização do app vinda do servidor (`publicar-app` envia o APK para lá); a versão nova é instalada pela última vez com o fluxo antigo.
9. [ ] **Chat no servidor**: provedor Gemini com a chave do servidor, só para o dono por enquanto; Claude pela assinatura volta na fase 10 (desktop).
10. [ ] **Entrega automática (CD)**: imagem Docker montada no GitHub Actions e guardada no GHCR; deploy ao criar uma versão (entra pelo Tailscale, faz backup, atualiza, roda migrações, confere `/health`, volta à versão anterior se falhar); segredos nos Secrets do GitHub; runbooks de deploy e de rollback.
11. [ ] **Docs e limpeza**: ARCHITECTURE (novo diagrama), README, `docs/celular.md`, `docs/servidor.md`, CHANGELOG; `iniciar-treino.bat` e `treino servico` ficam só para desenvolvimento; ADRs 0009, 0011, 0012 e 0013 atualizados.

## Critério de pronto
- [ ] `pytest` (SQLite e Postgres), `npm run build` e `npm test` passando; testes novos: cadastro, login por senha, login com Google (com o Google simulado), renovação e revogação de token, isolamento entre dois usuários em todas as rotas e ferramentas, migração com um banco sintético.
- [ ] Teste manual: com o **PC desligado**, fazer um treino curto, abrir o Pace Lab no celular (logado com a conta Google) e ver o treino no painel web pelo celular; no PC, entrar com a conta Google pelo navegador e ver o histórico completo, com os mesmos totais de antes da migração.
- [ ] Teste manual de segurança: uma segunda conta de teste não vê nada da primeira; sem login, a API recusa tudo; a restauração do backup funciona num banco vazio.
- [ ] Docs atualizadas.

## Resultado (preenchido no fechamento)
