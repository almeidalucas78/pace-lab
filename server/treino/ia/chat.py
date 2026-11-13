"""Uma troca de mensagens no chat: carrega a conversa, chama o provedor e grava pergunta e resposta."""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime

from .. import services
from ..config import Settings, get_settings
from ..db import Conversation, session_scope
from .provedores import ErroIA, Provedor, criar_provedor


async def conversar(
    mensagem: str,
    conversa_id: int | None = None,
    provedor: str | None = None,
    settings: Settings | None = None,
    fabrica: Callable[[str, Settings], Provedor] | None = None,
    contexto: str | None = None,
) -> dict:
    """`contexto` (ex.: "o usuário está vendo o treino #356") vai para a IA, mas não fica gravado na conversa."""
    settings = settings or get_settings()
    fabrica = fabrica or criar_provedor
    mensagem = mensagem.strip()
    if not mensagem:
        raise ErroIA("mensagem vazia")
    with session_scope() as s:
        if conversa_id is not None:
            c = s.get(Conversation, conversa_id)
            if c is None:
                raise ErroIA(f"conversa {conversa_id} não existe")
            if provedor and provedor != c.provider:
                raise ErroIA(f"a conversa {conversa_id} é com {c.provider}; para usar {provedor}, comece outra")
            nome, sessao = c.provider, c.provider_session_id
            historico = services.chat_history(s, c.id)
        else:
            nome, sessao, historico = provedor or settings.ia_provedor, None, []
            conversa_id = services.create_conversation(s, nome, title=mensagem[:80]).id

    inicio = datetime.now(UTC)
    para_ia = f"[Contexto do painel: {contexto.strip()}]\n\n{mensagem}" if contexto and contexto.strip() else mensagem
    resposta = await fabrica(nome, settings).responder(para_ia, historico, sessao)

    with session_scope() as s:
        c = s.get(Conversation, conversa_id)
        services.add_chat_message(s, c, "user", mensagem)
        services.add_chat_message(
            s, c, "assistant", resposta.texto, {"ferramentas": resposta.ferramentas, **resposta.meta}
        )
        if resposta.sessao:
            c.provider_session_id = resposta.sessao
        services.link_plans_to_conversation(s, conversa_id, inicio)
    return {
        "conversa_id": conversa_id,
        "provedor": nome,
        "resposta": resposta.texto,
        "ferramentas": resposta.ferramentas,
    }
