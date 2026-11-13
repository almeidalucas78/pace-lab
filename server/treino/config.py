from functools import lru_cache
from pathlib import Path
from zoneinfo import ZoneInfo

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


# Raiz do repositório (acima de server/): o .env, a pasta data/ e o painel compilado (web/dist) são
# resolvidos daqui, de qualquer pasta que o comando seja chamado (o Claude Desktop e o agy abrem o MCP
# a partir de outra pasta).
ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=ROOT / ".env", env_file_encoding="utf-8", extra="ignore")

    database_url: str = "sqlite:///./data/treino.db"
    timezone: str = "America/Sao_Paulo"
    fc_max: int | None = None
    fc_repouso: int | None = None
    api_token: str = "troque-este-token"

    notificacoes: bool = True

    # Chat com IA
    ia_provedor: str = "claude"         # claude ou gemini
    claude_modelo: str = "claude-opus-5-5"
    claude_esforco: str = ""            # low, medium, high, xhigh, max (vazio = padrão do modelo)
    gemini_api_key: str = ""            # chave gratuita do Google AI Studio
    gemini_modelo: str = "gemini-3.8-flash"
    gemini_modelo_reserva: str = "gemini-3.6-flash"  # usado se o principal estiver sobrecarregado (503/504)
    gemini_timeout_s: float = 90
    chat_max_turnos: int = 12           # chamadas de ferramenta por resposta

    # Painel no celular (ADR 0012): endereço do `tailscale serve`, usado no QR code do "Conectar celular"
    painel_url_celular: str = ""       # ex.: https://pacelab.nome-da-rede.ts.net
    # App Android (ADR 0013): APK publicado pelo PC com `treino publicar-app`, baixado pelo próprio app
    pasta_app: str = "data/app"

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
    def app_dir(self) -> Path:
        p = Path(self.pasta_app)
        return p if p.is_absolute() else ROOT / p

    @property
    def tz(self) -> ZoneInfo:
        return ZoneInfo(self.timezone)


@lru_cache
def get_settings() -> Settings:
    return Settings()
