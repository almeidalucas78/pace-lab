"""Provedores de IA intercambiáveis. Todos recebem a mensagem e devolvem Resposta; as ferramentas são as do REGISTRO."""

from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass, field
from typing import Protocol

from ..config import ROOT, Settings
from .ferramentas import REGISTRO, executar
from .prompt import SISTEMA, com_data


class ErroIA(Exception):
    """Falha do provedor (login, cota, rede). A mensagem vai para o usuário."""


@dataclass
class Resposta:
    texto: str
    ferramentas: list[str] = field(default_factory=list)
    sessao: str | None = None  # id de sessão do provedor, quando ele guarda o contexto (Claude)
    meta: dict = field(default_factory=dict)


class Provedor(Protocol):
    nome: str

    async def responder(self, mensagem: str, historico: list[tuple[str, str]], sessao: str | None) -> Resposta: ...


def _texto_resultado(res) -> str:
    return json.dumps(res, ensure_ascii=False, default=str)


# ---------- Claude (Claude Agent SDK) ----------

SERVIDOR_MCP = "treino"


class Claude:
    """Usa o Claude Code embutido no claude-agent-sdk, com as ferramentas num servidor MCP dentro do processo.
    Sem ANTHROPIC_API_KEY no ambiente, o Claude Code usa o login que já existe neste PC.
    O contexto da conversa fica na sessão do próprio Claude Code (retomada pelo id)."""

    nome = "claude"

    def __init__(self, settings: Settings):
        self.settings = settings

    def _servidor(self):
        from claude_agent_sdk import ToolAnnotations, create_sdk_mcp_server, tool

        tools = []
        for f in REGISTRO:

            async def handler(args, nome=f.nome):
                res = await asyncio.to_thread(executar, nome, args)
                out = {"content": [{"type": "text", "text": _texto_resultado(res)}]}
                if isinstance(res, dict) and "erro" in res:
                    out["is_error"] = True
                return out

            tools.append(
                tool(f.nome, f.descricao, f.schema, annotations=ToolAnnotations(readOnlyHint=f.somente_leitura))(
                    handler
                )
            )
        return create_sdk_mcp_server(SERVIDOR_MCP, tools=tools)

    async def responder(self, mensagem, historico, sessao):
        from claude_agent_sdk import (
            AssistantMessage,
            ClaudeAgentOptions,
            ClaudeSDKError,
            ResultMessage,
            ToolUseBlock,
            query,
        )

        cwd = ROOT / "data" / "chat-claude"  # sessões do Claude Code ficam associadas a esta pasta
        cwd.mkdir(parents=True, exist_ok=True)
        options = ClaudeAgentOptions(
            system_prompt=SISTEMA,
            model=self.settings.claude_modelo or None,
            effort=self.settings.claude_esforco or None,
            tools=[],  # nada de ler arquivos ou rodar comandos: só as nossas ferramentas
            mcp_servers={SERVIDOR_MCP: self._servidor()},
            allowed_tools=[f"mcp__{SERVIDOR_MCP}__{f.nome}" for f in REGISTRO],
            permission_mode="dontAsk",
            setting_sources=[],  # não carrega CLAUDE.md, skills nem configurações do usuário
            cwd=str(cwd),
            resume=sessao,
            max_turns=self.settings.chat_max_turnos,
        )
        usadas, resultado = [], None
        try:
            async for msg in query(prompt=com_data(mensagem, self.settings), options=options):
                if isinstance(msg, AssistantMessage):
                    usadas += [
                        b.name.removeprefix(f"mcp__{SERVIDOR_MCP}__")
                        for b in msg.content
                        if isinstance(b, ToolUseBlock)
                    ]
                elif isinstance(msg, ResultMessage):
                    resultado = msg
        except ClaudeSDKError as e:
            raise ErroIA(f"Claude: {e}") from e
        if resultado is None:
            raise ErroIA("Claude não devolveu resposta")
        if resultado.is_error or resultado.subtype != "success":
            raise ErroIA(f"Claude: {resultado.subtype} {resultado.result or resultado.errors or ''}".strip())
        return Resposta(
            texto=resultado.result or "",
            ferramentas=usadas,
            sessao=resultado.session_id,
            meta={
                "modelo": self.settings.claude_modelo,
                "turnos": resultado.num_turns,
                "custo_estimado_usd": resultado.total_cost_usd,
                "uso": resultado.usage,
            },
        )


