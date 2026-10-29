# Fase 4: planos de treino e aderência

- Status: concluída
- Planejada em: 2026-10-28 · Concluída em: 2026-10-28

## Objetivo
O usuário conversa com o treinador (chat ou MCP), recebe uma proposta de plano e, ao confirmar, o plano fica salvo com as sessões dia a dia. Depois ele pergunta "como estou indo no plano?" e o sistema responde com dados: quais sessões foram feitas, puladas ou feitas em outro dia, e se distância, tempo e intensidade bateram com o planejado. A IA usa isso para ajustar o plano na conversa.

## Fora do escopo
- Interface visual do plano e da aderência (fase 5; aqui só API, CLI, chat e MCP).
- Regras fixas de periodização no código: quem monta o plano é a IA, o Python só guarda e mede (ADR 0008).
- Notificação de sessão perdida, exportar para calendário, plano detalhado de musculação (séries e cargas, fase 7).

## Decisões necessárias

1. **Como a IA altera um plano?** Recomendação: os dois jeitos. Ajustes pontuais (mover, mudar ou cancelar uma sessão) editam a sessão no lugar; reescritas grandes criam um plano novo que substitui o anterior, que fica arquivado como histórico. Só um plano ativo por vez.
2. **Como casar sessão planejada com treino feito?** Recomendação: mesmo esporte no mesmo dia (fuso local). Se não houver, aceitar um treino do dia anterior ou seguinte que não esteja casado com outra sessão, marcado como "feito em outro dia". Duplicatas nunca entram. Treino sem sessão correspondente aparece como "extra".
3. **Que metas uma sessão pode ter?** Recomendação: todas opcionais, a IA escolhe: distância (km), duração (min), faixa de ritmo (min/km), zona de FC alvo (z1 a z5) e percepção de esforço. Descanso é uma sessão do tipo `descanso`.
4. **Musculação entra no plano?** Recomendação: sim, só como "feito ou não" (os dados do Hevy ainda não são analisados).
5. **A IA salva sem perguntar?** Recomendação: não. Regra no prompt: mostrar o plano, pedir confirmação e só então chamar `salvar_plano`.

Respondidas em 28/10/2026: todas as recomendações aceitas. Registrado no [ADR 0010](../decisions/0010-planos-e-aderencia.md).

## Mudanças no banco
Migração `0004`, só tabelas novas (sem tocar nas existentes):

- `training_plans`: `id`, `created_utc`, `updated_utc`, `title`, `goal` (objetivo em texto), `start_date`, `end_date`, `status` (`ativo`, `arquivado`, `substituido`), `replaced_by` (FK para o plano novo), `conversation_id` (FK opcional para a conversa em que nasceu), `notes`.
- `planned_sessions`: `id`, `plan_id` (FK, cascade), `day`, `sport`, `kind` (`rodagem`, `longao`, `intervalado`, `ritmo`, `regenerativo`, `descanso`, `musculacao`, `outro`), `description`, `target_distance_km`, `target_duration_min`, `target_pace_min_s_km`, `target_pace_max_s_km`, `target_hr_zone`, `target_rpe`, `status` (`planejada`, `cancelada`), `notes`.

O casamento com os treinos **não é gravado**: é calculado na hora (assim um treino que chega depois pelo celular ou por um novo export entra sozinho). Planos são dados que nenhum export recupera: backup do banco antes de migrar.

