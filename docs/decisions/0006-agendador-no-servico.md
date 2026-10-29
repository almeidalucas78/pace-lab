# 0006. Agendador dentro do serviço, iniciado à mão

- Status: aceita
- Data: 2026-10-27

## Contexto
Precisa sincronizar com o celular periodicamente. O Agendador do Windows não existe num servidor. O usuário prefere abrir o serviço ele mesmo ao ligar o PC.

## Decisão
- O agendador é uma thread dentro do processo da API (`treino servico`): sincroniza ao iniciar e a cada `SYNC_INTERVALO_MIN`.
- O usuário abre `iniciar-treino.bat`; início automático fica a critério dele (atalho na pasta Inicializar).

## Consequências
- Funciona igual num servidor.
- Com a janela fechada, nada sincroniza; ao reabrir, a primeira rodada recupera o período.
