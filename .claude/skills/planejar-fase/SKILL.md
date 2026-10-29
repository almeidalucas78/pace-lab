---
description: Planeja uma fase do roadmap do projeto Treino e escreve docs/fases/fase-N.md, sem implementar nada. Use quando o usuário pedir para planejar ou começar uma fase.
argument-hint: "[número da fase]"
disable-model-invocation: true
---

# Planejar a fase $ARGUMENTS

Objetivo: sair com um plano aprovado pelo usuário em `docs/fases/fase-$ARGUMENTS.md`. **Não escreva código nesta etapa.**

## 1. Entender o estado atual
Leia, nesta ordem:
- `docs/ROADMAP.md`: objetivo da fase e pendências que a afetam.
- `docs/decisions/README.md` e os ADRs relacionados ao tema da fase.
- `docs/ARCHITECTURE.md` e `docs/dados.md`.
- Os planos de fases anteriores em `docs/fases/` (se houver).
- O código que a fase vai tocar (comece por `treino/services.py` e pelos módulos citados na arquitetura).

Se já existir `docs/fases/fase-$ARGUMENTS.md`, revise-o em vez de começar do zero.

## 2. Verificar antes de propor
- Biblioteca, API ou ferramenta nova: confira a documentação oficial e a assinatura no pacote instalado. Se não der para verificar, diga no plano.
- Se a fase contradiz um ADR aceito, não decida sozinho: coloque como pergunta.

## 3. Escrever o plano
Crie `docs/fases/fase-$ARGUMENTS.md` seguindo o modelo de `docs/fases/README.md`:
- Objetivo do ponto de vista do usuário e o que fica fora do escopo.
- Decisões necessárias, como perguntas objetivas com a sua recomendação.
- Mudanças no banco (tabelas, colunas, migração, risco para dados não recuperáveis).
- Etapas pequenas, cada uma testável, com os arquivos envolvidos.
- Critério de pronto com testes sintéticos e um teste manual concreto (comando ou pergunta no chat).

Status do plano: `planejada`. No `docs/ROADMAP.md`, marque a fase como 📝.

## 4. Apresentar e esperar
Mostre ao usuário um resumo curto (objetivo, etapas, mudanças no banco) e as perguntas. **Pare e espere o ok.** Depois do ok, mude o status para `em andamento` (🚧 no ROADMAP) e implemente etapa por etapa, marcando os checkboxes. Decisões tomadas no caminho viram ADR na hora (modelo em `docs/decisions/README.md`).
