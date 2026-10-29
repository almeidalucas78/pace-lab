# 0007. Migrações com Alembic

- Status: aceita
- Data: 2026-10-27

## Contexto
Até a fase 1 o banco nascia de `create_all`, que não altera tabelas existentes. A partir da fase 2 o banco guarda dados que não vêm de export (treinos do celular, sensações, conversas, planos).

## Decisão
- Esquema versionado com Alembic; `init_db()` aplica as migrações sozinho.
- Banco da fase 1 (sem `alembic_version`) é marcado como `0001`.
- No SQLite as migrações rodam com `foreign_keys=OFF`, porque o batch do Alembic recria tabelas e, com FK ligada, apagaria amostras em cascata.
- Toda mudança de modelo tem migração nova, gerada com `alembic revision --autogenerate` e revisada à mão.

## Consequências
- Mudanças de esquema não exigem apagar e reimportar.
- Fazer backup do banco antes de migração arriscada (em `D:\dados\strava\`).
