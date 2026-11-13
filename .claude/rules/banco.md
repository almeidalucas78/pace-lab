---
paths:
  - "server/treino/db/**"
  - "server/treino/migrations/**"
  - "server/alembic.ini"
---

# Banco e migrações

- Toda mudança em `server/treino/db/models.py` precisa de migração nova: gerar com `alembic -c server/alembic.ini revision --autogenerate -m "descricao" --rev-id NNNN` apontando `DATABASE_URL` para um SQLite vazio no scratchpad (depois de `alembic upgrade head` nele), e revisar o arquivo gerado à mão.
- Mudar esquema é decisão cara: perguntar ao usuário antes.
- Antes de migrar o banco real, copiar `data/treino.db` para `D:\dados\strava\` com a data no nome.
- `sensations`, `conversations`, `chat_messages` e tabelas futuras de planos guardam dados que nenhum export recupera: nunca apagar nem recriar.
- No SQLite as migrações rodam com `foreign_keys=OFF` (feito em `init_db`); não remover, senão o batch do Alembic apaga amostras em cascata.
- Datas sempre com `UTCDateTime` e com fuso.
- Novos modelos entram também em `treino/db/__init__.py`.
- Depois de migrar, conferir as contagens (`activities`, `samples`) antes e depois.
