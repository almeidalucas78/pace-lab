# 0001. Strava só pelo export completo, nunca pela API

- Status: aceita (o usuário pediu reavaliação depois de testar o Health Connect)
- Data: 2026-10-27

## Contexto
A política da API do Strava (strava.com/legal/api_policy, vigente desde 1/6/2026, conferida em 27/10/2026):
- seção 5.3: proíbe usar dados da API, ou dados derivados deles, para "operate an AI Application", incluindo "ingestion into a context window or working memory";
- seção 3.5: a única exceção é o Strava MCP oficial, uso pessoal de assinantes;
- seção 6.2: cache de no máximo 7 dias; seção 5.5: proíbe índice persistente;
- não há exceção para uso pessoal ou app de um usuário só;
- seção 6.6: o usuário tem direito de exportar os próprios dados.

O sistema existe para a IA ler os treinos, então dados da API não poderiam entrar no chat nem ficar no banco.

## Decisão
- O Strava entra só pelo export completo da conta (`treino importar-strava`), idempotente.
- O conector MCP oficial do Strava pode ser usado no Claude separadamente; os dados dele não entram no nosso banco.

## Consequências
- Treinos novos precisam de outra fonte (ver 0002).
- Se o Health Connect não trouxer GPS, alternativas dentro das regras: novo export do Strava de tempos em tempos (a reimportação é idempotente e o Strava prevalece, ver 0003), o Strava MCP direto no Claude, ou o export de dados pessoais do Samsung Health (não verificado).
- Pendente: em 27/10/2026 o usuário pediu para reavaliar o uso da API caso a limitação do Health Connect se confirme; em 28/10/2026 disse que quer testar depois. Até lá, nada de API.
