from datetime import datetime, timezone

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from database import Base

# PK compatible con PostgreSQL (BIGINT identity) y SQLite (INTEGER rowid)
_id_type = BigInteger().with_variant(Integer, "sqlite")


def utcnow():
    return datetime.now(timezone.utc)


class Conversation(Base):
    __tablename__ = "conversations"

    id: Mapped[int] = mapped_column(_id_type, primary_key=True, autoincrement=True)
    whatsapp_phone: Mapped[str] = mapped_column(String(20), unique=True, index=True, nullable=False)
    customer_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    state: Mapped[str] = mapped_column(String(60), default="menu", nullable=False)
    pending_service: Mapped[str | None] = mapped_column(String(120), nullable=True)
    paused: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(_id_type, primary_key=True, autoincrement=True)
    conversation_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("conversations.id"), index=True, nullable=False
    )
    direction: Mapped[str] = mapped_column(String(10), nullable=False)  # "in" | "out"
    content: Mapped[str] = mapped_column(Text, nullable=False)
    wamid: Mapped[str | None] = mapped_column(String(128), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Setting(Base):
    """Almacenamiento clave-valor para ajustes del bot (p. ej. estado on/off/pausa)."""

    __tablename__ = "settings"

    key: Mapped[str] = mapped_column(String(60), primary_key=True)
    value: Mapped[str] = mapped_column(String(255), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )


class Lead(Base):
    __tablename__ = "leads"

    id: Mapped[int] = mapped_column(_id_type, primary_key=True, autoincrement=True)
    conversation_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("conversations.id"), index=True, nullable=True
    )
    whatsapp_phone: Mapped[str] = mapped_column(String(20), index=True, nullable=False)
    customer_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    service: Mapped[str | None] = mapped_column(String(120), nullable=True)
    message: Mapped[str | None] = mapped_column(Text, nullable=True)
    notified: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    # Origen: "whatsapp" (bot) o "web" (formulario de la pagina)
    source: Mapped[str] = mapped_column(String(20), default="whatsapp", nullable=False)
    # Estado: "nuevo" | "contactado" (para el panel administrativo)
    status: Mapped[str] = mapped_column(String(20), default="nuevo", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
