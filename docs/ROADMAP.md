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
| 7 | Pace Lab como app Android lendo o Samsung Health (com GPS) | ✅ ([plano](fases/fase-7.md)) |
| 8 | Fundação de engenharia: CI, processo no GitHub, qualidade, segurança e documentação para qualquer IA | ✅ ([plano](fases/fase-8.md)) |
| 9 | Nuvem com contas: Oracle, Postgres, login com Google, app Android enviando ao servidor, deploy automático | 📝 ([plano](fases/fase-9.md)) |
| 10 | Pace Lab Desktop (Electron) com IA: provedores, IA local, Claude pela assinatura | ⬜ |
| 11 | Musculação (Hevy) | ⬜ |
| 12 | Abrir para outras pessoas: conector MCP com OAuth, LGPD, cadastro | ⬜ |

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

## Fase 8: fundação de engenharia ✅
Repositório limpo e público; pastas `server/`, `web/`, `android/`, `scripts/`; `AGENTS.md` para qualquer IA (Claude, Gemini); ruff, mypy, oxlint, checagens do projeto e pre-commit (ADR 0016); CI no GitHub Actions; Dependabot e segurança do GitHub ligadas; issues, milestones e `main` protegida (tudo por pull request). Pendências viraram issues no GitHub. Detalhes em [fases/fase-8.md](fases/fase-8.md).

## Fase 9: nuvem com contas 📝
Servidor na Oracle Always Free (API, Postgres, painel web), contas com login por Google e por e-mail e senha, dados separados por usuário, os dados atuais migrados, app Android com login enviando direto ao servidor, backup diário. Decisões no [ADR 0014](decisions/0014-nuvem-com-contas-e-desktop.md); plano em [fases/fase-9.md](fases/fase-9.md). Inclui o deploy automático (CD).

## Fase 10: Pace Lab Desktop com IA ⬜
Programa para Windows em Electron (mesmo painel React, login) onde fica a IA para analisar e planejar:
- Tela de provedores no estilo do 9router: Gemini (chave grátis), "compatível com OpenAI" (endereço + chave + modelo), local (Ollama/LM Studio, detectado no PC), com teste de conexão, lista de modelos e ordem de reserva; chaves criptografadas.
- Claude pela assinatura (Agent SDK em TypeScript com o login do Claude Code do PC) só na versão do próprio usuário: a documentação proíbe oferecer o login do claude.ai a outras pessoas.
- Botão **"Conectar ao Claude"** (aceito em 11/11/2026): gera uma extensão do Claude Desktop (`.mcpb`, servidor MCP local com o login da pessoa) e abre a instalação; a pessoa conversa no Claude Desktop, na assinatura dela, com as ferramentas do Pace Lab. Permitido, porque é o app oficial usando uma extensão. Não funciona no celular (lá, conector remoto com OAuth, fase 12); extensões fora do diretório não se atualizam sozinhas.
- Conjunto fixo de perguntas de teste para comparar modelos (gpt-oss-20b, Gemma 4 26B-A4B, Qwen3.5-9B contra o Gemini). A placa do PC é uma RX 9060 XT de 16 GB; no Windows o Ollama usa Vulkan ou ROCm 7.1 (a testar).
- Sem treinar modelo próprio; num servidor sem placa de vídeo modelo local não roda com qualidade.
- Instalador com ícone; programas sem assinatura digital mostram aviso do Windows (a conferir).

## Fase 11: musculação ⬜
Decidido em 11/11/2026: continuar no Hevy e usar o export CSV dele (grátis), compartilhado com o app Android, que envia ao servidor; séries do Hevy juntadas à musculação do relógio no mesmo horário. Já guardados: 59 treinos do Hevy (25/05 a 26/10/2026, 1.005 séries) em `extra["detalhe_bruto"]`. Pendente: confirmar colunas e unidade do peso (provável kg) num CSV real. Tabela de séries, nomes em português e grupo muscular, volume, 1RM estimado e evolução; páginas e ferramentas da IA. Automático só com o Hevy Pro (API).

## Fase 12: abrir para outras pessoas ⬜
Conector MCP com OAuth (o app do Claude da pessoa usando o Pace Lab, permitido até no plano grátis do Claude com 1 conector), LGPD (consentimento, política de privacidade, exportar e apagar conta), cadastro e convites, domínio próprio, Play Protect e verificação de desenvolvedor do Google.

## Direção futura: app para outras pessoas
O usuário quer, um dia, um app "redondo" para amigos ou para a Play Store (10/11/2026). Ainda não é fase; exige revisar decisões aceitas:
- **Contas de usuário:** hoje um usuário e um token (ADR 0011); precisaria de contas e dados separados por pessoa.
- **IA:** o chat usa o login da assinatura do Claude, que não pode ser oferecido a terceiros (ADR 0008); seria chave de API ou Gemini.
- **Hospedagem obrigatória** (fase 9) em vez do PC ligado.
- **Fonte de treinos:** parceria com a Samsung (Samsung Health Data SDK sem modo desenvolvedor) ou Health Connect (sem GPS do Samsung Health); a fase 7 já deixa a leitura atrás de uma "fonte de treinos" para isso.
- **Registro de musculação próprio:** uma aba "Academia" no Pace Lab no lugar do Hevy (biblioteca de exercícios, descanso, cargas anteriores, offline). Ideia de 11/11/2026; hoje o Hevy com export CSV basta.
- **Play Store:** política de privacidade, declaração e revisão dos dados de saúde, conta de desenvolvedor (custo a conferir).

## Pendências de validação

Desde a fase 8, pendências novas viram issues no GitHub (label `tipo: validação`); a lista abaixo fica como histórico.

- [x] ~~**Celular:** ver um JSON real do HC Webhook (`GET /?days=2` depois de uma corrida) e ajustar `ingest/health_connect.py`: valores de `type`, se `metadata` vem na sessão, resolução da FC, granularidade da distância, se existe rota/GPS.~~ Obsoleto: o HC Webhook foi removido na fase 7.
- [x] ~~**Celular:** token do servidor local do HC Webhook.~~ Obsoleto: HC Webhook removido na fase 7.
- [ ] **Strava:** reavaliar a decisão [0001](decisions/0001-sem-api-do-strava.md) junto com o teste do Health Connect.
- [x] **Gemini:** testado com a chave real em 28/10/2026 (último treino e aderência). Nesse dia o `gemini-3.8-flash` estava sobrecarregado (503/504, até 2 min por resposta); o `gemini-3.6-flash` respondeu em cerca de 3 s e virou reserva automática.
- [ ] **agy:** conferir se o arquivo de MCP é `~/.gemini/config/mcp_config.json` (fontes citam também `~/.gemini/antigravity-cli/mcp_config.json`).
- [ ] **Plano de teste:** "Teste de aderencia" (id 1) ficou ativo no banco real; arquivar ou substituir pelo primeiro plano de verdade.
- [ ] **Musculação (fase 11):** peso do Hevy em kg? Valores de 2 a 180. Decidir como guardar os sets.
- [ ] **Play Protect (app Android):** na atualização pelo próprio app (11/11/2026) o Play Protect mostrou aviso de segurança e bloqueou, com opção de instalar mesmo assim; o usuário instalou e funcionou. Por enquanto não é problema. Verificar no futuro: registrar o app na conta gratuita de distribuição limitada do Google (verificação de desenvolvedor) e ver se o aviso some; obrigatório para o app ir a outras pessoas.
- [x] TCX do Watch 7, leitor de FIT e notificação do Windows validados (27/10/2026).
