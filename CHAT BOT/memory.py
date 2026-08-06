"""Memoria de conversacion por usuario.

Reutiliza las tablas existentes en PostgreSQL (`conversations` y `messages`)
para construir el historial que se envia a Gemini. Cada usuario (numero de
WhatsApp) tiene su propia conversacion y, por tanto, su propio historial.
"""

from sqlalchemy import select

from database import SessionLocal
from models import Message

# Maximo de mensajes (entrantes + salientes) que se envian a Gemini como contexto
MAX_HISTORY_MESSAGES = 20


def get_recent_messages(conversation_id: int, limit: int = MAX_HISTORY_MESSAGES) -> list[Message]:
    """Devuelve los ultimos mensajes de una conversacion en orden cronologico."""
    with SessionLocal() as db:
        rows = db.execute(
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.id.desc())
            .limit(limit)
        ).scalars().all()
        return list(reversed(rows))


def build_chat_history(conversation_id: int) -> list[dict]:
    """Construye el historial en el formato esperado por Gemini.

    Devuelve una lista de {"role": "user"|"model", "content": str}.
    El ultimo mensaje (el entrante en curso) se excluye para no duplicar la
    pregunta actual; main.py lo agrega por separado.
    """
    messages = get_recent_messages(conversation_id)
    history = []
    for msg in messages:
        role = "user" if msg.direction == "in" else "model"
        history.append({"role": role, "content": msg.content})
    return history
