# Roadmap

Cada fase tem um plano em `docs/fases/fase-N.md`, escrito com `/planejar-fase N` e aprovado antes de codar, e é fechada com `/fechar-fase N`.

Status: ⬜ não iniciada · 📝 planejada · 🚧 em andamento · ✅ concluída · ⏸️ aguardando o usuário

| Fase | Objetivo | Status |
|---|---|---|
| 1 | Importar o histórico do Strava e calcular métricas | ✅ |
| 2 | Puxar treinos do celular (Health Connect) com agendador e deduplicação | ✅ (validação com o celular ⏸️) |
| 3 | Servidor MCP e chat com Claude e Gemini | ✅ |
| 4 | Planos de treino salvos pelo chat e aderência planejado x executado | ✅ ([plano](fases/fase-4.md)) |
| 5 | Painel web desktop (React) com gráficos e chat | ✅ ([plano](fases/fase-5.md)) |
| 6 | Painel no celular (responsivo + PWA, via Tailscale) | ✅ ([plano](fases/fase-6.md)) |
| 7 | Pace Lab como app Android lendo o Samsung Health (com GPS) | 🚧 ([plano](fases/fase-7.md)) |
| 8 | Hospedagem e musculação (Hevy) | ⬜ |

## Fase 1: histórico do Strava ✅
Importador do export (pasta ou .zip, idempotente; GPX, TCX, FIT, JSON); parciais por km; limpeza de FC; alerta de FC colada na cadência; zonas por % da FC máxima; TRIMP de Edwards; fitness (42 dias), fadiga (7 dias) e forma; duplicatas; CLI e API com token. Validado com o export real (359 atividades).

## Fase 2: Health Connect ✅
Cliente do servidor local do HC Webhook; conversor do JSON (escrito pela documentação); sincronização desde o último sucesso menos 48 h; tabela `sync_state`; Strava prevalece nas duplicatas; agendador no serviço; notificação do Windows; `iniciar-treino.bat`; Alembic. Teste de ponta a ponta com servidor falso.

## Fase 3: MCP e chat ✅
Registro único de 9 ferramentas; `treino mcp` (stdio e HTTP); provedores Claude (Agent SDK, login do PC) e Gemini; conversas e sensações no banco; `treino chat`, `POST /chat`. Teste real com Claude em 28/10/2026.

## Fase 4: planos e aderência ✅
Planos montados no chat e salvos com confirmação; aderência calculada na hora (mesmo dia ou dia vizinho, metas, extras, resumo semanal); 7 ferramentas novas, `treino plano`, rotas `/planos`. Detalhes em [fases/fase-4.md](fases/fase-4.md).

## Fase 5: painel web desktop ✅
Painel em `web/` servido por `treino servico` em http://127.0.0.1:8000 (API em `/api`): visão geral, treinos com mapa e gráficos, plano com aderência e chat lateral com o contexto da página. Detalhes em [fases/fase-5.md](fases/fase-5.md).

## Fase 6: celular ✅
Painel no celular pelo Tailscale (`tailscale serve`), instalável como app, conectado por QR code, com layout próprio e dados guardados no aparelho para ver com o PC desligado. Detalhes em [fases/fase-6.md](fases/fase-6.md); guia em [celular.md](celular.md).

## Fase 7: app Android e Samsung Health ✅
App Android Pace Lab (Capacitor, painel embutido) que lê os treinos do Samsung Health com GPS, FC, velocidade e cadência (Samsung Health Data SDK em modo desenvolvedor) e envia ao PC pelo Tailscale ao abrir, ao voltar e no botão Sincronizar; atualização do app pelo próprio app (`treino publicar-app`). HC Webhook e agendador removidos. Detalhes em [fases/fase-7.md](fases/fase-7.md); guia em [celular.md](celular.md).

## Fase 8: hospedagem e musculação ⬜
Docker Compose, Postgres, MCP remoto com autenticação, Claude por chave de API. Hospedagem preferida: Oracle Cloud Always Free (ver ADR 0009), com backup automático do banco. Musculação do Hevy (JSON já guardado em `extra`).

## Direção futura: app para outras pessoas
O usuário quer, um dia, um app "redondo" para amigos ou para a Play Store (10/11/2026). Ainda não é fase; exige revisar decisões aceitas:
- **Contas de usuário:** hoje um usuário e um token (ADR 0011); precisaria de contas e dados separados por pessoa.
- **IA:** o chat usa o login da assinatura do Claude, que não pode ser oferecido a terceiros (ADR 0008); seria chave de API ou Gemini.
- **Hospedagem obrigatória** (fase 8) em vez do PC ligado.
- **Fonte de treinos:** parceria com a Samsung (Samsung Health Data SDK sem modo desenvolvedor) ou Health Connect (sem GPS do Samsung Health); a fase 7 já deixa a leitura atrás de uma "fonte de treinos" para isso.
- **Play Store:** política de privacidade, declaração e revisão dos dados de saúde, conta de desenvolvedor (custo a conferir).

## Pendências de validação

- [x] ~~**Celular:** ver um JSON real do HC Webhook (`GET /?days=2` depois de uma corrida) e ajustar `ingest/health_connect.py`: valores de `type`, se `metadata` vem na sessão, resolução da FC, granularidade da distância, se existe rota/GPS.~~ Obsoleto: o HC Webhook foi removido na fase 7.
- [x] ~~**Celular:** token do servidor local do HC Webhook.~~ Obsoleto: HC Webhook removido na fase 7.
- [ ] **Strava:** reavaliar a decisão [0001](decisions/0001-sem-api-do-strava.md) junto com o teste do Health Connect.
- [x] **Gemini:** testado com a chave real em 28/10/2026 (último treino e aderência). Nesse dia o `gemini-3.8-flash` estava sobrecarregado (503/504, até 2 min por resposta); o `gemini-3.6-flash` respondeu em cerca de 3 s e virou reserva automática.
- [ ] **agy:** conferir se o arquivo de MCP é `~/.gemini/config/mcp_config.json` (fontes citam também `~/.gemini/antigravity-cli/mcp_config.json`).
- [ ] **Plano de teste:** "Teste de aderencia" (id 1) ficou ativo no banco real; arquivar ou substituir pelo primeiro plano de verdade.
- [ ] **Musculação (fase 8):** peso do Hevy em kg? Valores de 2 a 180. Decidir como guardar os sets.
- [ ] **Play Protect (app Android):** na atualização pelo próprio app (11/11/2026) o Play Protect mostrou aviso de segurança e bloqueou, com opção de instalar mesmo assim; o usuário instalou e funcionou. Por enquanto não é problema. Verificar no futuro: registrar o app na conta gratuita de distribuição limitada do Google (verificação de desenvolvedor) e ver se o aviso some; obrigatório para o app ir a outras pessoas.
- [x] TCX do Watch 7, leitor de FIT e notificação do Windows validados (27/10/2026).
