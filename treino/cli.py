"""Comandos de linha: treino --help"""
from __future__ import annotations

import json
from pathlib import Path

import typer

from . import services
from .config import get_settings
from .db import init_db, session_scope
from .ingest.strava_export import import_strava_export

app = typer.Typer(add_completion=False, help="Painel de treinos: importação, métricas e API.")


def _print(obj) -> None:
    typer.echo(json.dumps(obj, ensure_ascii=False, indent=2, default=str))


@app.command()
def init():
    """Cria o banco de dados (seguro rodar de novo)."""
    init_db()
    typer.echo(f"Banco pronto em {get_settings().database_url}")


@app.command("importar-strava")
def importar_strava(
    caminho: Path = typer.Argument(..., help="Pasta descompactada do export do Strava ou o arquivo .zip"),
    sem_arquivos: bool = typer.Option(False, help="Importa só o activities.csv, sem ler os arquivos dos treinos"),
):
    """Importa (ou atualiza) todo o histórico do export do Strava e recalcula as métricas."""
    init_db()
    settings = get_settings()
    with typer.progressbar(length=1, label="Importando") as bar:
        state = {"total": None}

        def progress(n, total):
            if state["total"] is None:
                state["total"] = total
                bar.length = total
            bar.update(1)

        with session_scope() as s:
            rep = import_strava_export(s, caminho, with_streams=not sem_arquivos, progress=progress)
            rep["recalculo"] = services.recompute(s, settings)
    _print(rep)
    rc = rep["recalculo"]
    if rc["fc_max_origem"] == "estimada":
        typer.secho(f"\nAtenção: FC máxima ESTIMADA em {rc['fc_max']:.0f} bpm a partir dos seus treinos. "
                    "Zonas e carga dependem dela; preencha FC_MAX no .env se tiver um valor medido "
                    "e rode `treino recalcular`.", fg=typer.colors.YELLOW)


@app.command()
def recalcular():
    """Recalcula duplicatas, zonas, carga e fitness/fadiga/forma (use após mudar FC_MAX)."""
    with session_scope() as s:
        _print(services.recompute(s, get_settings()))


@app.command()
def resumo(semanas: int = typer.Option(8, help="Quantas semanas mostrar")):
    """Visão geral e volume semanal de corrida."""
    settings = get_settings()
    with session_scope() as s:
        _print(services.overview(s))
        typer.echo("\nCorrida por semana (segunda a domingo):")
        for w in services.weekly_summary(s, settings, weeks=semanas):
            typer.echo(f"  {w['semana']}  {w['treinos']} treino(s)  {w['km']:5.1f} km  "
                       f"ritmo {w['ritmo_medio'] or '-':>9}  maior {w['maior_treino_km']:4.1f} km  carga {w['carga']}")
        load = services.load_series(s, days=1)
        if load:
            d = load[-1]
            typer.echo(f"\nHoje: fitness {d['fitness']}  fadiga {d['fadiga']}  forma {d['forma']}")


@app.command()
def atividades(esporte: str = typer.Option("run", help="run, walk, ride, strength, workout ou 'todos'"),
               limite: int = 10):
    """Lista os treinos mais recentes."""
    with session_scope() as s:
        rows = services.list_activities(s, get_settings(), None if esporte == "todos" else esporte, limite)
    for r in rows:
        typer.echo(f"#{r['id']:<4} {r['data'][:16]}  {r['esporte']:<8} {r['distancia_km'] or 0:6.2f} km  "
                   f"{r['ritmo'] or '':>9}  FC {r['fc_media'] or '-'}  carga {r['carga'] or '-'}  {r['nome'] or ''}")


@app.command()
def atividade(id: int):
    """Detalhe de um treino: parciais por km, zonas e qualidade dos dados."""
    with session_scope() as s:
        d = services.activity_detail(s, get_settings(), id)
    if d is None:
        raise typer.Exit(code=1)
    _print(d)


@app.command()
def fc():
    """Mostra a FC máxima usada nos cálculos e de onde ela veio."""
    with session_scope() as s:
        v, src = services.resolve_fc_max(s, get_settings())
    typer.echo(f"FC máxima: {v} ({src})")


@app.command()
def sincronizar():
    """Puxa agora os treinos do celular (HC Webhook) e mostra o resultado."""
    from .scheduler import run_sync
    settings = get_settings()
    if not settings.hc_url:
        typer.secho("HC_URL vazio no .env: configure o endereço do celular (ex.: http://192.168.0.20:8787).",
                    fg=typer.colors.YELLOW)
        raise typer.Exit(code=1)
    init_db()
    rep = run_sync(settings)
    _print(rep)
    if rep["status"] != "ok":
        raise typer.Exit(code=1)


@app.command("status-sync")
def status_sync():
    """Mostra quando foi a última sincronização com o celular e se deu erro."""
    init_db()
    with session_scope() as s:
        _print(services.sync_status(s, get_settings()))


@app.command()
def chat(provedor: str = typer.Option(None, help="claude ou gemini (padrão: IA_PROVEDOR do .env)"),
         conversa: int = typer.Option(None, help="id de uma conversa para continuar")):
    """Conversa com o treinador (IA) no terminal. Linha vazia ou 'sair' encerra."""
    import asyncio

    from .ia.chat import conversar
    from .ia.provedores import ErroIA
    init_db()
    while True:
        try:
            msg = input("\nvocê> ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if msg.lower() in ("", "sair"):
            break
        try:
            r = asyncio.run(conversar(msg, conversa, provedor))
        except ErroIA as e:
            typer.secho(f"Erro: {e}", fg=typer.colors.RED)
            continue
        conversa = r["conversa_id"]
        if r["ferramentas"]:
            typer.secho(f"[{r['provedor']} consultou: {', '.join(r['ferramentas'])}]", dim=True)
        typer.echo(f"\ntreinador> {r['resposta']}")
    if conversa:
        typer.echo(f"\nConversa {conversa} salva. Para continuar: treino chat --conversa {conversa}")


@app.command()
def mcp(http: bool = typer.Option(False, help="Serve por HTTP em vez de stdio"),
        porta: int = typer.Option(8001, help="Porta do modo HTTP")):
    """Servidor MCP com as ferramentas de treino (Claude Desktop, Claude Code, agy)."""
    import logging

    from .ia.mcp_server import criar_servidor
    logging.basicConfig(level=logging.WARNING)  # stdio: nada pode ir para o stdout além do protocolo
    init_db()
    servidor = criar_servidor()
    if http:
        servidor.run(transport="streamable-http", host="127.0.0.1", port=porta)
    else:
        servidor.run()


def _serve(host: str, porta: int, agendador: bool) -> None:
    import logging
    import os

    import uvicorn
    from .api.app import SCHEDULER_ENV
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s", datefmt="%H:%M:%S")
    for noisy in ("alembic", "httpx"):
        logging.getLogger(noisy).setLevel(logging.WARNING)
    init_db()
    os.environ[SCHEDULER_ENV] = "1" if agendador else "0"
    uvicorn.run("treino.api.app:app", host=host, port=porta)


@app.command()
def api(host: str = "127.0.0.1", porta: int = 8000):
    """Sobe a API local sem sincronização automática."""
    _serve(host, porta, agendador=False)


@app.command()
def servico(host: str = "127.0.0.1", porta: int = 8000):
    """Sobe a API com a sincronização automática do celular (deixe a janela aberta)."""
    _serve(host, porta, agendador=True)


if __name__ == "__main__":
    app()
