# Fatos sobre os dados do usuário

O que foi observado nos dados reais. Os arquivos reais nunca entram no repositório nem nos testes (têm GPS de onde o usuário mora).

## Export do Strava
- Fica em `D:\dados\strava\export_<número>.zip` (fora do repositório). 359 atividades, de jan/2023 a out/2026.
- `activities.csv` com datas em português e em UTC ("26 de out. de 2026, 15:05:43").
- Colunas com nome repetido: o primeiro bloco é formatado (distância em km com vírgula), o segundo é numérico (distância em metros). Usar sempre o segundo.
- O ID da atividade no CSV é diferente do número no nome do arquivo.
- Cadência de corrida exportada por perna (multiplicar por 2); a de caminhada já vem total.

## Arquivos dos treinos
- **TCX recente do Watch 7** (`21821148731.tcx.gz`, out/2026): uma linha por segundo, sem horários repetidos. Traz FC, cadência por perna, velocidade, distância, GPS, altitude e `Watts` (potência de corrida, ainda não lida). `AverageHeartRateBpm` da volta vem vazio.
- **TCX antigos do Samsung:** várias linhas com o mesmo horário (uma com FC, outra com cadência e velocidade); o leitor junta por horário.
- **GPX do Samsung Health** não traz o tipo de atividade.
- **FIT** (8 arquivos, fev/2025): 2 corridas com GPS e FC, 3 "training" e 3 "cycling" curtos (cerca de 3 min, sem distância, provavelmente registros acidentais).

## Musculação
- 168 atividades; colunas de séries, repetições e peso total vazias no CSV.
- 59 têm `.json.gz` do Hevy (o 60º `.json` do zip é o `messaging.json`, que não é treino), 2 têm FIT, 107 não têm arquivo.
- Formato do JSON do Hevy: `start_time`, `utc_offset`, `elapsed_time`, `active_time`, `total_calories`, `streams` (`time` em segundos relativos e `heartrate`) e `sets` (`exercise_type` em códigos como `SMITH_MACHINE_SQUAT`, `repetitions`, `weight` inteiro e, às vezes, `start_time` e `duration`). 43 exercícios distintos. Unidade do peso não confirmada (provável kg).

## Frequência cardíaca
- A FC sobe de forma contínua até 200 a 210 bpm em algumas corridas.
- `FC_MAX` não está configurada; a estimativa automática deu **214** (maior média de 30 s nos treinos com FC "ok").
- Não é um treino isolado: 10 corridas diferentes (2024 a 2025) têm pico sustentado de 30 s entre 207 e 214, coerente com a FC máxima do resumo do Strava.
- Não tratar como erro sem evidência, e sempre deixar claro que é estimativa.

## Samsung Health Data SDK (lido pelo DataViewer em 11/11/2026)
- Corrida de 03/11/2026 (horários em UTC no SDK: 21:18Z = 18:18 em Brasília): `ExerciseSession` com `route` (5.326 pontos de GPS), `log` (10.904 registros com FC, velocidade e cadência), `distance` 17.027 m, `duration` 5.355 s, `meanHeartRate` 187, `maxHeartRate` 206, `meanCadence` 170 (já em passos por minuto, as duas pernas), `calories` 1.081, `altitudeGain` 31,8 m, `vo2Max` 47,48, `count` 15.199 passadas (`countType` STRIDE).
- O Health Connect mostra a mesma corrida só com horário e duração (sem percurso).

- Esteira (corridas de 28/10 e 09/11/2026) e musculação (`WEIGHT_MACHINE`) chegam com percurso em que todos os pontos são latitude 0 e longitude 0. O conversor ignora (0, 0) e, sem GPS, calcula a distância pela velocidade do `log` (`distancia_fonte` = `velocidade`), ajustada ao total do resumo.
- Na primeira sincronização (40 treinos, 12/10 a 10/11/2026) apareceram sessões `OTHER` no mesmo horário de sessões de musculação, e natação em piscina (`POOL_SWIMMING`, hoje gravada como `other`).
