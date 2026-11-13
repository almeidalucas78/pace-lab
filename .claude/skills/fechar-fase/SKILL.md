---
description: Fecha uma fase do projeto Treino - confere CI e issues, roda as checagens, confere o critério de pronto, atualiza ROADMAP, CHANGELOG, ARCHITECTURE, ADRs e README, abre o pull request de fechamento e, depois do merge, cria a tag e a Release no GitHub. Use quando o usuário pedir para fechar ou concluir uma fase.
argument-hint: "[número da fase]"
disable-model-invocation: true
---

# Fechar a fase $ARGUMENTS

Pare no primeiro problema e mostre ao usuário. Merge, tag e Release só com o ok dele. O fluxo completo está em `docs/processo.md`.

## 1. GitHub
- CI da `main` verde: `gh run list --branch main --workflow ci.yml --limit 1`.
- Issues da milestone: `gh issue list --milestone "Fase $ARGUMENTS" --state open`. Toda issue aberta precisa ser fechada (feita) ou movida para outra milestone com o motivo num comentário (com o ok do usuário).
- Pull requests abertos da fase: `gh pr list`. Nada da fase pode ficar pendente.

## 2. Checagens
Numa branch `docs/fechar-fase-$ARGUMENTS` a partir da `main` atualizada, rode tudo de `CONTRIBUTING.md`:
- `.\.venv\Scripts\pre-commit.exe run --all-files` (ruff, checagens do projeto, oxlint).
- `cd server; ..\.venv\Scripts\mypy.exe`.
- `.\.venv\Scripts\python.exe -m pytest -q server`.
- Se a fase mexeu em `web/`: `npm run lint`, `npm run build` e `npm test` na pasta `web`.
- Se mexeu em `android/`: build local do APK (o CI ainda não compila o Android).
Se algo falhar, pare e mostre a saída.

## 3. Critério de pronto
Abra `docs/fases/fase-$ARGUMENTS.md`:
- Confira cada item do critério de pronto e cada etapa; marque o que foi feito.
- Se o teste manual ainda não foi feito, faça agora (ou diga ao usuário o que ele precisa rodar).
- Preencha "Resultado": o que entrou, o que mudou em relação ao plano e por quê, o que ficou pendente (com o número da issue).
- Status `concluída` e data.

## 4. Decisões
- Toda decisão nova da fase tem ADR em `docs/decisions/` e linha na tabela do `README.md` de lá.
- Decisão que mudou: marque o ADR antigo como `substituída por NNNN`, nunca apague.

## 5. Documentação
- `docs/ROADMAP.md`: fase como ✅, resumo de uma linha, pendências novas ou resolvidas.
- `docs/ARCHITECTURE.md`: se mudaram pacotes, fluxos ou tabelas.
- `docs/dados.md`: se apareceu fato novo sobre os dados reais.
- `README.md`: comandos ou configurações novas para o usuário.
- `.env.example`: variáveis novas.
- `CHANGELOG.md`: mova o "Não lançado" para uma versão nova com a data (`0.$ARGUMENTS.0`, ver "Versões" em `docs/processo.md`); suba a `version` no `server/pyproject.toml` na mesma numeração.
- `AGENTS.md`: só se mudou o mapa do código ou uma regra; mantenha abaixo de 200 linhas (o `CLAUDE.md` e o `GEMINI.md` só importam ele).

## 6. Dados pessoais
- `python scripts/checagens.py` (já roda no pre-commit e no CI; confira de novo) e `git status` sem nada da lista "Nunca vai para o repositório" do `AGENTS.md`.
- Texto do pull request e da Release sem dados reais (GPS, nomes de rede ou de aparelho, tokens).

## 7. Pull request de fechamento
Mostre o resumo das mudanças. Com o ok do usuário: commit `docs: fecha a fase $ARGUMENTS`, push da branch, `gh pr create` com o modelo do repositório (corpo com o resumo da fase e `Fecha #...` das issues de fechamento, se houver). Espere o CI ficar verde; o merge é do usuário (ou com o ok dele).

## 8. Tag e Release (depois do merge, com o ok do usuário)
1. `git checkout main; git pull`.
2. Tag anotada no commit do merge: `git tag -a v0.$ARGUMENTS.0 -m "Fase $ARGUMENTS: título"` e `git push origin v0.$ARGUMENTS.0`.
3. Release com o trecho da versão no CHANGELOG (salve o trecho num arquivo no scratchpad): `gh release create v0.$ARGUMENTS.0 --title "v0.$ARGUMENTS.0: Fase $ARGUMENTS, título" --notes-file <arquivo>`.
4. Fechar a milestone: `gh api -X PATCH repos/{owner}/{repo}/milestones/<número> -f state=closed`.
