---
description: Fecha uma fase do projeto Treino - roda os testes, confere o critério de pronto, atualiza ROADMAP, CHANGELOG, ARCHITECTURE, ADRs e README, faz a checagem de dados pessoais e prepara o commit. Use quando o usuário pedir para fechar ou concluir uma fase.
argument-hint: "[número da fase]"
disable-model-invocation: true
---

# Fechar a fase $ARGUMENTS

Pare no primeiro problema e mostre ao usuário. Não faça commit nem push sem o ok dele.

## 1. Testes
Rode `.venv\Scripts\python.exe -m pytest -q`. Se algum falhar, pare e mostre a saída.

## 2. Critério de pronto
Abra `docs/fases/fase-$ARGUMENTS.md`:
- Confira cada item do critério de pronto e cada etapa; marque o que foi feito.
- Se o teste manual ainda não foi feito, faça agora (ou diga ao usuário o que ele precisa rodar).
- Preencha "Resultado": o que entrou, o que mudou em relação ao plano e por quê, o que ficou pendente.
- Status `concluída` e data.

## 3. Decisões
- Toda decisão nova da fase tem ADR em `docs/decisions/` e linha na tabela do `README.md` de lá.
- Decisão que mudou: marque o ADR antigo como `substituída por NNNN`, nunca apague.

## 4. Documentação
- `docs/ROADMAP.md`: fase como ✅, resumo de uma linha, pendências novas ou resolvidas.
- `docs/ARCHITECTURE.md`: se mudaram pacotes, fluxos ou tabelas.
- `docs/dados.md`: se apareceu fato novo sobre os dados reais.
- `README.md`: comandos ou configurações novas para o usuário.
- `.env.example`: variáveis novas.
- `CHANGELOG.md`: mova o "Não lançado" para uma versão nova com a data; suba a `version` no `pyproject.toml` na mesma numeração.
- `AGENTS.md`: só se mudou o mapa do código ou uma regra; mantenha abaixo de 200 linhas (o `CLAUDE.md` e o `GEMINI.md` só importam ele).

## 5. Checagens
- Nenhum travessão (U+2014) em arquivos do projeto (fora do `.venv`).
- `git status`: nada de `.env`, `data/`, `*.db`, arquivos de treino (`*.gpx`, `*.tcx`, `*.fit`, `*.json.gz`, `activities*`) ou `*.zip`.
- `git grep --cached` pelo valor do `API_TOKEN` do `.env` e por chaves (`AIza`, `sk-ant`): nada pode aparecer.

## 6. Commit
Mostre o resumo das mudanças e a mensagem de commit proposta (em português, primeira linha "Fase $ARGUMENTS: ..."). Com o ok do usuário, faça o commit e, se ele pedir, o push.
