"""Logica de conversacion del chatbot de OCA Servicios Integrales.

Combina el flujo por reglas (menu, cotizaciones y leads) con la IA de Gemini
para conversaciones naturales y mensajes multimedia.
"""

import re
import unicodedata

from config import settings
from knowledge import BUSINESS_INFO, MENU_OPTIONS
import pricing

# Respuesta generica cuando las reglas no reconocen el mensaje.
# main.py detecta esta respuesta para delegar la conversacion a Gemini.
FALLBACK_REPLY = (
    "No entiendo bien tu mensaje, pero con gusto te ayudo. Escribe *menu* "
    "para ver las opciones o el numero del servicio que necesitas."
)

def build_menu() -> str:
    lines = [
        "Ofrecemos consultorías, estructuras metálicas, redes de urbanismo, instalaciones hidráulicas y sanitarias, redes contra incendios, construcción de vías, impermeabilización, acabados y mampostería, y mantenimiento de A/C.",
        "",
        "¿En cuál de estos servicios te puedo ayudar?",
    ]
    return "\n".join(lines)


def service_detail(key: str) -> str:
    svc = MENU_OPTIONS[key]
    lines = [f"{svc['name']}", "", svc["desc"], ""]
    lines.extend(f"- {item}" for item in svc["items"])
    lines.extend(
        [
            "",
            "¿Te gustaría que un asesor te prepare una cotización?",
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
INTENT_MENU = ("menu", "opciones", "catalogo", "servicios", "servicio", "que hacen", "que ofrecen", "ayuda")
INTENT_CONTACT = ("contacto", "telefono", "whatsapp", "direccion", "ubicacion", "donde", "nit", "correo")
INTENT_HOURS = ("horario", "horas", "atienden", "cuando atienden")
INTENT_QUOTE = ("cotizar", "cotizo", "cotizame", "cotiza", "cotizacion", "presupuesto", "precio", "tarifa", "costo", "cuanto cuesta")
INTENT_HUMAN = ("asesor", "persona", "humano", "agente", "hablar con alguien", "un tecnico", "atencio")
INTENT_YES = ("si", "sip", "claro", "perfecto", "dale", "ok", "bueno", "sale", "confirmar")
INTENT_NO = ("no", "nop", "no gracias", "ahora no", "despues")
INTENT_THANKS = ("gracias", "muchas gracias", "genial", "excelente", "vale", "ok perfecto")
INTENT_CANCEL = ("cancelar", "cancelacion", "dejarlo", "salir", "empezar de nuevo", "olvidalo", "deja asi")


AREA_PATTERNS = (
    r"(\d+(?:[.,]\d+)?)\s*(?:mts?\s*cuadrados?|m2|m²|metros?\s*cuadrados?|mts|metros?)",
    r"(\d+(?:[.,]\d+)?)\s*(?:metros?)\b",
)


def _extract_area(text: str) -> float | None:
    """Extrae el metraje (m2) de un mensaje, p.ej. '50 m2' -> 50.0."""
    text = text.lower().replace(",", ".")
    for pattern in AREA_PATTERNS:
        m = re.search(pattern, text)
        if m:
            try:
                return float(m.group(1))
            except ValueError:
                return None
    return None


def _bare_number(text: str) -> float | None:
    """Numero suelto (ej: '50') que usa el estado awaiting_area."""
    m = re.fullmatch(r"\s*(\d+(?:\.\d+)?)\s*", text.lower().replace(",", "."))
    if m:
        try:
            return float(m.group(1))
        except ValueError:
            return None
    return None


def _extract_unit_mode(text: str) -> str | None:
    """Detecta si el usuario pide la cantidad en m2, ml o unidades.

    Se revisa en orden de prioridad: area, lineal, unidades. Debe ejecutarse
    antes de detectar 'ventana'/'unidad' para que 'ventana por m2' sea area.
    """
    t = normalize(text)
    if _has_any(t, ("m2", "m²", "metro cuadrado", "metros cuadrados", "metros cuadrado", "mt2")):
        return "area"
    if _has_any(t, ("metro lineal", "metros lineales", "lineal")) or re.search(r"\bml\b", t):
        return "linear"
    if _has_any(t, ("unidad", "unid", "ventana", "pieza", "piezas")):
        return "units"
    return None


def _parse_awaiting_area(state: str) -> tuple[str, str, str]:
    """Parseo de 'awaiting_area:2:area|keywords' -> (service_key, mode, keywords)."""
    payload = state.split(":", 1)[1]
    key_part, _, keywords = payload.partition("|")
    key, _, mode = key_part.partition(":")
    return key, mode or "auto", keywords


def _extract_service_key(text: str) -> str | None:
    """Intenta adivinar el servicio por texto libre (ej: 'quiero cotizar el A/C')."""
    text = normalize(text)
    for key, svc in MENU_OPTIONS.items():
        name = normalize(svc["name"])
        if name in text:
            return key
    aliases = {
        "1": ("consultor", "diseno", "viabilidad"),
        "2": ("metalica", "metal", "soldadura", "acero", "estructura", "ventana", "aluminio", "vidrio", "rejas", "cerramiento"),
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


def _try_quote(text: str, customer_name: str | None) -> dict | None:
    """Si el texto pide una cotizacion de un servicio, devuelve el resultado.

    Devuelve None si no hay intento de cotizacion o no se reconoce el servicio.
    Si el mensaje ya incluye el metraje (ej: '50 m2'), cotiza directo; si no,
    pasa al estado awaiting_area para pedir el metraje.
    """
    if not _has_any(normalize(text), INTENT_QUOTE):
        return None
    service_key = _extract_service_key(text)
    if not service_key:
        return None
    unit_mode = _extract_unit_mode(text) or "auto"
    area = _extract_area(text)
    if area and area > 0:
        quote_text = pricing.build_quote_text(service_key, area, query=text, unit=unit_mode)
        return {
            "replies": [
                service_detail(service_key),
                quote_text,
                "¿Te gustaría que un asesor te prepare la cotización formal?",
            ],
            "state": f"service:{service_key}",
            "customer_name": customer_name,
            "lead": {"service": MENU_OPTIONS[service_key]["name"]},
        }
    return {
        "replies": [
            service_detail(service_key),
            "Para calcular tu cotización, ¿cuántos metros cuadrados (m²), metros lineales (ml) o unidades necesitas? Por ejemplo: 50 m2 o 3.",
        ],
        "state": f"awaiting_area:{service_key}:{unit_mode}|{pricing.extract_query_keywords(text)}",
        "customer_name": customer_name,
        "lead": {"service": MENU_OPTIONS[service_key]["name"]},
    }


def handle_inbound(text: str, state: str, customer_name: str | None) -> dict:
    """Devuelve {replies, state, customer_name, lead} segun el estado actual."""
    normalized = normalize(text)

    # --- Comandos de escape: permiten salir de los flujos de captura ---
    # Si el usuario esta en medio de una cotizacion (pide nombre o detalles)
    # y escribe un comando general, se cancela la captura y se vuelve al menu.
    if state in ("awaiting_name", "awaiting_details") or state.startswith("awaiting_area:"):
        if (
            _has_any(normalized, INTENT_CANCEL)
            or _has_any(normalized, INTENT_MENU)
            or _has_any(normalized, INTENT_HI)
            or normalized in ("0", "menu")
        ):
            return {
                "replies": [build_menu()],
                "state": "menu",
                "customer_name": customer_name,
                "lead": None,
            }

    # Si el cliente pregunta un precio estando en medio de la captura de datos
    # (nombre/detalles), responder con la cotizacion antes que cerrar el lead.
    if state in ("awaiting_name", "awaiting_details"):
        quote_result = _try_quote(text, customer_name)
        if quote_result:
            return quote_result

    # --- Estados de captura de datos ---
    if state == "awaiting_name":
        name = text.strip()
        return {
            "replies": [
                f"Gracias, {name}. Cuentanos brevemente tu proyecto o necesidad para pasarsela al asesor (por ejemplo, el tipo de servicio, el lugar y el alcance)."
            ],
            "state": "awaiting_details",
            "customer_name": name,
            "lead": None,
        }

    if state == "awaiting_details":
        return {
            "replies": [
                "¡Perfecto! Hemos registrado tu solicitud. Un asesor de OCA te contactara muy pronto por este mismo canal.",
            ],
            "state": "menu",
            "customer_name": customer_name,
            "lead": {"message": text},
        }

    # --- Estado dentro de un servicio: espera SI/NO ---
    if state.startswith("service:"):
        if _has_any(normalized, INTENT_YES):
            lead_service = {"service": MENU_OPTIONS[state.split(":")[1]]["name"]}
            if customer_name:
                return {
                    "replies": [
                        "Perfecto. Cuentanos brevemente tu proyecto o necesidad para pasarsela al asesor (por ejemplo, el tipo de servicio, el lugar y el alcance)."
                    ],
                    "state": "awaiting_details",
                    "customer_name": customer_name,
                    "lead": lead_service,
                }
            return {
                "replies": ["Perfecto. ¿Cual es tu nombre?"],
                "state": "awaiting_name",
                "customer_name": customer_name,
                "lead": lead_service,
            }
        if _has_any(normalized, INTENT_NO):
            return {
                "replies": ["Sin problema. ¿En que mas puedo ayudarte?"],
                "state": "menu",
                "customer_name": customer_name,
                "lead": None,
            }

    # --- Estado dentro de una cotizacion: espera el metraje (m2) ---
    if state.startswith("awaiting_area:"):
        service_key, stored_mode, query = _parse_awaiting_area(state)
        area = _extract_area(text) or _bare_number(text)
        unit_mode = _extract_unit_mode(text) or stored_mode or "auto"
        if area and area > 0:
            quote_text = pricing.build_quote_text(service_key, area, query=query or None, unit=unit_mode)
            return {
                "replies": [quote_text, "¿Te gustaría que un asesor te prepare la cotización formal?"],
                "state": f"service:{service_key}",
                "customer_name": customer_name,
                "lead": {"service": MENU_OPTIONS[service_key]["name"]},
            }
        return {
            "replies": [
                "Disculpa, necesito saber la cantidad para calcularlo. "
                "¿Cuántos metros cuadrados (m²), metros lineales (ml) o unidades necesitas? Por ejemplo: 50 m2 o 3."
            ],
            "state": state,
            "customer_name": customer_name,
            "lead": None,
        }

    # --- Comandos generales ---
    if _has_any(normalized, INTENT_HUMAN):
        if customer_name:
            return {
                "replies": ["Te pongo en contacto con un asesor. ¿Cual es tu nombre?"],
                "state": "awaiting_name",
                "customer_name": customer_name,
                "lead": None,
            }
        return {
            "replies": ["Con gusto. Un asesor te atendera. ¿Cual es tu nombre?"],
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
        service_key = _extract_service_key(text)
        if service_key:
            return {
                "replies": [service_detail(service_key)],
                "state": f"service:{service_key}",
                "customer_name": customer_name,
                "lead": None,
            }
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
        quote_result = _try_quote(text, customer_name)
        if quote_result:
            return quote_result
        return {
            "replies": ["Para cotizar, cuentanos primero cual es tu nombre."],
            "state": "awaiting_name",
            "customer_name": customer_name,
            "lead": None,
        }

    if _has_any(normalized, INTENT_THANKS):
        return {
            "replies": ["¡Con gusto! Si necesitas algo más, aquí estoy. Quedamos atentos."],
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
