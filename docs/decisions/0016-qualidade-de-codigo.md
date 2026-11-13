# 0016. Qualidade de código: ruff, mypy gradual, oxlint, checagens do projeto e pre-commit

- Status: aceita
- Data: 2026-11-12

## Contexto
Até a fase 7 o projeto não tinha lint, formatador nem checagem de tipos no Python, nem lint no painel (fase 8, etapa 4). Verificado em 12/11/2026:
- ruff 0.17 (lint e formatação, PyPI), mypy 2.4 (PyPI), pre-commit 4.7 (PyPI), hooks `ruff-pre-commit` v0.17.4 e `pre-commit-hooks` v6.0.0 (GitHub).
- O painel usa TypeScript 7.0. O `typescript-eslint` 8.72 (necessário para o ESLint ler TypeScript) aceita só TypeScript `>=4.8.4 <6.1.0`, inclusive na versão canary (npm, `peerDependencies`).
- O oxlint 1.93 lê TypeScript e JSX sozinho, se integra ao TypeScript 7 (oxc.rs/docs/guide/usage/linter), traz as regras de React (incluindo as de hooks e de efeitos) e lê `.oxlintrc.json` (oxc.rs, config).

## Decisão
- **Python:** ruff para lint e formatação (linha de 120; regras E, W, F, I, B, UP, SIM, com exceções comentadas no `server/pyproject.toml`); mypy rigoroso em `treino/core/` e no modo padrão no resto, apertando aos poucos.
- **Painel:** oxlint no lugar do ESLint, com `correctness` como erro e `suspicious` como aviso; `npm run lint` falha com qualquer aviso. Exceções pontuais com comentário explicando o motivo.
- **Regras do projeto:** `scripts/checagens.py` (travessão, arquivos proibidos, chaves conhecidas e padrões privados de `data/checagens-locais.txt`, que nunca vai para o git).
- **pre-commit** com as checagens rápidas (ruff, checagens, oxlint, arquivo grande, chave privada); mypy, testes e build ficam no CI.
- `.gitattributes` com LF no repositório (o CI roda em Linux) e CRLF só nos `.bat`.

## Consequências
- O código Python foi formatado de uma vez (um commit só de formatação e correções).
- Se o `typescript-eslint` passar a aceitar o TypeScript 7, dá para reavaliar o ESLint; as regras de React do oxlint cobrem o que o painel precisa hoje.
- A versão do ruff fica fixa e igual no `pyproject.toml` e no pre-commit; o Dependabot (etapa 6) sobe as duas juntas.
