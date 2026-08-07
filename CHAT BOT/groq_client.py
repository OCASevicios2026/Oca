"""Cliente de Groq para el chatbot de OCA.

Encapsula toda la comunicacion con la API de Groq:
- Conversacion natural con historial (memoria).
- Analisis de imagenes (fotos, planos, croquis) con un modelo de vision.
- Transcipcion de notas de voz con Whisper.
- Lectura de documentos PDF extrayendo su texto con pypdf.

Se configura con GROQ_API_KEY, GROQ_MODEL, GROQ_VISION_MODEL y GROQ_STT_MODEL.
"""

import base64
import io
import logging
from functools import lru_cache

import pypdf
from groq import Groq

from config import settings
from knowledge import MENU_OPTIONS
from prompts import SYSTEM_PROMPT

logger = logging.getLogger("oca-chatbot")


@lru_cache(maxsize=1)
def _client() -> Groq:
    """Devuelve el cliente de Groq (una sola instancia por proceso)."""
    return Groq(api_key=settings.groq_api_key)


def _run(messages: list[dict], model: str | None = None, temperature: float = 0.7, max_tokens: int = 1024) -> str:
    """Ejecuta un chat completion y devuelve el texto de la respuesta."""
    response = _client().chat.completions.create(
        model=model or settings.groq_model,
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
    )
    return (response.choices[0].message.content or "").strip()


def _build_history(history: list[dict]) -> list[dict]:
    """Convierte el historial interno (roles user/model) al formato de Groq (user/assistant)."""
    messages = []
    for turn in history:
        role = "assistant" if turn["role"] == "model" else "user"
        messages.append({"role": role, "content": turn["content"]})
    return messages


def humanize_service_reply(service_key: str) -> str | None:
    """Reescribe el detalle de un servicio con tono de asesor humano.

    Mantiene un cierre natural invitando a seguir la conversación.
    Devuelve None si Groq falla.
    """
    svc = MENU_OPTIONS.get(service_key)
    if svc is None:
        return None
    data = f"{svc['name']}\n{svc['desc']}\n" + "\n".join(
        f"- {item}" for item in svc["items"]
    )
    try:
        reply = _run(
            [
                {
                    "role": "user",
                    "content": (
                        "Redacta la siguiente informacion de servicio en espanol, con tono "
                        "cercano y profesional de un asesor de WhatsApp, sin inventar datos.\n\n"
                        f"{data}\n\n"
                        "Termina de forma natural, invitando a que pregunte lo que necesite o pida cotizacion si le interesa. "
                        "No uses formatos de menu ni pidas que responda SI/NO. "
                        "Maximo 4-5 lineas. No uses emojis."
                    ),
                }
            ],
            temperature=0.8,
            max_tokens=500,
        )
        return reply or None
    except Exception:
        logger.exception("Error al humanizar servicio %s", service_key)
        return None


def humanize_menu() -> str | None:
    """Lista los servicios en prosa natural (tono de asesor), variando la apertura.

    Evita el formato de menu con numeros y asteriscos para que no parezca
    una respuesta preprogramada. Devuelve None si Groq falla.
    """
    services = ", ".join(svc["name"] for svc in MENU_OPTIONS.values())
    try:
        reply = _run(
            [
                {
                    "role": "user",
                    "content": (
                        "Actua como asesor de OCA Servicios Integrales (Santa Marta, Colombia). "
                        "El cliente pregunto por los servicios que ofrecen. "
                        "VARIA la apertura: no empieces con 'Claro' ni 'Perfecto' ni 'Estos son'; "
                        "usa formas naturales como 'Con gusto te comento', 'Te cuento', "
                        "'Quedo atento, trabajamos en', 'Mira, ofrecemos' u otra variacion. "
                        "Menciona los servicios en una lista natural, en prosa, sin numeros, "
                        "asteriscos ni viñetas: "
                        f"{services}. "
                        "Termina preguntando cual le interesa para ayudarle mejor. "
                        "Maximo 3-4 lineas. No uses emojis."
                    ),
                }
            ],
            temperature=0.9,
            max_tokens=300,
        )
        return (reply or "").strip('"') or None
    except Exception:
        logger.exception("Error al humanizar menu")
        return None


