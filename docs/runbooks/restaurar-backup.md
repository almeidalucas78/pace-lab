# Runbook: restaurar o banco a partir de um backup

Hoje o banco é o SQLite em `data/treino.db`; os backups ficam em `D:\dados\strava\` com a data no nome. Na fase 9, com Postgres no servidor, este runbook ganha a parte do servidor.

1. **Parar o serviço** (fechar a janela do `scripts\iniciar-treino.bat`). Com o serviço aberto, o SQLite pode estar no meio de uma gravação.
2. **Guardar o banco atual**, mesmo estragado: copiar `data\treino.db` (e `treino.db-wal` e `treino.db-shm`, se existirem) para `D:\dados\strava\treino-antes-de-restaurar-AAAA-MM-DD.db`.
3. **Copiar o backup** escolhido para `data\treino.db` e apagar os `treino.db-wal` e `treino.db-shm` que sobraram.
4. **Conferir:** `.\.venv\Scripts\treino.exe resumo` (contagens por esporte) e `.\.venv\Scripts\alembic.exe -c server\alembic.ini current` (versão do esquema). Se a versão for antiga, o próximo comando `treino` migra sozinho.
5. **Recuperar o que faltou:** treinos do celular posteriores ao backup voltam ao sincronizar no app; os do Strava, com `treino importar-strava` no export. Sensações, conversas e planos criados depois do backup não têm outra cópia.
6. Abrir o serviço de novo e olhar o painel.
