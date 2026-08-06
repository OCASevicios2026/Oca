"""Logica de conversacion del chatbot de OCA Servicios Integrales."""

import re
import unicodedata

from config import settings

MENU_OPTIONS = {
    "1": {
        "name": "Consultorias",
        "desc": "Diseno arquitectonico, estructural, hidraulico y de vias para proyectos residenciales, comerciales e institucionales, con estudios de viabilidad y acompanamiento tecnico en cada etapa.",
        "items": [
            "Diseno arquitectonico y estructural",
            "Diseno hidraulico y de vias",
            "Proyectos residenciales, comerciales e institucionales",
            "Estudios de viabilidad y asesoria tecnica",
        ],
    },
    "2": {
        "name": "Estructuras Metalicas",
        "desc": "Construccion de estructuras metalicas para edificaciones, bodegas, cubiertas y carpinteria metalica, con fabricacion y montaje certificado.",
        "items": [
            "Edificaciones, bodegas y cubiertas",
            "Carpinteria metalica",
            "Fabricacion y montaje certificado",
            "Soldadura y trabajos en acero",
        ],
    },
    "3": {
        "name": "Redes de Urbanismo",
        "desc": "Construccion de redes de alcantarillado e hidraulicas, registros de inspeccion (manjoles) y estructuras para el manejo de aguas lluvias.",
        "items": [
            "Redes de alcantarillado sanitario",
            "Registros de inspeccion (manjoles)",
            "Estructuras para manejo de aguas lluvias",
            "Obra urbana e infraestructura",
        ],
    },
    "4": {
        "name": "Instalaciones Hidraulicas y Sanitarias",
        "desc": "Instalacion de redes hidraulicas y sanitarias, con suministro de macromedidores y micromedidores y cumplimiento de la normatividad vigente.",
        "items": [
            "Redes hidraulicas y sanitarias",
            "Suministro de macromedidores y micromedidores",
            "Diseno e instalacion de redes domiciliarias",
            "Cumplimiento de normatividad vigente",
        ],
    },
    "5": {
        "name": "Redes Contra Incendios",
        "desc": "Diseno e instalacion de sistemas contra incendios para proteger vidas y bienes: redes de hidrantes, gabinetes, rociadores y estaciones de bombeo, cumpliendo la normatividad vigente.",
        "items": [
            "Redes de hidrantes y gabinetes",
            "Sistemas de rociadores automaticos",
            "Estaciones de bombeo y tanques",
            "Cumplimiento de la normatividad vigente",
        ],
    },
    "6": {
        "name": "Construccion de Vias",
        "desc": "Pavimento rigido y pavimento articulado (adoquin) para vias urbanas, accesos y zonas de transito vehicular, con preparacion de subbase y nivelacion.",
        "items": [
            "Pavimento rigido en concreto",
            "Pavimento articulado (adoquin)",
            "Vias urbanas, accesos y parqueaderos",
            "Preparacion de subbase y nivelacion",
        ],
    },
    "7": {
        "name": "Impermeabilizacion",
        "desc": "Impermeabilizacion de cubiertas y zonas comunes para proteger las edificaciones de filtraciones y humedad, con tratamiento y sellado de superficies.",
        "items": [
            "Cubiertas y terrazas",
            "Zonas comunes y fachadas",
            "Proteccion contra filtraciones",
            "Tratamiento de humedad y sellado",
        ],
    },
    "8": {
        "name": "Acabados y Mamposteria",
        "desc": "Levante de muros, panete, estuco, pintura, acabados y mantenimiento de fachadas de edificios, ademas de remodelaciones y adecuaciones.",
        "items": [
            "Levante de muros y panete",
            "Estuco, pintura y acabados",
            "Mantenimiento de fachadas",
            "Remodelaciones y adecuaciones",
        ],
    },
    "9": {
        "name": "Mantenimiento A/C",
        "desc": "Servicio especializado de mantenimiento correctivo y preventivo de aires acondicionados, residenciales, comerciales e industriales, con atencion 24/7.",
        "items": [
            "Mantenimiento preventivo programado",
            "Mantenimiento correctivo y diagnostico",
            "Equipos residenciales, comerciales e industriales",
            "Atencion de urgencias 24/7",
        ],
    },
}

BUSINESS_INFO = (
    "*OCA Servicios Integrales S.A.S.*\n"
    "NIT 900.413.290-7\n"
    "Santa Marta, Magdalena, Colombia\n\n"
    "*Telefono / WhatsApp:* 317 400 4016 · 420 7586\n"
    "*Direccion:* Calle 14 #14-123 Loc. 402 B, Santa Marta\n"
    "(Av. del Libertador 19-97)\n"
    "*Horario:* Lunes a Sabado, 7:00 am - 6:00 pm\n"
    "*Mantenimiento A/C:* urgencias 24/7"
)


def build_menu() -> str:
    lines = [
        "*OCA Servicios Integrales S.A.S.*",
        "",
        "Somos especialistas en obras de ingenieria civil y climatizacion en Santa Marta y el Caribe.",
        "",
        "¿En que podemos ayudarte? Responde con el *numero* de la opcion:",
        "",
    ]
    for key, svc in MENU_OPTIONS.items():
        lines.append(f"{key}. {svc['name']}")
    lines.extend(
        [
            "",
            "0. Hablar con un asesor",
            "",
            "Tambien puedes escribir *servicios*, *cotizar*, *contacto* u *horario*.",
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
            "¿Deseas que un asesor te cotice este servicio? Responde *SI* o *NO*.",
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
            return {
                "replies": ["Perfecto. ¿Cual es tu nombre?"],
                "state": "awaiting_name",
                "customer_name": customer_name,
                "lead": {"service": MENU_OPTIONS[state.split(":")[1]]["name"]},
            }
        if _has_any(normalized, INTENT_NO):
            return {
                "replies": ["Sin problema. ¿En que mas puedo ayudarte?"],
                "state": "menu",
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
                "replies": [
                    service_detail(service_key),
                    "¿Deseas cotizar este servicio? Responde *SI* o *NO*.",
                ],
                "state": f"service:{service_key}",
                "customer_name": customer_name,
                "lead": {"service": MENU_OPTIONS[service_key]["name"]},
            }
        return {
            "replies": ["Para cotizar, cuentanos primero cual es tu nombre."],
            "state": "awaiting_name",
            "customer_name": customer_name,
            "lead": None,
        }

    if _has_any(normalized, INTENT_THANKS):
        return {
            "replies": ["¡Con gusto! Para volver al menu escribe *menu* o *servicios*. Quedamos atentos."],
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
        "replies": [
            "No entiendo bien tu mensaje, pero con gusto te ayudo. Escribe *menu* para ver las opciones o el numero del servicio que necesitas."
        ],
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
