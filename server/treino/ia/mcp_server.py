"""Servidor MCP com as ferramentas de treino, para Claude Desktop, Claude Code e Antigravity CLI (agy).

stdio (padrão): o cliente abre o processo `treino mcp`.
HTTP: `treino mcp --http` serve em http://127.0.0.1:8001/mcp (só nesta máquina; sem autenticação ainda).
"""

from __future__ import annotations

from mcp.server import MCPServer
from mcp_types import ToolAnnotations

from .ferramentas import REGISTRO
from .prompt import INSTRUCOES_MCP


def criar_servidor() -> MCPServer:
    mcp = MCPServer("treino", instructions=INSTRUCOES_MCP)
    for f in REGISTRO:
        mcp.add_tool(
            f.funcao,
            name=f.nome,
            description=f.descricao,
            annotations=ToolAnnotations(read_only_hint=f.somente_leitura),
        )
    return mcp
