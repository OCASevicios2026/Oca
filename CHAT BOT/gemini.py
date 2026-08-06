"""Cliente de Gemini para el chatbot de OCA (gemini-3.5-flash).

Encapsula toda la comunicacion con la API de Google Gemini:
- Conversacion natural con historial (memoria).
- Analisis de imagenes (fotos, planos, croquis).
- Analisis de notas de voz (el modelo transcribe el audio directamente).
- Lectura de documentos PDF.

Usa el SDK oficial `google-genai`. Se configura con GEMINI_API_KEY y GEMINI_MODEL.
"""

import logging
from functools import lru_cache

from google import genai
from google.genai import types

from config import settings
from prompts import SYSTEM_PROMPT

logger = logging.getLogger("oca-chatbot")


@lru_cache(maxsize=1)
def _client() -> genai.Client:
    """Devuelve el cliente de Gemini (una sola instancia por proceso)."""
    return genai.Client(api_key=settings.gemini_api_key)


def _media_part(media_type: str, media_bytes: bytes):
    """Convierte un archivo multimedia (imagen/audio/pdf) en una parte de Gemini."""
    mime_map = {
        "image": "image/jpeg",
        "audio": "audio/ogg",
        "document": "application/pdf",
    }
    mime = mime_map.get(media_type, "application/octet-stream")
    return types.Part.from_bytes(data=media_bytes, mime_type=mime)


def generate_reply(
    history: list[dict],
    user_text: str,
    media_type: str | None = None,
    media_bytes: bytes | None = None,
) -> str:
    """Genera una respuesta de Gemini.

    Args:
        history: Historial de la conversacion (lista de {"role", "content"}).
        user_text: Mensaje de texto del usuario (puede estar vacio si hay media).
        media_type: "image", "audio" o "document" (opcional).
        media_bytes: Contenido binario del archivo (opcional).

    Returns:
        La respuesta de Gemini como texto, o un mensaje de error controlado.
    """
    try:
        contents = []

        # Historial: roles alternados usuario/modelo
        for turn in history:
            contents.append(
                types.Content(
                    role=turn["role"],
                    parts=[types.Part(text=turn["content"])],
                )
            )

        # Parte actual del usuario: texto + (opcional) media
        parts = []
        if media_type and media_bytes:
            parts.append(_media_part(media_type, media_bytes))
        if user_text.strip():
            parts.append(types.Part(text=user_text))
        elif not parts:
            parts.append(types.Part(text="¿Qué ves en este archivo?"))

        contents.append(types.Content(role="user", parts=parts))

        response = _client().models.generate_content(
            model=settings.gemini_model,
            contents=contents,
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT,
                temperature=0.7,
                max_output_tokens=1024,
            ),
        )
        reply = response.text.strip()
        if not reply:
            return (
                "No logre generar una respuesta. Por favor intenta de nuevo "
                "o escribe *menu* para ver las opciones."
            )
        return reply
    except Exception:
        logger.exception("Error al llamar a Gemini")
        return (
            "En este momento tengo problemas para procesar tu mensaje. "
            "Por favor intenta de nuevo en unos segundos o escribe *menu*."
        )
