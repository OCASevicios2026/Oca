"""Calculo de cotizaciones usando la base de costos de OCA (CSV).

Lee la hoja ``CALCULADORA`` de ``BASE DE DATOS.csv`` (catalogo de costos de
construccion, estilo Camacol/SISPAC) que contiene actividades con su precio
por unidad (M2, ML, UN, M3...). Para cada servicio de OCA se define un
conjunto de palabras clave que permiten ubicar las actividades relevantes y
calcular cantidad x precio unitario.

Los precios son de referencia (promedio nacional). No incluyen AIU ni IVA.
"""

import csv
import re
import unicodedata
from functools import lru_cache
from typing import Iterable

CSV_PATH = "BASE DE DATOS.csv"
SHEET = "CALCULADORA"

# Unidades que se consideran "por area" para pedir metraje
AREA_UNITS = ("M2",)


def _norm(text: str) -> str:
    """Normaliza texto: minusculas, sin tildes ni caracteres especiales."""
    text = unicodedata.normalize("NFD", text.lower())
    text = "".join(c for c in text if unicodedata.category(c) != "Mn")
    text = text.replace("ñ", "n").replace("\ufffd", "")
    return re.sub(r"\s+", " ", text).strip()


@lru_cache(maxsize=1)
def load_activities() -> list[dict]:
    """Carga las actividades con precio de la hoja CALCULADORA."""
    items: list[dict] = []
    try:
        with open(CSV_PATH, encoding="utf-8", errors="replace") as f:
            reader = csv.reader(f)
            next(reader, None)  # header
            for row in reader:
                if not row or row[0] != SHEET:
                    continue
                # Fila de actividad: [.., False, codigo, descripcion, unidad, '', precio]
                if len(row) < 7 or not row[2]:
                    continue
                if not re.fullmatch(r"\d{4,6}", row[2].strip()):
                    continue
                try:
                    precio = float(row[6])
                except (TypeError, ValueError):
                    continue
                items.append(
                    {
                        "codigo": row[2].strip(),
                        "descripcion": (row[3] or "").strip(),
                        "unidad": (row[4] or "").strip(),
                        "precio": precio,
                    }
                )
    except FileNotFoundError:
        return []
    return items


# Palabras clave por servicio de OCA (indice de MENU_OPTIONS en knowledge.py)
# Para ubicar las actividades del catalogo que corresponden a cada servicio.
SERVICE_KEYWORDS: dict[str, list[str]] = {
    "2": [  # Estructuras Metalicas
        "cerramiento", "carpinteria metalica", "div ba",
    ],
    "3": [  # Redes de Urbanismo
        "registro", "alcantarillado", "aguas lluvias", "colector", "manjol", "tuberia",
    ],
    "4": [  # Instalaciones Hidraulicas y Sanitarias
        "punto potable", "colector", "punto sanitario", "bajante",
        "juego sanitario", "orinal", "sanitario", "lavamanos", "tuberia",
    ],
    "6": [  # Construccion de Vias
        "pavimento", "adoquin", "subbase", "caliche",
    ],
    "7": [  # Impermeabilizacion
        "impermeabilizacion",
    ],
    "8": [  # Acabados y Mamposteria
        "levant", "panete", "estucado", "pintura", "enchape", "piso",
        "muro", "zocalo", "graniplast", "silcoplast",
    ],
}


def search_activities(service_key: str, limit: int = 6) -> list[dict]:
    """Devuelve actividades del catalogo relevantes para un servicio de OCA."""
    keywords = SERVICE_KEYWORDS.get(service_key)
    if not keywords:
        return []
    norm_kws = [_norm(k) for k in keywords]
    results = []
    seen: set[str] = set()
    for item in load_activities():
        desc = _norm(item["descripcion"])
        score = sum(1 for kw in norm_kws if kw in desc)
        if score:
            key = (desc, item["unidad"])
            if key in seen:
                continue
            seen.add(key)
            results.append((score, item))
    results.sort(key=lambda t: (-t[0], t[1]["precio"]))
    return [item for _, item in results[:limit]]


def quote(service_key: str, cantidad: float, city: str | None = None) -> dict:
    """Calcula una cotizacion estimada para un servicio con una cantidad.

    Devuelve:
    {
      "service_key": str,
      "cantidad": float,
      "items": [{descripcion, unidad, precio, subtotal}],
      "min_total": float, "max_total": float,
      "has_prices": bool,
    }
    """
    items = search_activities(service_key)
    computed = []
    for it in items:
        computed.append(
            {
                "descripcion": it["descripcion"],
                "unidad": it["unidad"],
                "precio": it["precio"],
                "subtotal": round(it["precio"] * cantidad),
            }
        )
    if computed:
        precios = [c["subtotal"] for c in computed]
        return {
            "service_key": service_key,
            "cantidad": cantidad,
            "items": computed,
            "min_total": min(precios),
            "max_total": max(precios),
            "has_prices": True,
        }
    return {
        "service_key": service_key,
        "cantidad": cantidad,
        "items": [],
        "min_total": 0,
        "max_total": 0,
        "has_prices": False,
    }


def format_cop(value: float) -> str:
    """Formatea un numero como moneda colombiana (ej: $1.234.567)."""
    return "${:,.0f}".format(round(value)).replace(",", ".")


def build_quote_text(service_key: str, cantidad: float) -> str:
    """Arma el texto de cotizacion en prosa para enviar por WhatsApp."""
    result = quote(service_key, cantidad)
    if not result["has_prices"]:
        return (
            "Todavía no tengo precios de referencia para este servicio en mi base de costos. "
            "Puedo dejar tus datos a un asesor para que te prepare una cotización formal."
        )

    lines = [
        f"*Cotización estimada* ({_cantidad_text(cantidad)}):",
        "",
    ]
    for it in result["items"]:
        lines.append(
            f"• {it['descripcion']} — {format_cop(it['precio'])} /{it['unidad']} "
            f"(subtotal {format_cop(it['subtotal'])})"
        )
    lines.append("")
    if len(result["items"]) > 1:
        lines.append(
            f"Estimado total entre *{format_cop(result['min_total'])}* "
            f"y *{format_cop(result['max_total'])}*."
        )
    else:
        lines.append(f"Estimado total: *{format_cop(result['min_total'])}*.")
    lines.append("")
    lines.append(
        "Valores de referencia (APUs SISPAC, edición vigente No. 206, "
        "Enero-Febrero 2026). No incluye AIU ni costos indirectos. Un asesor te "
        "confirmará la cotización formal según tu proyecto."
    )
    return "\n".join(lines)


def _cantidad_text(cantidad: float) -> str:
    cantidad = round(cantidad, 2)
    if cantidad == int(cantidad):
        return f"{int(cantidad)} m²"
    return f"{cantidad:.2f} m²"
