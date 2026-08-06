# OCA WhatsApp Chatbot

Chatbot de WhatsApp para **OCA Servicios Integrales S.A.S.** (Santa Marta, Colombia).
Responde mensajes entrantes con un menú de los 9 servicios, entrega información de
contacto y registra leads de cotización en **PostgreSQL**.

- Mensajería WhatsApp: [YCloud](https://www.ycloud.com) (WhatsApp Business API, Meta BSP)
- Backend: Python + FastAPI
- Base de datos: PostgreSQL (SQLAlchemy)
- Hosting: [Railway](https://railway.com/)

## Cómo funciona

```
Usuario WhatsApp  →  YCloud (webhook)  →  /webhook (FastAPI)  →  chatbot.py (lógica)
                                                                    │
                                                                    ├─ PostgreSQL (conversaciones, mensajes, leads)
                                                                    └─ YCloud sendDirectly → respuesta al usuario
```

El webhook responde `200` de inmediato y el procesamiento ocurre en segundo plano.
Se verifica la firma `YCloud-Signature` de cada evento.

## Estructura

```
CHAT BOT/
├── main.py            # API FastAPI + webhook + verificación de firma
├── chatbot.py         # Lógica de conversación (menú, intentos, flujo de cotización)
├── ycloud_client.py   # Cliente de la API de YCloud (envío de mensajes)
├── config.py          # Variables de entorno (pydantic-settings)
├── database.py        # Motor y sesión SQLAlchemy
├── models.py          # Tablas: conversations, messages, leads
├── requirements.txt
├── Procfile
├── railway.json
└── .env.example
```

## 1. Requisitos en YCloud

1. Crea una cuenta en https://www.ycloud.com y configura una cuenta de **WhatsApp Business API**
   con el número de OCA (p. ej. 317 400 4016).
2. Genera una **API Key** en *Settings → API Keys*.
3. Crea un **Webhook endpoint** en *Developer → Webhooks* con:
   - URL: `https://TU-APP.up.railway.app/webhook`
   - Eventos: `whatsapp.inbound_message.received`
   - Guarda el **secret** que te muestre (se usa para firmar los eventos).

## 2. Despliegue en Railway

1. Sube esta carpeta a un repositorio de Git y conéctalo a Railway (New Project → Deploy from repo).
2. Agrega PostgreSQL: `railway add --plugin postgresql` (Railway inyecta `DATABASE_URL` automáticamente).
3. Configura las variables de entorno:

| Variable | Descripción |
|---|---|
| `YCLOUD_API_KEY` | API Key de YCloud |
| `YCLOUD_WEBHOOK_SECRET` | Secret del webhook de YCloud |
| `WHATSAPP_BUSINESS_PHONE` | Número de WhatsApp de OCA en formato E.164, ej. `+573174004016` |
| `LEAD_NOTIFY_PHONE` | *(Opcional)* Número que recibe la notificación de cada lead, ej. `+573174004016` |

4. Deploy. La app arranca sola (Procfile / railway.json): `uvicorn main:app --host 0.0.0.0 --port $PORT`.
5. Verifica el health check: `https://TU-APP.up.railway.app/health`.
6. En YCloud apunta el webhook a tu dominio de Railway y envía un mensaje de prueba a tu número.

## 3. Pruebas locales

```bash
cd "CHAT BOT"
python -m venv .venv
.venv\Scripts\activate            # Windows
pip install -r requirements.txt
copy .env.example .env            # llenar con tus credenciales
uvicorn main:app --reload
```

Para que YCloud te alcance localmente usa un túnel (`ngrok http 8000`) y apunta el
webhook a la URL `https://xxxx.ngrok.app/webhook`.

## Comportamiento del bot

- `1` – `9`: detalle del servicio y oferta de cotización.
- `0` / *asesor*: enlaza con un asesor (pide nombre y descripción del proyecto).
- *servicios* / *menu*: muestra el menú principal.
- *contacto* / *horario*: información de la empresa (teléfono, dirección, NIT).
- *cotizar*: detecta el servicio en el texto y arranca el flujo de cotización.

Cada cotización finaliza en la tabla `leads` y, si configuraste `LEAD_NOTIFY_PHONE`,
se notifica por WhatsApp al número de la empresa.
