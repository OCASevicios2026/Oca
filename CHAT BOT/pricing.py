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

# Columnas de precios por region en las hojas A.P.U. (verificadas contra el CSV)
CITY_COLUMNS: dict[str, int] = {
    "nacional": 8,   # Prom. Nacional (== precio de CALCULADORA)
    "bogota": 10,
    "medellin": 12,
    "cali": 14,
    "barranquilla": 16,
}

# Como se muestran las ciudades en la cotizacion
CITY_NAMES: dict[str, str] = {
    "nacional": "promedio nacional",
    "bogota": "Bogotá",
    "medellin": "Medellín",
    "cali": "Cali",
    "barranquilla": "Barranquilla",
}

# Codigos cortos para el campo `state` (VARCHAR(60)): 'barq', 'bog', etc.
CITY_SHORT: dict[str, str] = {
    "barranquilla": "barq",
    "bogota": "bog",
    "medellin": "med",
    "cali": "cal",
    "nacional": "nac",
}
CITY_LONG: dict[str, str] = {v: k for k, v in CITY_SHORT.items()}

# Como se pide una ciudad (sin tildes, por normalize). Orden importa:
# "santa marta" se busca antes de "marta" suelta.
CITY_ALIASES: dict[str, tuple[str, ...]] = {
    "santa marta": ("santa marta",),
    "barranquilla": ("barranquilla", "barranquillero"),
    "bogota": ("bogota",),
    "medellin": ("medellin",),
    "cali": ("cali",),
    "nacional": ("nacional", "promedio", "colombia", "pais"),
}

# Ciudades que usan el precio de Barranquilla (OCA opera desde la costa)
CITY_FALLBACK: dict[str, str] = {
    "santa marta": "barranquilla",
}

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


def normalize_city(text: str | None) -> str | None:
    """Convierte la ciudad del cliente en la clave estandar (sin tildes).

    'barranquilla', 'Barranquilla' -> 'barranquilla'
    'santa marta', 'Santa Marta'   -> 'santa marta' (y se cotiza con Barranquilla)
    'bogota'/'Bogota'              -> 'bogota'
    Si no reconoce ninguna ciudad, devuelve None.
    """
    if not text:
        return None
    t = _norm(text)
    for city, aliases in CITY_ALIASES.items():
        for alias in aliases:
            if alias in t:
                return city
    return None


def resolve_city(city: str | None) -> str | None:
    """Devuelve la ciudad cuyo precio debe usarse (aplica fallbacks).

    'santa marta' -> 'barranquilla'. 'nacional' se conserva como tal.
    """
    if not city:
        return None
    return CITY_FALLBACK.get(city, city)


@lru_cache(maxsize=1)
def load_city_prices() -> dict[str, dict[str, float]]:
    """Carga los precios por ciudad de las hojas A.P.U. del CSV.

    Devuelve {codigo: {ciudad: precio}}. Solo considera ciudades con precio
    valido; si una ciudad no tiene precio para un codigo, se usa el precio
    base de CALCULADORA (nacional).
    """
    prices: dict[str, dict[str, float]] = {}
    try:
        with open(CSV_PATH, encoding="utf-8", errors="replace") as f:
            reader = csv.reader(f)
            for row in reader:
                if not row or row[0] not in ("A.P.U. EDIFICACIONES", "A.P.U. OBRAS CIVILES"):
                    continue
                if not row[1] or not re.fullmatch(r"\d{4,6}", row[1].strip()):
                    continue
                codigo = row[1].strip()
                entry: dict[str, float] = {}
                for city, idx in CITY_COLUMNS.items():
                    try:
                        value = float(row[idx])
                    except (ValueError, IndexError, TypeError):
                        continue
                    if value > 0:
                        entry[city] = value
                if entry:
                    prices[codigo] = entry
    except FileNotFoundError:
        return {}
    return prices


def get_city_price(codigo: str, city: str | None) -> float | None:
    """Precio de una actividad en la ciudad dada (o None si no hay dato)."""
    if not city or city == "nacional":
        return None
    return load_city_prices().get(codigo, {}).get(city)


