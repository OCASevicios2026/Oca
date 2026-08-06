"""Logica de conversacion del chatbot de OCA Servicios Integrales.

Combina el flujo por reglas (menu, cotizaciones y leads) con la IA de Gemini
para conversaciones naturales y mensajes multimedia.
"""

import re
import unicodedata

from config import settings
from knowledge import BUSINESS_INFO, MENU_OPTIONS

# Respuesta generica cuando las reglas no reconocen el mensaje.
# main.py detecta esta respuesta para delegar la conversacion a Gemini.
FALLBACK_REPLY = (
    "No estoy seguro de haber entendido, pero con gusto te ayudo. "
    "Escribe *menu* para ver nuestros servicios o dime qué necesitas y te guío."
)


def build_menu() -> str:
    lines = [
        "Hola, soy el asistente de *OCA Servicios Integrales*.",
        "",
        "Ofrecemos soluciones en ingeniería civil y climatización en Santa Marta y el Caribe.",
        "",
        "Estos son los servicios que podemos atender:",
        "",
    ]
    for key, svc in MENU_OPTIONS.items():
        lines.append(f"{key}. {svc['name']}")
    lines.extend(
        [
            "",
            "0. Hablar con un asesor",
            "",
            "Puedes escribir el número del servicio o simplemente decir el nombre del servicio que buscas.",
        ]
    )
    return "\n".join(lines)


def service_detail(key: str) -> str:
    svc = MENU_OPTIONS[key]
    lines = [f"*{svc['name']}*", "", svc["desc"], ""]
    lines.extend(f"- {item}" for item in svc["items"])
    lines.extend(
        [
            "",
            "Si quieres, puedo pedirle a un asesor que te prepare una cotización para este servicio.",
            "Responde *SI* o *NO*.",
        ]
    )
    return "\n".join(lines)

def normalize(text: str) -> str:
    text = unicodedata.normalize("NFD", text.lower().strip())
    text = "".join(c for c in text if unicodedata.category(c) != "Mn")
    return text


def _has_any(text: str, words: tuple[str, ...]) -> bool:
    return any(word in text for word in words)


INTENT_HI = ("hola", "buenas", "buenos dias", "buenas tardes", "buenas noches", "hi", "hello")
INTENT_MENU = ("menu", "opciones", "catalogo", "servicios", "que hacen", "que ofrecen", "ayuda")
INTENT_CONTACT = ("contacto", "telefono", "whatsapp", "direccion", "ubicacion", "donde", "nit", "correo")
INTENT_HOURS = ("horario", "horas", "atienden", "cuando atienden")
INTENT_QUOTE = ("cotizar", "cotizacion", "presupuesto", "precio", "tarifa", "costo", "cuanto cuesta")
INTENT_HUMAN = ("asesor", "persona", "humano", "agente", "hablar con alguien", "un tecnico", "atencio")
INTENT_YES = ("si", "sip", "claro", "perfecto", "dale", "ok", "bueno", "sale", "confirmar")
INTENT_NO = ("no", "nop", "no gracias", "ahora no", "despues")
INTENT_THANKS = ("gracias", "muchas gracias", "genial", "excelente", "vale", "ok perfecto")
INTENT_CANCEL = ("cancelar", "cancelacion", "dejarlo", "salir", "empezar de nuevo", "olvidalo", "deja asi")


def _extract_service_key(text: str) -> str | None:
    """Intenta adivinar el servicio por texto libre (ej: 'quiero cotizar el A/C')."""
    text = normalize(text)
    for key, svc in MENU_OPTIONS.items():
        name = normalize(svc["name"])
        if name in text:
            return key
    aliases = {
        "1": ("consultor", "diseno", "viabilidad"),
        "2": ("metalica", "metal", "soldadura", "acero", "estructura"),
        "3": ("urbanismo", "alcantarillado", "manjol", "aguas lluvias", "red de urbanismo"),
        "4": ("hidraulica", "sanitarias", "macromedidor", "micromedidor", "aguas"),
        "5": ("incendio", "incendios", "hidrante", "rociador", "bombeo"),
        "6": ("via", "vias", "pavimento", "adoquin", "concreto"),
        "7": ("impermeab", "filtracion", "humedad", "cubierta", "sellado"),
        "8": ("acabado", "mamposteria", "estuco", "pintura", "muros", "panete", "fachada"),
        "9": ("aire", " ac ", "clima", "acondicionado", "minisplit"),
    }
    for key, words in aliases.items():
        if _has_any(text, words):
            return key
    return None


