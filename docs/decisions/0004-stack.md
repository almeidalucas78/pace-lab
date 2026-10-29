# 0004. Python + FastAPI + SQLAlchemy; React + TypeScript + Vite

- Status: aceita
- Data: 2026-10-27

## Contexto
Sistema pessoal no Windows, sem custo de hospedagem por enquanto, mas pronto para hospedar depois.

## Decisão
- Backend: Python, FastAPI, SQLAlchemy 2. SQLite agora; Postgres depois trocando só `DATABASE_URL`.
- Front: React + TypeScript + Vite, responsivo, virando PWA na fase mobile. Nada de Streamlit.
- Notificações do Windows com `winotify`; em outro sistema, só log.
- IA: `mcp` 2.x (API v2: `MCPServer`, não `FastMCP`), `claude-agent-sdk` (traz o `claude.exe` embutido), `google-genai` 2.x (laço manual de ferramentas). APIs conferidas no pacote instalado em 28/10/2026.

## Consequências
- Datas sempre com fuso (`UTCDateTime`), porque o SQLite perde o fuso.
- O painel é um app separado que fala só com a API.
