from functools import lru_cache
from pathlib import Path
from zoneinfo import ZoneInfo

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


# Raiz do projeto: o .env e o SQLite relativo ficam aqui, de qualquer pasta que o comando seja chamado
# (o Claude Desktop e o agy abrem o MCP a partir de outra pasta).
ROOT = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=ROOT / ".env", env_file_encoding="utf-8", extra="ignore")

    database_url: str = "sqlite:///./data/treino.db"
    timezone: str = "America/Sao_Paulo"
    fc_max: int | None = None
    fc_repouso: int | None = None
    api_token: str = "troque-este-token"

    # Health Connect via app HC Webhook (servidor HTTP local do celular)
    hc_url: str = ""                    # ex.: http://192.168.0.20:8787 (vazio = sincronização desligada)
    hc_token: str = ""                  # token Bearer configurado no app (vazio = sem token)
    hc_timeout_s: float = 60
    sync_intervalo_min: int = 30
    sync_margem_h: int = 48             # relê esse tanto antes da última leitura (o relógio sincroniza com atraso)
    sync_primeira_janela_dias: int = 30 # janela da primeira leitura, quando ainda não há histórico de sincronização
    notificacoes: bool = True

    # Chat com IA
    ia_provedor: str = "claude"         # claude ou gemini
    claude_modelo: str = "claude-opus-5-5"
    claude_esforco: str = ""            # low, medium, high, xhigh, max (vazio = padrão do modelo)
    gemini_api_key: str = ""            # chave gratuita do Google AI Studio
    gemini_modelo: str = "gemini-3.8-flash"
    chat_max_turnos: int = 12           # chamadas de ferramenta por resposta

    @field_validator("fc_max", "fc_repouso", mode="before")
    @classmethod
    def empty_to_none(cls, v):
        return None if v in ("", None) else v

    @property
    def sqlite_url(self) -> str:
        """DATABASE_URL com caminho de SQLite relativo resolvido a partir da raiz do projeto."""
        url = self.database_url
        prefix = "sqlite:///"
        if url.startswith(prefix) and not url.startswith(prefix + ":memory:"):
            path = Path(url.removeprefix(prefix))
            if not path.is_absolute():
                return prefix + (ROOT / path).as_posix()
        return url

    @property
    def tz(self) -> ZoneInfo:
        return ZoneInfo(self.timezone)


@lru_cache
def get_settings() -> Settings:
    return Settings()