# ---------- Gemini (google-genai, chave do AI Studio) ----------

SOBRECARGA = {500, 503, 504}  # erros do lado do Google em que vale tentar o modelo de reserva


class Gemini:
    """Gemini com laço manual de ferramentas. O histórico vem do nosso banco a cada mensagem."""

    nome = "gemini"

    def __init__(self, settings: Settings, client=None):
        self.settings = settings
        if client is None:
            if not settings.gemini_api_key:
                raise ErroIA(
                    "GEMINI_API_KEY vazio no .env (crie a chave gratuita em https://aistudio.google.com/apikey)"
                )
            from google import genai
            from google.genai import types

            client = genai.Client(
                api_key=settings.gemini_api_key,
                http_options=types.HttpOptions(timeout=int(settings.gemini_timeout_s * 1000)),
            )
        self.client = client

    def _config(self):
        from google.genai import types

        return types.GenerateContentConfig(
            system_instruction=SISTEMA,
            tools=[
                types.Tool(
                    function_declarations=[
                        types.FunctionDeclaration(name=f.nome, description=f.descricao, parameters_json_schema=f.schema)
                        for f in REGISTRO
                    ]
                )
            ],
            automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
        )

    async def responder(self, mensagem, historico, sessao):
        from google.genai import errors

        principal, reserva = self.settings.gemini_modelo, self.settings.gemini_modelo_reserva
        usadas: list[str] = []
        try:
            return await self._rodar(principal, mensagem, historico, usadas)
        except errors.APIError as e:
            # Sobrecarga do modelo principal: tenta o de reserva, mas só se nenhuma ferramenta rodou
            # (repetir a resposta depois de um salvar_plano gravaria duas vezes).
            if usadas or e.code not in SOBRECARGA or not reserva or reserva == principal:
                raise ErroIA(f"Gemini: {e.code} {e.message}") from e
            try:
                return await self._rodar(reserva, mensagem, historico, usadas, aviso=f"{principal}: {e.code}")
            except errors.APIError as e2:
                raise ErroIA(f"Gemini: {e2.code} {e2.message} (modelo principal: {e.code})") from e2

    async def _rodar(self, modelo, mensagem, historico, usadas, aviso=None):
        from google.genai import types

        contents = [
            types.Content(role="user" if papel == "user" else "model", parts=[types.Part(text=texto)])
            for papel, texto in historico
        ]
        contents.append(types.Content(role="user", parts=[types.Part(text=com_data(mensagem, self.settings))]))
        config = self._config()
        for _ in range(self.settings.chat_max_turnos):
            resp = await self.client.aio.models.generate_content(model=modelo, contents=contents, config=config)
            chamadas = resp.function_calls or []
            if not chamadas:
                meta = {
                    "modelo": modelo,
                    "uso": resp.usage_metadata.model_dump(exclude_none=True) if resp.usage_metadata else None,
                }
                if aviso:
                    meta["reserva_por"] = aviso
                return Resposta(texto=resp.text or "", ferramentas=usadas, meta=meta)
            # devolve o conteúdo do modelo inteiro (inclui as assinaturas de raciocínio do Gemini 3)
            contents.append(resp.candidates[0].content)
            partes = []
            for fc in chamadas:
                usadas.append(fc.name)
                res = await asyncio.to_thread(executar, fc.name, dict(fc.args or {}))
                parte = types.Part.from_function_response(name=fc.name, response={"resultado": res})
                if fc.id:
                    parte.function_response.id = fc.id
                partes.append(parte)
            contents.append(types.Content(role="user", parts=partes))
        raise ErroIA("limite de chamadas de ferramenta atingido nesta resposta")


def criar_provedor(nome: str, settings: Settings) -> Provedor:
    if nome == "claude":
        return Claude(settings)
    if nome == "gemini":
        return Gemini(settings)
    raise ErroIA(f"provedor desconhecido: {nome} (use claude ou gemini)")