def handle_inbound(text: str, state: str, customer_name: str | None) -> dict:
    """Devuelve {replies, state, customer_name, lead} segun el estado actual."""
    normalized = normalize(text)

    # --- Comandos de escape: permiten salir de los flujos de captura ---
    # Si el usuario esta en medio de una cotizacion (pide nombre o detalles)
    # y escribe un comando general, se cancela la captura y se vuelve al menu.
    if state in ("awaiting_name", "awaiting_details"):
        if (
            _has_any(normalized, INTENT_CANCEL)
            or _has_any(normalized, INTENT_MENU)
            or _has_any(normalized, INTENT_HI)
            or normalized in ("0", "menu")
        ):
            return {
                "replies": ["Entendido. ¿En que mas puedo ayudarte?\n\n" + build_menu()],
                "state": "menu",
                "customer_name": customer_name,
                "lead": None,
            }

    # --- Estados de captura de datos ---
    if state == "awaiting_name":
        name = text.strip()
        return {
            "replies": [
                f"Gracias, {name}. Cuéntanos brevemente tu proyecto o necesidad para pasársela al asesor (por ejemplo, el tipo de servicio, el lugar y el alcance)."
            ],
            "state": "awaiting_details",
            "customer_name": name,
            "lead": None,
        }

    if state == "awaiting_details":
        return {
            "replies": [
                "¡Perfecto! Hemos registrado tu solicitud. Un asesor de OCA te contactará muy pronto por este mismo canal.",
            ],
            "state": "menu",
            "customer_name": customer_name,
            "lead": {"message": text},
        }

    # --- Estado dentro de un servicio: espera SI/NO ---
    if state.startswith("service:"):
        if _has_any(normalized, INTENT_YES):
            return {
                "replies": ["Perfecto. ¿Cuál es tu nombre?"],
                "state": "awaiting_name",
                "customer_name": customer_name,
                "lead": {"service": MENU_OPTIONS[state.split(":")[1]]["name"]},
            }
        if _has_any(normalized, INTENT_NO):
            return {
                "replies": ["Sin problema. ¿En qué más puedo ayudarte?"],
                "state": "menu",
                "customer_name": customer_name,
                "lead": None,
            }

    # --- Comandos generales ---
    if _has_any(normalized, INTENT_HUMAN):
        if customer_name:
            return {
                "replies": ["Te pongo en contacto con un asesor. ¿Cuál es tu nombre?"],
                "state": "awaiting_name",
                "customer_name": customer_name,
                "lead": None,
            }
        return {
            "replies": ["Con gusto. Un asesor te atenderá. ¿Cuál es tu nombre?"],
            "state": "awaiting_name",
            "customer_name": customer_name,
            "lead": None,
        }

    if _has_any(normalized, INTENT_HI):
        return {
            "replies": ["¡Hola! Bienvenido a OCA Servicios Integrales.\n\n" + build_menu()],
            "state": "menu",
            "customer_name": customer_name,
            "lead": None,
        }

    if _has_any(normalized, INTENT_MENU):
        return {
            "replies": [build_menu()],
            "state": "menu",
            "customer_name": customer_name,
            "lead": None,
        }

    if _has_any(normalized, INTENT_CONTACT):
        return {
            "replies": [BUSINESS_INFO],
            "state": state,
            "customer_name": customer_name,
            "lead": None,
        }

    if _has_any(normalized, INTENT_HOURS):
        return {
            "replies": [
                "*Horario de atencion:* Lunes a Sabado, 7:00 am a 6:00 pm.\n"
                "Para urgencias de mantenimiento de aires acondicionados contamos con atencion 24/7."
            ],
            "state": state,
            "customer_name": customer_name,
            "lead": None,
        }

    if _has_any(normalized, INTENT_QUOTE):
        service_key = _extract_service_key(text)
        if service_key:
            return {
                "replies": [service_detail(service_key)],
                "state": f"service:{service_key}",
                "customer_name": customer_name,
                "lead": {"service": MENU_OPTIONS[service_key]["name"]},
            }
        return {
            "replies": ["Claro, para cotizar necesito tu nombre."],
            "state": "awaiting_name",
            "customer_name": customer_name,
            "lead": None,
        }

    if _has_any(normalized, INTENT_THANKS):
        return {
            "replies": ["¡Con gusto! Si quieres volver al menú, escribe *menu* o *servicios*. Estoy para ayudarte."],
            "state": state,
            "customer_name": customer_name,
            "lead": None,
        }

    # --- Numeros del menu / seleccion de servicio ---
    if re.fullmatch(r"[0-9]", normalized):
        if normalized == "0":
            return {
                "replies": ["Te pongo en contacto con un asesor. ¿Cual es tu nombre?"],
                "state": "awaiting_name",
                "customer_name": customer_name,
                "lead": None,
            }
        if normalized in MENU_OPTIONS:
            return {
                "replies": [service_detail(normalized)],
                "state": f"service:{normalized}",
                "customer_name": customer_name,
                "lead": None,
            }

    # --- Texto libre: intentar detectar servicio ---
    service_key = _extract_service_key(text)
    if service_key:
        return {
            "replies": [service_detail(service_key)],
            "state": f"service:{service_key}",
            "customer_name": customer_name,
            "lead": None,
        }

    return {
        "replies": [FALLBACK_REPLY],
        "state": state,
        "customer_name": customer_name,
        "lead": None,
    }


def build_lead_message(phone: str, name: str | None, service: str | None, message: str | None) -> str:
    return (
        "*Nuevo lead de cotizacion (WhatsApp Bot)*\n"
        f"- Telefono: {phone}\n"
        f"- Nombre: {name or 'No indicado'}\n"
        f"- Servicio: {service or 'No indicado'}\n"
        f"- Detalle: {message or 'No indicado'}\n"
        f"- Webhook: {settings.whatsapp_business_phone}"
    )