def humanize_greeting(customer_name: str | None, returning: bool = False) -> str | None:
    """Bienvenida natural y variada segun el tipo de cliente.

    - Cliente nuevo (returning=False): presenta los servicios en prosa.
    - Cliente recurrente (returning=True): responde corto, sin repetir la
      lista de servicios ni el saludo completo.
    """
    services = ", ".join(svc["name"] for svc in MENU_OPTIONS.values())
    try:
        if returning:
            instruction = (
                "El cliente ya hablo con nosotros antes. Redacta un mensaje breve, "
                "natural y cordial sin volver a presentar los servicios ni usar "
                "saludos repetidos. Pregunta en que le podemos ayudar ahora. "
                "Maximo 2 lineas. No uses emojis."
            )
        else:
            instruction = (
                "Redacta un mensaje de WhatsApp natural y cercano para un cliente nuevo"
                f"{(', llamandolo por su nombre ' + customer_name) if customer_name else ''}. "
                "VARIA la apertura: no empieces con 'Hola'; usa formas como "
                "'¡Buen dia!', 'Que gusto saludarte', 'Saludos', 'Con gusto te atiendo' "
                "u otra variacion natural en espanol. "
                "Menciona los servicios de la empresa en una lista natural, en prosa, "
                "sin numeros ni asteriscos ni formato de menu: "
                f"{services}. "
                "Termina preguntando cual de esos servicios le interesa. "
                "Maximo 3-4 lineas. No uses emojis ni puntuacion excesiva."
            )
        reply = _run(
            [
                {
                    "role": "user",
                    "content": (
                        f"Actua como asesor de OCA Servicios Integrales (Santa Marta, Colombia). "
                        f"{instruction}"
                    ),
                }
            ],
            temperature=0.9,
            max_tokens=250,
        )
        return (reply or "").strip('"') or None
    except Exception:
        logger.exception("Error al humanizar saludo")
        return None


def _extract_pdf_text(media_bytes: bytes) -> str:
    """Extrae el texto de un PDF usando pypdf."""
    reader = pypdf.PdfReader(io.BytesIO(media_bytes))
    pages = [page.extract_text() or "" for page in reader.pages]
    return "\n".join(pages).strip()


def _transcribe_audio(media_bytes: bytes, mime: str = "") -> str:
    """Transcribe una nota de voz con Whisper de Groq."""
    ext = "mp3" if mime and "mp3" in mime else "ogg" if mime and "ogg" in mime else "mp4"
    mime_type = mime or "audio/ogg"
    response = _client().audio.transcriptions.create(
        model=settings.groq_stt_model,
        file=(f"audio.{ext}", media_bytes, mime_type),
        language="es",
    )
    return (response.text or "").strip()


def _image_part(media_bytes: bytes) -> dict:
    """Convierte una imagen en la parte de contenido que espera el modelo de vision."""
    return {
        "type": "image_url",
        "image_url": {
            "url": "data:image/jpeg;base64," + base64.b64encode(media_bytes).decode()
        },
    }


def _media_reply(user_text: str, media_type: str, media_bytes: bytes, media_mime: str = "") -> str:
    """Genera una respuesta para un mensaje multimedia."""
    if media_type == "audio":
        transcript = _transcribe_audio(media_bytes, media_mime)
        if not transcript:
            return (
                "No pude entender la nota de voz. Intenta de nuevo "
                "o escríbenos tu consulta por texto."
            )
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            *[
                {"role": "user", "content": "Transcripción de la nota de voz del cliente:"},
                {"role": "assistant", "content": "La he escuchado. Dame un momento para responder."},
                {"role": "user", "content": f"Nota de voz: {transcript}\n\nResponde al cliente como asesor de OCA."},
            ],
        ]
        return _run(messages)

    if media_type == "document":
        pdf_text = _extract_pdf_text(media_bytes)
        if not pdf_text:
            return (
                "El PDF no contiene texto legible (puede ser solo imágenes). "
                "Intenta enviarlo como imagen o escríbenos tu consulta por texto."
            )
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": (
                    f"{user_text or '¿Qué dice este documento?'}\n\n"
                    f"Contenido del PDF:\n{pdf_text[:8000]}"
                ),
            },
        ]
        return _run(messages)

    if media_type == "image":
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": [
                    _image_part(media_bytes),
                    {"type": "text", "text": user_text or "¿Qué ves en esta imagen?"},
                ],
            },
        ]
        return _run(messages, model=settings.groq_vision_model)

    return (
        "No logre procesar este archivo. Intenta enviarlo como imagen "
        "o escríbenos tu consulta por texto."
    )


def generate_reply(
    history: list[dict],
    user_text: str,
    media_type: str | None = None,
    media_bytes: bytes | None = None,
    media_mime: str = "",
) -> str:
    """Genera una respuesta de Groq.

    Args:
        history: Historial de la conversacion (lista de {"role", "content"}).
        user_text: Mensaje de texto del usuario (puede estar vacio si hay media).
        media_type: "image", "audio" o "document" (opcional).
        media_bytes: Contenido binario del archivo (opcional).
        media_mime: Tipo MIME del archivo (opcional).

    Returns:
        La respuesta de Groq como texto, o un mensaje de error controlado.
    """
    try:
        if media_type and media_bytes:
            return _media_reply(user_text, media_type, media_bytes, media_mime)

        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            *_build_history(history),
            {"role": "user", "content": user_text or "¿En qué puedo ayudarte?"},
        ]
        reply = _run(messages)
        if not reply:
            return (
                "No logre generar una respuesta. Por favor intenta de nuevo "
                "o cuentame en que te puedo ayudar."
            )
        return reply
    except Exception:
        logger.exception("Error al llamar a Groq")
        return (
            "En este momento tengo problemas para procesar tu mensaje. "
            "Por favor intenta de nuevo en unos segundos o escribe *menu*."
        )
