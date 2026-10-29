---
paths:
  - "treino/ingest/**"
  - "treino/core/**"
  - "tests/**"
---

# Leitura de fontes, cálculos e testes

- Antes de mexer em leitores ou cálculos, ler `docs/dados.md` (fatos observados nos dados reais).
- `core/` é cálculo puro: sem banco, sem rede, sem arquivos.
- Testes só com dados sintéticos gerados no próprio teste (ver `make_gpx`, `make_csv`, `make_payload`). Nunca copiar trechos dos arquivos reais, que têm GPS da casa do usuário.
- Para inspecionar os dados reais, usar scripts no scratchpad que leem `D:\dados\strava\export_<número>.zip` direto e não imprimem coordenadas.
- Importações precisam ser idempotentes (rodar duas vezes não duplica).
- Limpeza de dados é conservadora: marcar como suspeito em vez de apagar, guardando o valor original.
- A FC máxima de 214 é estimativa coerente com os dados; não "corrigir" sem evidência.
