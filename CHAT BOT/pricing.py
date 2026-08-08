"""Calculo de cotizaciones usando la base de costos de OCA (CSV).

Lee la hoja ``CALCULADORA`` de ``BASE DE DATOS.csv`` (catalogo de costos de
construccion, estilo Camacol/SISPAC) que contiene actividades con su precio
por unidad (M2, ML, UN, M3...). Para cada servicio de OCA se define un
conjunto de palabras clave que permiten ubicar las actividades relevantes y
calcular cantidad x precio unitario.

Los precios son de referencia (promedio nacional). No incluyen AIU ni IVA.
"""

import csv
import math
import re
import unicodedata
from functools import lru_cache
from typing import Iterable

CSV_PATH = "BASE DE DATOS.csv"
SHEET = "CALCULADORA"

# Unidades que se consideran "por area" para pedir metraje
AREA_UNITS = ("M2",)

# Dimensiones expresadas en el nombre del APU, en cm: 'Ventana 5020 200x100' -> 200x100 cm.
# Solo coincide con DOS dimensiones: '200x100' -> si, '50x50x50' (registro) -> no.
DIM_RE = re.compile(r"(?<![\d.x×X])(\d{2,4})\s*[x×X]\s*(\d{2,4})(?!\s*[x×X])")


def parse_dimensions_m2(desc: str) -> float | None:
    """Area (m2) a partir de las dimensiones en el nombre (en cm).

    'Ventana 5020 200x100' -> 200 cm x 100 cm = 2.0 m2
    'Ventana 5020 300x150 3H' -> 300 cm x 150 cm = 4.5 m2
    'Registro de 50x50x50' -> None (es una caja 3D, se vende por unidad)
    """
    m = DIM_RE.search(desc or "")
    if not m:
        return None
    w_cm, h_cm = int(m.group(1)), int(m.group(2))
    return round((w_cm / 100.0) * (h_cm / 100.0), 3)


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


# Palabras vacias que no aportan a la busqueda en el catalogo
_STOPWORDS = frozenset(
    "cuanto cuesta cuantos necesito quiero saber por para usted quiere una unos "
    "unas seria serian del con sin sobre entre hasta donde cual cuales cuando "
    "hacer hacerle hago una cotizacion cotizar presupuesto precio tarifa costo "
    "queremos quisiera puedo puede me mi tu su de la el los las y o a e".split()
)


def extract_query_keywords(query: str | None) -> str:
    """Extrae las palabras utiles de la consulta del cliente (max ~36 chars).

    Se guarda en el campo ``state`` de la BD (VARCHAR(60)), por eso debe ser
    corto: 'ventana de aluminio por m2' -> 'ventana aluminio'.
    """
    if not query:
        return ""
    words = []
    for w in _norm(query).replace(",", " ").split():
        w = w.strip(".")
        if len(w) <= 3 or w in _STOPWORDS or re.fullmatch(r"\d+([.,]\d+)?", w):
            continue
        if w not in words:
            words.append(w)
    return " ".join(words)[:36]