## Etapas
1. [x] **Modelos e migração**: `TrainingPlan` e `PlannedSession` em `treino/db/models.py` e `db/__init__.py`; migração `0004` gerada e revisada; backup do banco e migração do banco real com contagens conferidas.
2. [x] **Cálculo de aderência (puro)**: `treino/core/aderencia.py` recebe sessões e treinos (dataclasses simples) e devolve, por sessão, o status (`feita`, `feita_outro_dia`, `perdida`, `futura`, `cancelada`, `descanso`) e as comparações (distância e duração em % do alvo, ritmo dentro ou fora da faixa, % do tempo na zona alvo usando `hr_zones_s`), mais os treinos extras e o resumo por semana. Testes em `tests/test_aderencia.py`.
3. [x] **Serviços**: em `treino/services.py`, `create_plan` (arquiva o ativo anterior como `substituido`), `get_plan`, `active_plan`, `list_plans`, `update_session` (mover, alterar metas, cancelar), `plan_adherence` (monta os dados, chama o core, devolve ficha resumida). Validações: datas dentro do plano, esporte e tipo conhecidos, faixa de ritmo coerente. Testes em `tests/test_planos.py`.
4. [x] **Ferramentas da IA**: em `treino/ia/ferramentas.py`, `salvar_plano`, `plano_atual`, `aderencia_plano`, `alterar_sessao`, `listar_planos`. Atualizar `treino/ia/prompt.py` (tirar o "ainda não existe ferramenta para salvar planos"; regra de confirmar antes de salvar; datas sempre absolutas AAAA-MM-DD). Testes em `tests/test_ia.py`.
5. [x] **API e CLI**: `GET /planos`, `GET /planos/ativo`, `GET /planos/{id}`, `GET /planos/{id}/aderencia`; comando `treino plano` (plano ativo com status de cada sessão e resumo da semana).
6. [x] **Docs**: ADR 0010, `docs/ARCHITECTURE.md` (tabelas e fluxo), `README.md` (como pedir um plano no chat, `treino plano`).

## Critério de pronto
- [x] Testes novos com dados sintéticos passando: casamento no mesmo dia, em dia vizinho, sessão perdida, treino extra, duplicata ignorada, metas de ritmo e zona, substituição de plano, edição de sessão, validações.
- [x] Todos os testes antigos continuam passando.
- [x] Banco real migrado com as contagens de `activities` e `samples` iguais antes e depois.
- [x] Teste manual no chat com o Claude (`treino chat`): "Monte um plano retroativo de 13/10 a 26/10 com rodagens às segundas e quartas e um longão no domingo, só para eu testar a aderência." A IA mostra o plano e pede confirmação; depois de confirmar, salva; em seguida "como foi minha aderência nesse plano?" deve casar as corridas reais de 13/10 e 20/10 e apontar as sessões perdidas.
- [x] Docs atualizadas.

## Resultado (preenchido no fechamento)

**Entrou:** migração `0004` (`training_plans`, `planned_sessions`); `core/aderencia.py` (casamento mesmo dia, depois dia vizinho; metas de distância, duração, ritmo, zona e esforço; extras; resumo por semana); serviços de plano em `services.py`; ferramentas da IA; `treino plano`; rotas `/planos`; prompt com confirmação antes de salvar; ADR 0010. 35 testes passando (13 novos).

**Mudou em relação ao plano:**
- 7 ferramentas em vez de 5: `adicionar_sessao` (incluir sessão sem refazer o plano) e `arquivar_plano` (o status "arquivado" estava previsto no ADR 0010, mas sem ação para chegar nele; foi preciso para descartar o plano de teste).
- O plano é ligado à conversa em que nasceu depois da resposta (`link_plans_to_conversation`), sem a IA precisar informar o id da conversa.
- `pace_str` foi para `core/formato.py`, para o core e os serviços usarem o mesmo formatador.
- Pelo MCP, erros de validação viram erro do protocolo (o `{"erro": ...}` vale para o chat).

**Teste manual (28/10/2026, Claude, banco real):** o Claude montou o plano retroativo de 13/10 a 26/10, mostrou dia a dia, perguntou se podia salvar e só salvou depois do sim. Aderência: 2 de 6 sessões feitas, ambas em dia vizinho (corridas reais de 13/10 e 20/10) e fora do alvo; longões e rodagens de 21 e 26/10 perdidos; 6 musculações como extras. O plano "Teste de aderencia" (id 1) ficou ativo no banco.

**Pendente:** decidir se arquiva o plano de teste; aderência só testada com Claude (Gemini continua sem chave).
