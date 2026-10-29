# 0003. Deduplicação por horário e esporte; Strava prevalece

- Status: aceita
- Data: 2026-10-27

## Contexto
O histórico vem do Strava e os treinos novos do Health Connect; no período em que as fontes se sobrepõem, o mesmo treino aparece duas vezes. O Strava corrige o GPS e tem o resumo oficial.

## Decisão
- Treinos do mesmo esporte com início a até 10 min do primeiro do grupo são o mesmo treino.
- Vale o de fonte mais confiável (`SOURCE_PRIORITY`: Strava antes do Health Connect); na mesma fonte, o mais cedo.
- O outro fica marcado em `possible_duplicate_of` e sai dos totais, sem ser apagado.

## Consequências
- Um novo export do Strava completa parciais e mapa dos treinos que vieram do Health Connect sem intervenção.
- Dois treinos reais do mesmo esporte com menos de 10 min de diferença seriam fundidos (raro; revisar se acontecer).