# Palabras clave por servicio de OCA (indice de MENU_OPTIONS en knowledge.py)
# Para ubicar las actividades del catalogo que corresponden a cada servicio.
SERVICE_KEYWORDS: dict[str, list[str]] = {
    "2": [  # Estructuras Metalicas / Carpinteria Metalica
        "cerramiento", "carpinteria metalica", "div ba", "ventana",
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


def search_activities(service_key: str, limit: int = 6, query: str | None = None) -> list[dict]:
    """Devuelve actividades del catalogo relevantes para un servicio de OCA.

    ``query`` es el texto libre del cliente (ej: 'ventana de aluminio'); las
    actividades cuyo nombre coincida con esas palabras se priorizan, para que
    una ventana no muestre cerramientos ni desmontes.
    """
    keywords = SERVICE_KEYWORDS.get(service_key)
    if not keywords:
        return []
    norm_kws = [_norm(k) for k in keywords]
    extra_kws = [_norm(w) for w in (query or "").replace(",", " ").split()]
    extra_kws = [w for w in extra_kws if len(w) > 3 and w not in (
        "cuanto", "cuesta", "cuantos", "necesito", "quiero", "saber", "por",
        "para", "usted", "quiere", "una", "unos", "unas", "seria", "seria",
    )]
    want_desmont = "desmont" in _norm(query or "")
    results = []
    seen: set[str] = set()
    for item in load_activities():
        desc = _norm(item["descripcion"])
        if "desmont" in desc and not want_desmont:
            continue
        score = sum(1 for kw in norm_kws if kw in desc)
        extra_score = sum(1 for kw in extra_kws if kw in desc)
        if score or extra_score:
            # Se deduplica por codigo: filas repetidas con el mismo APU no
            # deben duplicarse, pero APUs distintos con igual descripcion
            # (mismos materiales, precios diferentes) si deben aparecer.
            if item["codigo"] in seen:
                continue
            seen.add(item["codigo"])
            results.append((score, extra_score, item))
    # Prioriza coincidencias con la consulta del cliente, luego las del servicio
    results.sort(key=lambda t: (-t[1], -t[0], t[2]["precio"]))
    return [item for _, _, item in results[:limit]]


# Modo de cantidad segun la unidad del APU
_UNIT_MODE = {"M2": "area", "UN": "units", "ML": "linear", "ML2": "linear", "M3": "volume"}
# Prioridad al resolver el modo cuando no se indica (desempate)
_UNIT_PRIORITY = {"M2": 4, "UN": 3, "ML": 2, "M3": 1}


def _resolve_unit_mode(mode: str | None, items: list[dict]) -> str:
    """Decide el modo de cantidad ("area"|"units"|"linear"|"volume").

    Si la consulta no aclara la unidad, se infiere de las actividades mas
    relevantes (las que coinciden con el texto del cliente, que van primero
    porque ``search_activities`` ordena por coincidencia).
    """
    if mode in ("area", "units", "linear", "volume"):
        return mode
    top = items[:4]
    counts: dict[str, int] = {}
    for it in top:
        counts[it["unidad"]] = counts.get(it["unidad"], 0) + 1
    if counts:
        best = max(
            counts.items(),
            key=lambda kv: (kv[1], _UNIT_PRIORITY.get(kv[0], 0)),
        )[0]
        return _UNIT_MODE.get(best, "area")
    return "area"


def _item_fits_mode(it: dict, mode: str) -> bool:
    """Indica si una actividad puede cotizarse en el modo de cantidad activo.

    Evita mezclar unidades: si el cliente pide m2 no se muestra el precio de
    cerramientos por metro lineal ni de UN sin dimensiones; si pide unidades
    no se muestran las tuberias por metro, etc.
    """
    u = it["unidad"]
    if mode == "area":
        return u == "M2" or (u == "UN" and parse_dimensions_m2(it["descripcion"]) is not None)
    if mode == "units":
        return u == "UN"
    if mode == "linear":
        return u in ("ML", "ML2")
    if mode == "volume":
        return u == "M3"
    return True


def quote(
    service_key: str,
    cantidad: float,
    city: str | None = None,
    query: str | None = None,
    unit: str | None = None,
) -> dict:
    """Calcula una cotizacion estimada para un servicio con una cantidad.

    `unit` controla como se interpreta la cantidad: "area" (m2), "units"
    (unidades) o "linear" (metros lineales). Para actividades UN con
    dimensiones en el nombre (ej: 'Ventana 5020 200x100'), el precio se
    convierte a $/m2 y la cantidad en area se traduce al numero de unidades
    necesarias.

    Devuelve:
    {
      "service_key": str,
      "cantidad": float,
      "unit": str,
      "items": [{descripcion, unidad, precio, area_m2, precio_m2, units, subtotal}],
      "min_total": float, "max_total": float,
      "has_prices": bool,
    }
    """
    items = search_activities(service_key, query=query)
    mode = _resolve_unit_mode(unit, items)
    items = [it for it in items if _item_fits_mode(it, mode)]
    computed = []
    for it in items:
        precio = round(it["precio"])
        desc = it["descripcion"]
        area_m2 = parse_dimensions_m2(desc) if it["unidad"] == "UN" else None
        precio_m2 = round(precio / area_m2) if area_m2 else None

        if it["unidad"] == "M2":
            # La cantidad ya viene en m2
            units = cantidad
            subtotal = round(precio * cantidad)
        elif it["unidad"] == "M3":
            # La cantidad viene en metros cubicos
            units = cantidad
            subtotal = round(precio * cantidad)
        elif it["unidad"] in ("ML", "ML2"):
            # La cantidad viene en metros lineales
            units = cantidad
            subtotal = round(precio * cantidad)
        elif it["unidad"] == "UN" and area_m2 and mode == "area":
            # Cantidad en m2 -> cuantas unidades cubren esa area
            units = math.ceil(cantidad / area_m2)
            subtotal = round(precio * units)
        else:
            # Unidades directas (o UN sin dimensiones)
            units = cantidad
            subtotal = round(precio * cantidad)

        computed.append(
            {
                "descripcion": desc,
                "unidad": it["unidad"],
                "precio": precio,
                "area_m2": area_m2,
                "precio_m2": precio_m2,
                "units": units,
                "subtotal": subtotal,
            }
        )
    if computed:
        precios = [c["subtotal"] for c in computed]
        return {
            "service_key": service_key,
            "cantidad": cantidad,
            "unit": mode,
            "items": computed,
            "min_total": min(precios),
            "max_total": max(precios),
            "has_prices": True,
        }
    return {
        "service_key": service_key,
        "cantidad": cantidad,
        "unit": mode,
        "items": None,
        "min_total": 0,
        "max_total": 0,
        "has_prices": False,
    }


def format_cop(value: float) -> str:
    """Formatea un numero como moneda colombiana (ej: $1.234.567)."""
    return "${:,.0f}".format(round(value)).replace(",", ".")


def build_quote_text(service_key: str, cantidad: float, query: str | None = None, unit: str | None = None) -> str:
    """Arma el texto de cotizacion en prosa para enviar por WhatsApp."""
    result = quote(service_key, cantidad, query=query, unit=unit)
    if not result["has_prices"]:
        if result["items"] is None:
            # Hay actividades, pero ninguna cotizable en esa unidad (ej: pedir
            # m2 de un registro que se vende por unidad)
            return (
                "En este servicio las actividades se cotizan por otra unidad "
                "(unidades, metros lineales o m³), no por m². ¿Cuál necesitas?"
            )
        return (
            "Todavía no tengo precios de referencia para este servicio en mi base de costos. "
            "Puedo dejar tus datos a un asesor para que te prepare una cotización formal."
        )

    mode = result["unit"]
    cantidad_label = {
        "area": _cantidad_text(cantidad) + " m²",
        "units": _cantidad_text(cantidad) + " unid.",
        "linear": _cantidad_text(cantidad) + " ml",
        "volume": _cantidad_text(cantidad) + " m³",
    }[mode]

    lines = [
        f"*Cotización estimada* (para {cantidad_label}):",
        "",
    ]
    for it in result["items"]:
        detail = _item_detail(it, mode, cantidad)
        lines.append(detail)
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


def _item_detail(it: dict, mode: str, cantidad: float) -> str:
    """Describe una actividad dentro de la cotizacion segun el modo de cantidad."""
    base = f"• {it['descripcion']} — {format_cop(it['precio'])} /{it['unidad']}"
    area_m2 = it.get("area_m2")
    if it["unidad"] == "UN" and area_m2 and mode == "area":
        # Ej: Ventana 5020 200x100 (2 m² c/u) -> $285.628/m²
        per_m2 = format_cop(it["precio_m2"])
        units = it["units"]
        units_text = _cantidad_text(units)
        base = (
            f"• {it['descripcion']} — {format_cop(it['precio'])} /UN "
            f"({_format_area(area_m2)} m² c/u, ≈{per_m2} /m²) → {units_text} unid. "
            f"(subtotal {format_cop(it['subtotal'])})"
        )
    else:
        base = f"{base} (subtotal {format_cop(it['subtotal'])})"
    return base


def _format_area(area: float) -> str:
    """Formatea un area en m2 (1.0 -> 1, 4.5 -> 4,5)."""
    if area == int(area):
        return str(int(area))
    return f"{area:.2f}".replace(".", ",").rstrip("0").rstrip(",")


def _cantidad_text(cantidad: float) -> str:
    cantidad = round(cantidad, 2)
    if cantidad == int(cantidad):
        return str(int(cantidad))
    return f"{cantidad:.2f}".replace(".", ",")
