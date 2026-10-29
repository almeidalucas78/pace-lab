---
paths:
  - "treino/ia/**"
---

# IA, ferramentas e MCP

- Ferramenta nova entra só em `treino/ia/ferramentas.py` (decorador `@ferramenta`): ela aparece sozinha no MCP, no Claude e no Gemini. O esquema sai das anotações de tipo (`Annotated` + `Field`).
- Ferramentas chamam só `services` e devolvem fichas resumidas: nada de amostras brutas, GPS ou listas longas.
- Erros de entrada viram `{"erro": ...}` (via `executar`), para a IA poder reagir.
- Ferramentas que gravam usam `somente_leitura=False`.
- `ia/prompt.py`: o texto do sistema fica estável (sem data nem valores variáveis) para aproveitar cache; a data vai em `com_data()`. Nunca usar travessão no prompt.
- Testes nunca chamam provedor real: usar `ProvedorFalso` / `GeminiFalso` de `tests/test_ia.py`.
- Antes de usar qualquer parâmetro novo do `claude-agent-sdk`, `google-genai` ou `mcp`, conferir a documentação oficial e a assinatura no pacote instalado.
- O Claude do chat continua sem acesso a arquivos e comandos (`tools=[]`, `setting_sources=[]`).
