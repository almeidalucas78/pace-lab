---
description: Planeja uma fase do roadmap do projeto Treino, escreve docs/fases/fase-N.md e, depois do ok, cria a milestone e as issues no GitHub. Use quando o usuário pedir para planejar ou começar uma fase.
argument-hint: "[número da fase]"
disable-model-invocation: true
---

# Planejar a fase $ARGUMENTS

Objetivo: sair com um plano aprovado pelo usuário em `docs/fases/fase-$ARGUMENTS.md` e com o trabalho organizado no GitHub (milestone `Fase $ARGUMENTS` e uma issue por etapa). **Não escreva código nesta etapa.** O fluxo completo está em `docs/processo.md`.

## 1. Entender o estado atual
Leia, nesta ordem:
- `docs/ROADMAP.md`: objetivo da fase e pendências que a afetam.
- Issues já abertas da fase e sem milestone: `gh issue list --milestone "Fase $ARGUMENTS"` e `gh issue list --search "no:milestone"`.
- `docs/decisions/README.md` e os ADRs relacionados ao tema da fase.
- `docs/ARCHITECTURE.md` e `docs/dados.md`.
- Os planos de fases anteriores em `docs/fases/` (se houver).
- O código que a fase vai tocar (comece por `server/treino/services.py` e pelos módulos citados na arquitetura).

Se já existir `docs/fases/fase-$ARGUMENTS.md`, revise-o em vez de começar do zero.

## 2. Verificar antes de propor
- Biblioteca, API ou ferramenta nova: confira a documentação oficial e a assinatura no pacote instalado. Se não der para verificar, diga no plano.
- Se a fase contradiz um ADR aceito, não decida sozinho: coloque como pergunta.

## 3. Escrever o plano
Crie `docs/fases/fase-$ARGUMENTS.md` seguindo o modelo de `docs/fases/README.md`:
- Objetivo do ponto de vista do usuário e o que fica fora do escopo.
- Decisões necessárias, como perguntas objetivas com a sua recomendação.
- Mudanças no banco (tabelas, colunas, migração, risco para dados não recuperáveis).
- Etapas pequenas, cada uma testável, com os arquivos envolvidos. Cada etapa vira uma issue e, em geral, um pull request.
- Critério de pronto com testes sintéticos e um teste manual concreto (comando ou pergunta no chat).

Status do plano: `planejada`. No `docs/ROADMAP.md`, marque a fase como 📝. O plano entra na `main` por pull request (`docs: plano da fase $ARGUMENTS`), como todo o resto.

## 4. Apresentar e esperar
Mostre ao usuário um resumo curto (objetivo, etapas, mudanças no banco) e as perguntas. **Pare e espere o ok.**

## 5. Depois do ok: organizar no GitHub
1. Milestone `Fase $ARGUMENTS` (crie se não existir): `gh api repos/{owner}/{repo}/milestones -f title="Fase $ARGUMENTS" -f description="..."`.
2. Uma issue por etapa, com o modelo "Tarefa": título `Fase $ARGUMENTS, etapa K: nome`, corpo com o objetivo, o link para a etapa no plano e o critério de pronto; labels `tipo: tarefa` e as de área (`área: server`, `área: web`, ...); milestone `Fase $ARGUMENTS`. Não duplique issues que já existem (confira antes pela lista).
3. Issues soltas que pertencem à fase (pendências, bugs): ponha na milestone.
4. Status `em andamento` no plano e 🚧 no ROADMAP, no mesmo pull request das decisões respondidas.
5. Decisões tomadas viram ADR na hora (modelo em `docs/decisions/README.md`).

Depois disso, cada etapa segue a seção 2 de `docs/processo.md`: branch `tipo/NUMERO-resumo`, commits no padrão, pull request com `Fecha #NUMERO`, CI verde, merge pelo usuário (ou com o ok dele) e a etapa marcada no plano.
