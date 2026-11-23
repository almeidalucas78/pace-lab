# 0018. Dados por usuário: user_id em cada registro, conta passada ao services e dono no PC

- Status: aceita
- Data: 2026-11-23

## Contexto
Com as contas (ADR 0017), cada pessoa precisa ver e alterar só os próprios dados (ADR 0014; checklist da fase 9 em `docs/seguranca.md`). Até aqui, o `services.py` recebia as configurações globais (`Settings`) e consultava a tabela inteira; FC máxima, FC de repouso e fuso vinham do `.env`. As ferramentas da IA são as mesmas no chat do painel e no MCP local, e pegavam as configurações sozinhas.

## Decisão
- **`user_id` em todo dado com dono:** `activities`, `sensations`, `conversations`, `training_plans`, `sync_state` e `daily_load` (os dois últimos com o usuário na chave primária). Amostras, parciais, mensagens e sessões de plano herdam pelo registro pai. A chave única dos treinos vira `(user_id, source, source_id)`.
- **Preferências na conta:** FC máxima, FC de repouso e fuso passam para `users`; o `.env` só é lido pela migração 0006, que os copia para a conta do dono. Ajuste pelo comando `treino ajustar-conta` (no painel, na etapa 7).
- **Migração dos dados existentes:** tudo vai para a primeira conta do banco; sem conta, cria-se a conta provisória `dono@pacelab.local`, sem senha, que o `treino criar-usuario` assume depois.
- **`Conta` no lugar de `Settings`:** um objeto com id do usuário, FC máxima, FC de repouso e fuso vai para cada função do `services` que lê ou grava dados de usuário; toda consulta filtra por ela, e buscar por id devolve "não existe" quando o registro é de outra conta.
- **Quem é a conta em cada entrada:** na API, a do login; com o `API_TOKEN` antigo (até as etapas 7 e 8), a do dono. Nos comandos do PC (`treino ...`) e no MCP local, a do dono (a primeira do banco).
- **Ferramentas da IA:** `executar(nome, args, conta)` marca a conta num `ContextVar` durante a chamada; a ferramenta lê `conta.atual()`. Sem marca (MCP local), vale a do dono. O formato das ferramentas não muda e continua o mesmo para MCP, Claude e Gemini.

## Consequências
- Esquecer o filtro numa consulta nova vaza dados entre contas; os testes de isolamento (`tests/test_isolamento.py`) cobrem cada rota e ferramenta atual, e funções novas do `services` precisam receber a `Conta`.
- O MCP local e os comandos do PC só enxergam a conta do dono; um MCP remoto com OAuth (fase 12) vai marcar a conta de quem conectou.
- A migração 0006 recria `sync_state` e `daily_load` (copiando as linhas) e reconstrói as tabelas com `user_id` no SQLite pelo batch do Alembic, com as chaves estrangeiras desligadas (`init_db`).
