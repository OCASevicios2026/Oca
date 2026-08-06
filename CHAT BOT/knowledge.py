"""Datos de negocio de OCA Servicios Integrales S.A.S.

Este modulo centraliza la informacion de la empresa y el catalogo de servicios
para que pueda ser reutilizada tanto por la logica por reglas (chatbot.py) como
por el prompt de sistema de Gemini (prompts.py) sin imports circulares.
"""

# Catalogo de los 9 servicios con descripcion e items
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
