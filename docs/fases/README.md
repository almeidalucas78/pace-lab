# Planos de fase

Um arquivo por fase (`fase-N.md`), criado com `/planejar-fase N` antes de qualquer código e atualizado com `/fechar-fase N` no fim. As fases 1 a 3 foram feitas antes deste ritual; o resumo delas está no [ROADMAP](../ROADMAP.md).

## Modelo

```markdown
# Fase N: título

- Status: planejada | em andamento | concluída
- Planejada em: AAAA-MM-DD · Concluída em: AAAA-MM-DD

## Objetivo
O que o usuário consegue fazer ao final, em 2 ou 3 frases.

## Fora do escopo
O que fica para outra fase.

## Decisões necessárias
Perguntas para o usuário e decisões novas (viram ADR no fechamento).

## Mudanças no banco
Tabelas e colunas novas, migração, risco para dados que não se recuperam.

## Etapas
1. [ ] Etapa pequena e testável (arquivos envolvidos)
2. [ ] ...

## Critério de pronto
- [ ] Testes novos com dados sintéticos passando
- [ ] Teste manual: comando ou pergunta no chat que mostra a fase funcionando
- [ ] Docs atualizadas

## Resultado (preenchido no fechamento)
O que entrou, o que mudou do plano e por quê, o que ficou pendente.
```
