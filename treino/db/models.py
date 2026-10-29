"""Modelos do banco. Funcionam igual em SQLite (PC) e Postgres (hospedado)."""
from datetime import date, datetime, timezone

from sqlalchemy import JSON, Date, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.types import TypeDecorator


class UTCDateTime(TypeDecorator):
    """Grava sempre em UTC e devolve com fuso, inclusive no SQLite (que perde o fuso)."""
    impl = DateTime(timezone=True)
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is not None:
            if value.tzinfo is None:
                raise ValueError("datetime sem fuso horário")
            value = value.astimezone(timezone.utc)
            if dialect.name == "sqlite":
                value = value.replace(tzinfo=None)
        return value

    def process_result_value(self, value, dialect):
        if value is not None and value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value


class Base(DeclarativeBase):
    pass


class Activity(Base):
    __tablename__ = "activities"
    __table_args__ = (UniqueConstraint("source", "source_id", name="uq_activity_source"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    source: Mapped[str] = mapped_column(String(20))              # strava, health_connect...
    source_id: Mapped[str] = mapped_column(String(64))
    sport: Mapped[str] = mapped_column(String(20), index=True)   # run, walk, ride, strength, workout, other
    sport_raw: Mapped[str | None] = mapped_column(String(60))
    name: Mapped[str | None] = mapped_column(String(200))
    description: Mapped[str | None] = mapped_column(Text)
    start_utc: Mapped[datetime] = mapped_column(UTCDateTime, index=True)

    # Totais (fonte de verdade: resumo da plataforma; streams só complementam)
    elapsed_s: Mapped[float | None] = mapped_column(Float)
    moving_s: Mapped[float | None] = mapped_column(Float)
    distance_m: Mapped[float | None] = mapped_column(Float)
    elev_gain_m: Mapped[float | None] = mapped_column(Float)
    avg_hr: Mapped[float | None] = mapped_column(Float)
    max_hr: Mapped[float | None] = mapped_column(Float)
    avg_cadence_spm: Mapped[float | None] = mapped_column(Float)  # passos/min, as duas pernas
    calories: Mapped[float | None] = mapped_column(Float)
    rpe: Mapped[float | None] = mapped_column(Float)              # percepção de esforço (1 a 10)
    gear: Mapped[str | None] = mapped_column(String(120))
    temp_c: Mapped[float | None] = mapped_column(Float)
    humidity: Mapped[float | None] = mapped_column(Float)         # 0 a 1

    # Arquivo de origem e qualidade
    file_path: Mapped[str | None] = mapped_column(String(300))
    file_status: Mapped[str] = mapped_column(String(20), default="sem_arquivo")  # ok, ausente, erro, sem_arquivo, nao_suportado
    file_error: Mapped[str | None] = mapped_column(Text)
    hr_quality: Mapped[str] = mapped_column(String(30), default="sem_fc")       # ok, suspeita, suspeita_cadencia, sem_fc
    hr_suspect_pct: Mapped[float | None] = mapped_column(Float)

    # Métricas calculadas
    hr_zones_s: Mapped[dict | None] = mapped_column(JSON)         # {"z1": seg, ...}
    trimp: Mapped[float | None] = mapped_column(Float)
    trimp_method: Mapped[str | None] = mapped_column(String(30))  # streams, media_csv
    possible_duplicate_of: Mapped[int | None] = mapped_column(ForeignKey("activities.id", ondelete="SET NULL"))
    extra: Mapped[dict | None] = mapped_column(JSON)              # detalhes brutos (ex.: musculação)

    samples: Mapped[list["Sample"]] = relationship(back_populates="activity", cascade="all, delete-orphan",
                                                   order_by="Sample.t_s")
    splits: Mapped[list["Split"]] = relationship(back_populates="activity", cascade="all, delete-orphan",
                                                 order_by="Split.km")


class Sample(Base):
    """Uma leitura ao longo do treino (normalmente 1 por segundo)."""
    __tablename__ = "samples"

    id: Mapped[int] = mapped_column(primary_key=True)
    activity_id: Mapped[int] = mapped_column(ForeignKey("activities.id", ondelete="CASCADE"), index=True)
    t_s: Mapped[float] = mapped_column(Float)          # segundos desde o início
    lat: Mapped[float | None] = mapped_column(Float)
    lon: Mapped[float | None] = mapped_column(Float)
    ele_m: Mapped[float | None] = mapped_column(Float)
    hr: Mapped[float | None] = mapped_column(Float)    # já filtrada (leituras suspeitas viram NULL)
    hr_raw: Mapped[float | None] = mapped_column(Float)
    cadence_spm: Mapped[float | None] = mapped_column(Float)
    speed_ms: Mapped[float | None] = mapped_column(Float)
    dist_m: Mapped[float | None] = mapped_column(Float)  # distância acumulada

    activity: Mapped[Activity] = relationship(back_populates="samples")


class Split(Base):
    __tablename__ = "splits"

    id: Mapped[int] = mapped_column(primary_key=True)
    activity_id: Mapped[int] = mapped_column(ForeignKey("activities.id", ondelete="CASCADE"), index=True)
    km: Mapped[int] = mapped_column(Integer)
    distance_m: Mapped[float] = mapped_column(Float)
    moving_s: Mapped[float] = mapped_column(Float)
    pace_s_km: Mapped[float | None] = mapped_column(Float)
    avg_hr: Mapped[float | None] = mapped_column(Float)
    elev_delta_m: Mapped[float | None] = mapped_column(Float)

    activity: Mapped[Activity] = relationship(back_populates="splits")


class SyncState(Base):
    """Situação da sincronização de cada fonte automática (hoje só o Health Connect)."""
    __tablename__ = "sync_state"

    source: Mapped[str] = mapped_column(String(30), primary_key=True)
    last_success_utc: Mapped[datetime | None] = mapped_column(UTCDateTime)  # fim da última janela lida com sucesso
    last_attempt_utc: Mapped[datetime | None] = mapped_column(UTCDateTime)
    last_error: Mapped[str | None] = mapped_column(Text)
    last_result: Mapped[dict | None] = mapped_column(JSON)


class Sensation(Base):
    """Como o usuário se sentiu (registrado pelo chat): cansaço, dor, sono, percepção de esforço."""
    __tablename__ = "sensations"

    id: Mapped[int] = mapped_column(primary_key=True)
    created_utc: Mapped[datetime] = mapped_column(UTCDateTime)
    day: Mapped[date] = mapped_column(Date, index=True)            # dia a que a sensação se refere (fuso local)
    activity_id: Mapped[int | None] = mapped_column(ForeignKey("activities.id", ondelete="SET NULL"))
    rpe: Mapped[float | None] = mapped_column(Float)              # percepção de esforço (1 a 10)
    text: Mapped[str] = mapped_column(Text)
    tags: Mapped[list | None] = mapped_column(JSON)               # ex.: ["dor_joelho", "sono_ruim"]


class Conversation(Base):
    __tablename__ = "conversations"

    id: Mapped[int] = mapped_column(primary_key=True)
    created_utc: Mapped[datetime] = mapped_column(UTCDateTime)
    updated_utc: Mapped[datetime] = mapped_column(UTCDateTime, index=True)
    provider: Mapped[str] = mapped_column(String(20))             # claude, gemini
    title: Mapped[str | None] = mapped_column(String(200))
    provider_session_id: Mapped[str | None] = mapped_column(String(100))  # sessão do Claude Agent SDK

    messages: Mapped[list["ChatMessage"]] = relationship(back_populates="conversation", cascade="all, delete-orphan",
                                                         order_by="ChatMessage.id")


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id: Mapped[int] = mapped_column(primary_key=True)
    conversation_id: Mapped[int] = mapped_column(ForeignKey("conversations.id", ondelete="CASCADE"), index=True)
    created_utc: Mapped[datetime] = mapped_column(UTCDateTime)
    role: Mapped[str] = mapped_column(String(20))                 # user, assistant
    content: Mapped[str] = mapped_column(Text)
    meta: Mapped[dict | None] = mapped_column(JSON)               # ferramentas usadas, modelo, uso de tokens

    conversation: Mapped[Conversation] = relationship(back_populates="messages")


class DailyLoad(Base):
    __tablename__ = "daily_load"

    day: Mapped[date] = mapped_column(Date, primary_key=True)
    trimp: Mapped[float] = mapped_column(Float, default=0.0)
    fitness: Mapped[float] = mapped_column(Float)   # CTL, média exponencial 42 dias
    fatigue: Mapped[float] = mapped_column(Float)   # ATL, média exponencial 7 dias
    form: Mapped[float] = mapped_column(Float)      # TSB = fitness - fadiga do dia anterior