# Palabras vacias que no aportan a la busqueda en el catalogo
_STOPWORDS = frozenset(
    "cuanto cuesta cuantos necesito quiero saber por para usted quiere una unos "
    "unas seria serian del con sin sobre entre hasta donde cual cuales cuando "
    "hacer hacerle hago una cotizacion cotizar presupuesto precio tarifa costo "
    "queremos quisiera puedo puede me mi tu su de la el los las y o a e".split()
)


# Palabras de ciudades (para que no contaminen las keywords del estado ni la busqueda)
_CITY_WORDS = frozenset(
    w for aliases in CITY_ALIASES.values() for a in aliases for w in a.split()
)


def _stem(word: str) -> str:
    """Raiz simple en espanol: 'ventanas' -> 'ventana', 'obras' -> 'obra'."""
    if len(word) > 4 and word.endswith("s"):
        return word[:-1]
    return word


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
        if len(w) <= 3 or w in _STOPWORDS or w in _CITY_WORDS or re.fullmatch(r"\d+([.,]\d+)?", w):
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
    # Keywords del query del cliente, con raiz (ventanas -> ventana)
    extra_kws = [_stem(_norm(w)) for w in (query or "").replace(",", " ").split()]
    extra_kws = [w for w in extra_kws if len(w) > 3 and w not in (
        "cuanto", "cuest", "cuanto", "necesit", "quier", "saber", "por",
        "para", "usted", "quiere", "una", "unos", "una", "seria",
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
    # Prioriza las coincidencias con el texto del cliente (extra_score); con
    # empate, las del servicio (score). Con la raiz (ventanas->ventana) esto
    # ubica las Ventanas antes que los cielorasos solo por 'aluminio', y las
    # Tuberias antes que los Colectores por 'tuberia'.
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

    `city` es la clave de ciudad (ej: 'barranquilla'); si la actividad tiene
    precio para esa ciudad se usa ese valor, si no, el promedio nacional.
    `unit` controla como se interpreta la cantidad: "area" (m2), "units"
    (unidades), "linear" (metros lineales) o "volume" (m3). Para actividades
    UN con dimensiones en el nombre (ej: 'Ventana 5020 200x100'), el precio se
    convierte a $/m2 y la cantidad en area se traduce al numero de unidades
    necesarias.

    Devuelve:
    {
      "service_key": str,
      "cantidad": float,
      "unit": str,
      "city": str | None,
      "items": [{descripcion, unidad, precio, area_m2, precio_m2, units, subtotal}],
      "min_total": float, "max_total": float,
      "has_prices": bool,
    }
    """
    items = search_activities(service_key, query=query)
    mode = _resolve_unit_mode(unit, items)
    items = [it for it in items if _item_fits_mode(it, mode)]
    city = resolve_city(city)
    computed = []
    for it in items:
        city_precio = get_city_price(it["codigo"], city)
        precio = round(city_precio) if city_precio else round(it["precio"])
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
            "city": city,
            "items": computed,
            "min_total": min(precios),
            "max_total": max(precios),
            "has_prices": True,
        }
    return {
        "service_key": service_key,
        "cantidad": cantidad,
        "unit": mode,
        "city": city,
        "items": None,
        "min_total": 0,
        "max_total": 0,
        "has_prices": False,
    }


def format_cop(value: float) -> str:
    """Formatea un numero como moneda colombiana (ej: $1.234.567)."""
    return "${:,.0f}".format(round(value)).replace(",", ".")


def build_quote_text(service_key: str, cantidad: float, query: str | None = None, unit: str | None = None, city: str | None = None) -> str:
    """Arma el texto de cotizacion en prosa para enviar por WhatsApp."""
    result = quote(service_key, cantidad, city=city, query=query, unit=unit)
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

    head = "Cotización estimada"
    if result["city"]:
        head += f" en {CITY_NAMES.get(result['city'], 'promedio nacional')}"
    head += f" para {cantidad_label}"
    qlabel = extract_query_keywords(query)
    if qlabel:
        head += f" de {qlabel}"
    header = f"*{head}*:"

    rows, per_h, qty_h = _quote_rows(result, mode, cantidad)
    lines = [
        header,
        "",
        _build_table(rows, per_h, qty_h),
        "",
    ]

    # La opcion mas economica (por m² en area, por unidad en el resto)
    best = min(rows, key=lambda r: r[1])
    per_unit = {"area": "m²", "units": "unid.", "linear": "ml", "volume": "m³"}[mode]
    lines.append(
        f"*La opción más económica por {per_unit} es la {best[0]}, "
        f"con aprox. {format_cop(best[1])}/{per_unit}.*"
    )

    nota = _rounding_note(result["items"], cantidad, mode)
    if nota:
        lines.extend(["", nota])
    lines.extend(
        [
            "",
            "Valores de referencia según APUs SISPAC No. 206, enero-febrero de 2026. "
            "No incluyen AIU ni costos indirectos. La cotización final dependerá de las "
            "especificaciones y condiciones del proyecto.",
        ]
    )
    return "\n".join(lines)


def _quote_rows(result: dict, mode: str, cantidad: float) -> tuple[list, str, str]:
    """Filas de la tabla: (modelo, precio/m²|unid, cantidad, total) y cabeceras."""
    rows: list = []
    if mode == "area":
        per_h, qty_h = "$/m²", "Cantidad"
        for it in result["items"]:
            if it["unidad"] == "UN" and it.get("area_m2"):
                # Ej: Ventana 5020 300x150 3H (4,5 m² c/u): para 20 m² -> 5 unid (22,5 m²)
                per = it["precio_m2"]
                real = round(it["units"] * it["area_m2"], 3)
                qty = f"{_cantidad_text(it['units'])} unid ({_format_area(real)} m²)"
            else:
                per = it["precio"]
                qty = _format_area(cantidad) + " m²"
            rows.append((it["descripcion"], per, qty, it["subtotal"]))
    else:
        per_h = {"units": "$/unid", "linear": "$/ml", "volume": "$/m³"}[mode]
        qty_h = "Cantidad"
        unit_label = {"units": "unid", "linear": "ml", "volume": "m³"}[mode]
        for it in result["items"]:
            qty = f"{_cantidad_text(it['units'])} {unit_label}"
            rows.append((it["descripcion"], it["precio"], qty, it["subtotal"]))
    return rows, per_h, qty_h


def _build_table(rows: list, per_h: str, qty_h: str, total_h: str = "Total", max_model: int = 30) -> str:
    """Tabla en monospace (bloque ``` de WhatsApp) alineando columnas con espacios."""
    modelo_w = min(max(len(r[0]) for r in rows) + 2, max_model)
    per_w = max(len(per_h), *(len(format_cop(r[1])) for r in rows))
    qty_w = max(len(qty_h), *(len(r[2]) for r in rows))
    tot_w = max(len(total_h), *(len(format_cop(r[3])) for r in rows))

    def row(modelo, per, qty, total):
        if len(modelo) > max_model:
            modelo = modelo[: max_model - 1] + "…"
        return (
            f"{modelo.ljust(modelo_w)}"
            f"{format_cop(per).rjust(per_w)}  "
            f"{qty.rjust(qty_w)}  "
            f"{format_cop(total).rjust(tot_w)}"
        )

    header = (
        f"{'Modelo'.ljust(modelo_w)}"
        f"{per_h.rjust(per_w)}  "
        f"{qty_h.rjust(qty_w)}  "
        f"{total_h.rjust(tot_w)}"
    )
    data = [row(r[0], r[1], r[2], r[3]) for r in rows]
    return "\n".join(["```", header, *data, "```"])


def _rounding_note(items: list, cantidad: float, mode: str) -> str:
    """Explica el redondeo a unidades completas cuando el area pedida no divide exacto.

    Ej: para 20 m² de una ventana de 4,5 m² c/u se necesitan 5 unidades
    (5 x 4,5 = 22,5 m²). Solo aplica al modo area con APUs UN dimensionados.
    """
    if mode != "area":
        return ""
    rounded = []
    for it in items:
        area = it.get("area_m2")
        if it["unidad"] == "UN" and area:
            real = round(it["units"] * area, 3)
            if abs(real - cantidad) > 0.01:
                rounded.append(
                    f"la {it['descripcion']} ({_format_area(area)} m² c/u) necesita "
                    f"{_cantidad_text(it['units'])} unidades, que suministran "
                    f"{_format_area(real)} m²"
                )
    if not rounded:
        return ""
    return (
        f"_Nota: para cubrir exactamente {_format_area(cantidad)} m², las cantidades "
        f"se redondean a unidades completas: {'; '.join(rounded)}._"
    )


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
