# Processo de trabalho

Como o Pace Lab é construído, do plano ao código na `main`. Vale para pessoas e para qualquer IA. No Claude Code, as skills `/planejar-fase` e `/fechar-fase` fazem os passos 1 e 4; em outras ferramentas, siga o texto abaixo.

## Visão geral

```
fase no ROADMAP → plano (docs/fases/fase-N.md) → milestone e issues no GitHub
  → para cada issue: branch → commits → pull request → CI verde → merge na main
  → fechamento da fase: docs, CHANGELOG, tag e Release
```

> Desde 12/11/2026 (fase 8, etapa 7) a `main` é protegida: só recebe pull request com os três jobs do CI verdes e a branch em dia com a `main`; merge só por squash. Vale para todos, inclusive administradores.

## 1. Planejar a fase

1. Ler o estado: `docs/ROADMAP.md`, `docs/decisions/README.md` e os ADRs do tema, `docs/ARCHITECTURE.md`, `docs/dados.md`, planos anteriores e o código que a fase toca.
2. Verificar antes de propor: biblioteca, API ou ferramenta nova só com a documentação oficial conferida. Se a fase contradiz um ADR aceito, vira pergunta ao usuário.
3. Escrever `docs/fases/fase-N.md` pelo modelo de `docs/fases/README.md`: objetivo, fora do escopo, decisões necessárias (com recomendação), mudanças no banco, etapas pequenas e testáveis, critério de pronto.
4. Status `planejada`; ROADMAP com 📝.
5. Apresentar ao usuário e **esperar o ok**. Nada de código antes.
6. Com o ok: criar a milestone `Fase N` e uma issue por etapa (modelo "Tarefa"), com o link para o plano. Status `em andamento`; ROADMAP com 🚧.

## 2. Trabalhar numa issue

1. Pegar a próxima issue aberta da milestone (`gh issue list --milestone "Fase N"`).
2. Criar a branch a partir da `main` atualizada: `tipo/NUMERO-resumo`, por exemplo `feat/42-login-google`.
3. Implementar com testes (dados sintéticos). Decisão nova no caminho vira ADR na hora (`docs/decisions/`).
4. Rodar as checagens locais (`CONTRIBUTING.md`).
5. Commits em Conventional Commits: `feat(api): rota de login`, tipo em inglês, texto em português.

## 3. Pull request

1. Abrir com o modelo do repositório; o corpo diz `Closes #NUMERO` (o GitHub só fecha a issue com as palavras-chave em inglês: close, fix, resolve), o que mudou, como foi testado e o que ficou de fora.
2. O CI precisa ficar verde. Se falhar, corrigir na mesma branch.
3. Revisão: o usuário aprova (ou pede ajuste). Uma IA pode revisar antes (`/code-review` no Claude Code), mas o merge é do usuário ou com o ok dele.
4. Merge por "squash", com a mensagem no padrão de commit. A branch é apagada.
5. Marcar a etapa como feita no `docs/fases/fase-N.md`.

## 4. Fechar a fase

1. Testes e CI verdes na `main`.
2. Critério de pronto conferido, teste manual feito, "Resultado" preenchido, status `concluída` com data.
3. ADRs novos com linha no índice; ADR substituído marcado, nunca apagado.
4. Docs: ROADMAP (✅), ARCHITECTURE, `dados.md`, README, `.env.example`, `AGENTS.md` se mudou o mapa do código ou uma regra.
5. `CHANGELOG.md`: "Não lançado" vira a versão nova com data; `version` no `pyproject.toml` igual.
6. Checagem de dados pessoais (lista em "Nunca vai para o repositório" do `AGENTS.md`).
7. Com o ok do usuário: tag `vX.Y.Z` e Release no GitHub com o trecho do CHANGELOG; milestone fechada.

## Bugs e ideias fora da fase

- Bug: issue com o modelo "Bug" (passos, esperado, obtido), sem dados reais do usuário. Urgente entra na fase atual; o resto vai para uma milestone futura.
- Ideia: issue sem milestone, ou anotação no ROADMAP ("Direção futura").

## Versões

Versão `0.F.Z`: `F` é a última fase concluída, `Z` sobe em correções entre fases. A `1.0.0` fica para quando o app for usado por outras pessoas (fase 12).
