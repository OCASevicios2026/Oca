"""Control del estado del bot desde el panel de administrador.

Permite apagar/pausar el bot de forma global o pausar chats individuales
(por numero de WhatsApp). El estado global se guarda en la tabla ``settings``
y la pausa por chat en ``conversations.paused``.
"""

from sqlalchemy import select

from models import Conversation, Setting

# Estados globales validos del bot
STATUS_ON = "on"          # responde normalmente
STATUS_PAUSED = "paused"  # no responde, registra lead
STATUS_OFF = "off"        # no responde, registra lead
VALID_STATUS = (STATUS_ON, STATUS_PAUSED, STATUS_OFF)
DEFAULT_STATUS = STATUS_ON

# Clave en la tabla settings para el estado global
SETTINGS_KEY_BOT_STATUS = "bot_status"


def get_bot_status(db) -> str:
    """Devuelve el estado global del bot (on | paused | off)."""
    row = db.get(Setting, SETTINGS_KEY_BOT_STATUS)
    value = row.value if row else DEFAULT_STATUS
    return value if value in VALID_STATUS else DEFAULT_STATUS


def set_bot_status(db, status: str) -> str:
    """Guarda el estado global del bot."""
    status = status if status in VALID_STATUS else DEFAULT_STATUS
    row = db.get(Setting, SETTINGS_KEY_BOT_STATUS)
    if row is None:
        row = Setting(key=SETTINGS_KEY_BOT_STATUS, value=status)
        db.add(row)
    else:
        row.value = status
    db.commit()
    return status


def is_chat_paused(db, whatsapp_phone: str) -> bool:
    """Devuelve True si un chat especifico esta pausado."""
    conv = db.execute(
        select(Conversation).where(Conversation.whatsapp_phone == whatsapp_phone)
    ).scalar_one_or_none()
    return bool(conv and conv.paused)


def set_chat_paused(db, whatsapp_phone: str, paused: bool) -> bool:
    """Pausa/reanuda un chat especifico. Devuelve el nuevo estado."""
    conv = db.execute(
        select(Conversation).where(Conversation.whatsapp_phone == whatsapp_phone)
    ).scalar_one_or_none()
    if conv is None:
        conv = Conversation(whatsapp_phone=whatsapp_phone)
        db.add(conv)
        db.flush()
    conv.paused = paused
    db.commit()
    return conv.paused


def should_respond(db, whatsapp_phone: str) -> tuple[bool, str | None]:
    """Decide si el bot debe responder a un chat.

    Devuelve (responder, motivo). ``motivo`` es "global" o "chat" cuando NO
    debe responder.
    """
    status = get_bot_status(db)
    if status != STATUS_ON:
        return False, "global"
    if is_chat_paused(db, whatsapp_phone):
        return False, "chat"
    return True, None
