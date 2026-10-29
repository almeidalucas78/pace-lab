# 0005. Camadas core, ingest, services e interfaces

- Status: aceita
- Data: 2026-10-27

## Contexto
O mesmo dado é usado pela CLI, pela API, pelo agendador, pelo MCP e pelo chat; regras espalhadas divergiriam.

## Decisão
- `core/`: só cálculo puro (sem banco, sem IO).
- `ingest/`: leitura de fontes como adaptadores.
- `services.py`: única camada de regras e consultas.
- CLI, API, agendador, MCP e chat chamam só `services`. Toda interface visual fala com a API, nunca direto com o banco.

## Consequências
- Uma regra nova (ex.: aderência ao plano) é escrita uma vez e aparece em todas as interfaces.
- `services.py` cresce; quando passar de umas 800 linhas, dividir em pacote `services/` mantendo os mesmos nomes.
