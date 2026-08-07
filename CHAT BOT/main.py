"""API principal del chatbot de OCA (WhatsApp via YCloud).

Despliegue: Railway ejecuta `uvicorn main:app`.
"""

import asyncio
import base64
import hashlib
import hmac
import logging
from contextlib import asynccontextmanager

from fastapi import BackgroundTasks, Depends, FastAPI, Header, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select, text
from sqlalchemy.orm import Session

import chatbot
import groq_client as ai
import memory
import models
import ycloud_client
from config import settings
from database import Base, SessionLocal, engine, get_db

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("oca-chatbot")


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    # Migracion minima (Postgres): columnas del panel en tablas existentes
    if engine.dialect.name == "postgresql":
        with engine.begin() as conn:
            conn.execute(text("ALTER TABLE leads ALTER COLUMN conversation_id DROP NOT NULL"))
            conn.execute(
                text(
                    "ALTER TABLE leads ADD COLUMN IF NOT EXISTS source VARCHAR(20) "
                    "NOT NULL DEFAULT 'whatsapp'"
                )
            )
            conn.execute(
                text(
                    "ALTER TABLE leads ADD COLUMN IF NOT EXISTS status VARCHAR(20) "
                    "NOT NULL DEFAULT 'nuevo'"
                )
            )
    logger.info("Tablas verificadas. OCA Chatbot listo.")
    yield


app = FastAPI(title="OCA WhatsApp Chatbot", version="1.0.0", lifespan=lifespan)

# CORS: permite que la web (panel y formulario) consulte la API del bot
_cors_origins = [o.strip() for o in settings.cors_origins.split(",") if o.strip()]
# El panel local (file://) envia Origin: null; se incluye para poder abrirlo sin servidor web
if "null" not in _cors_origins:
    _cors_origins.append("null")
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)


def verify_signature(raw_body: bytes, header: str | None) -> bool:
    """Valida la firma del webhook de YCloud (dos formatos soportados)."""
    if not settings.ycloud_webhook_secret:
        logger.warning("YCLOUD_WEBHOOK_SECRET vacio: firma no verificada (solo para desarrollo).")
        return True
    if not header:
        return False
    secret = settings.ycloud_webhook_secret.encode()

    if header.startswith("sha256="):
        expected = "sha256=" + hmac.new(secret, raw_body, hashlib.sha256).hexdigest()
        return hmac.compare_digest(expected, header)

    try:
        parts = dict(p.split("=", 1) for p in header.split(","))
        timestamp = parts["t"]
        signature = parts["s"]
    except Exception:
        return False
    expected = hmac.new(
        secret, f"{timestamp}.{raw_body.decode()}".encode(), hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected, signature)


def _normalize_phone(phone: str) -> str:
    phone = phone.strip().replace(" ", "")
    if phone.startswith("+"):
        return phone
    return "+" + phone


def _extract_inbound_message(payload: dict) -> dict:
    msg = payload.get("whatsappInboundMessage")
    if msg is None:
        data = payload.get("data") or {}
        obj = data.get("object") or {}
        msg = obj.get("whatsappInboundMessage")
    return msg or {}


def _inbound_text(msg: dict) -> str | None:
    msg_type = msg.get("type")
    if msg_type == "text":
        return (msg.get("text") or {}).get("body", "")
    if msg_type == "interactive":
        interactive = msg.get("interactive") or {}
        reply = interactive.get("list_reply") or interactive.get("button_reply") or {}
        return reply.get("title") or reply.get("id") or ""
    return None


def _inbound_media(msg: dict) -> dict | None:
    """Extrae la informacion del archivo multimedia entrante, si existe.

    YCloud envia el archivo bajo la clave del tipo de mensaje (image/audio/
    document/video) con un campo ``link`` descargable directamente (requiere
    el header ``X-API-Key``). Devuelve:
    {"link": str, "type": str, "mime": str} o None.
    """
    msg_type = msg.get("type")
    if msg_type not in ("image", "audio", "document", "video"):
        return None
    media_obj = msg.get("media") or msg.get(msg_type) or {}
    link = media_obj.get("link") or media_obj.get("url")
    if not link:
        return None
    return {
        "link": link,
        "type": "audio" if msg_type == "audio" else "image" if msg_type == "image" else "document",
        "mime": media_obj.get("mimeType") or media_obj.get("mime_type") or "",
    }


def _send_sync(phone: str, body: str, conversation_id: int | None = None) -> None:
    """EnvÃ­a un mensaje (async) dentro de un hilo de BackgroundTasks."""
    try:
        asyncio.run(ycloud_client.send_text(phone, body))
        if conversation_id is not None:
            with SessionLocal() as db:
                db.add(
                    models.Message(
                        conversation_id=conversation_id, direction="out", content=body
                    )
                )
                db.commit()
    except Exception:
        logger.exception("Fallo al enviar mensaje a %s", phone)


def _process_event(payload: dict) -> None:
    """Procesa un evento entrante de YCloud (sync para BackgroundTasks)."""
    if payload.get("type") != "whatsapp.inbound_message.received":
        return

    msg = _extract_inbound_message(payload)
    phone_raw = msg.get("from")
    if not phone_raw:
        return
    phone = _normalize_phone(phone_raw)
    wamid = msg.get("wamid") or msg.get("id") or ""

    text = _inbound_text(msg)
    media = _inbound_media(msg)

    # Descarga el archivo multimedia (imagen, nota de voz o PDF) si viene adjunto
    media_bytes: bytes | None = None
    if media:
        try:
            media_bytes = asyncio.run(ycloud_client.download_media(media["link"]))
        except Exception:
            logger.exception("Fallo al descargar media de %s", phone)
            media = None

    with SessionLocal() as db:
        # Idempotencia: ignorar entregas duplicadas del mismo mensaje
        if wamid and db.execute(
            select(models.Message.id).where(models.Message.wamid == wamid).limit(1)
        ).scalar_one_or_none():
            return

        conversation = db.execute(
            select(models.Conversation).where(
                models.Conversation.whatsapp_phone == phone
            )
        ).scalar_one_or_none()
        if conversation is None:
            conversation = models.Conversation(whatsapp_phone=phone)
            db.add(conversation)
            db.flush()

        # Historial previo (excluye el mensaje en curso, aun no guardado)
        history = memory.build_chat_history(conversation.id)

        if text is None:
            content = f"[{msg.get('type')}]"
        else:
            content = text

        db.add(
            models.Message(
                conversation_id=conversation.id,
                direction="in",
                content=content,
                wamid=wamid,
            )
        )

        if text is None and media is None:
            db.commit()
            logger.info("Mensaje no-texto ignorado de %s", phone)
            return

        # Decide la respuesta: reglas primero; Groq para multimedia o
        # cuando el flujo por reglas no reconoce el mensaje (fallback).
        result = None
        if media is not None:
            reply = ai.generate_reply(
                history,
                text or "",
                media_type=media["type"],
                media_bytes=media_bytes,
                media_mime=media["mime"],
            )
            result = {
                "replies": [reply],
                "state": conversation.state,
                "customer_name": conversation.customer_name,
                "lead": None,
            }
        else:
            result = chatbot.handle_inbound(
                text, conversation.state, conversation.customer_name
            )
            if result["replies"] == [chatbot.FALLBACK_REPLY]:
                reply = ai.generate_reply(history, text)
                result = {
                    "replies": [reply],
                    "state": conversation.state,
                    "customer_name": conversation.customer_name,
                    "lead": None,
                }
            elif (
                result["state"].startswith("service:")
                and len(result["replies"]) == 1
                and result["replies"][0] == chatbot.service_detail(result["state"].split(":", 1)[1])
            ):
                # Humanizar el detalle de servicio (tono de asesor) sin romper el flujo
                humanized = ai.humanize_service_reply(
                    result["state"].split(":", 1)[1]
                )
                if humanized:
                    result["replies"] = [humanized]
            elif (
                result["state"] == "menu"
                and len(result["replies"]) == 1
                and result["replies"][0].startswith("¡Hola! Bienvenido a OCA Servicios Integrales.")
            ):
                # Humanizar el saludo inicial: bienvenida natural con los servicios en prosa
                # (solo la primera vez; si el cliente ya tiene historial, se saluda corto)
                returning = bool(history)
                greeting = ai.humanize_greeting(conversation.customer_name, returning=returning)
                if greeting:
                    result["replies"] = [greeting]
            elif (
                result["state"] == "menu"
                and len(result["replies"]) == 1
                and result["replies"][0] == chatbot.build_menu()
            ):
                # Humanizar el menu: respuestas variadas y naturales en vez de texto fijo
                menu_natural = ai.humanize_menu()
                if menu_natural:
                    result["replies"] = [menu_natural]

        conversation.state = result["state"]
        if result.get("customer_name"):
            conversation.customer_name = result["customer_name"]
        if result.get("lead") and result["lead"].get("service"):
            conversation.pending_service = result["lead"]["service"]

        final_lead = result.get("lead")
        lead_service = conversation.pending_service
        if final_lead and final_lead.get("message"):
            lead = models.Lead(
                conversation_id=conversation.id,
                whatsapp_phone=phone,
                customer_name=conversation.customer_name,
                service=lead_service,
                message=final_lead["message"],
                notified=1 if settings.lead_notify_phone else 0,
                source="whatsapp",
                status="nuevo",
            )
            db.add(lead)
            conversation.pending_service = None

        db.commit()

        if settings.lead_notify_phone and final_lead and final_lead.get("message"):
            _send_sync(
                settings.lead_notify_phone,
                chatbot.build_lead_message(
                    phone,
                    conversation.customer_name,
                    lead_service,
                    final_lead["message"],
                ),
            )

        for reply in result["replies"]:
            _send_sync(phone, reply, conversation.id)


@app.get("/")
def root():
    return {"name": "OCA WhatsApp Chatbot", "status": "ok"}


@app.get("/health")
def health():
    return {"status": "ok"}


async def _handle_webhook_request(
    request: Request,
    response: Response,
    background_tasks: BackgroundTasks,
    ycloud_signature: str | None,
):
    """Centraliza la logica del webhook para soportar rutas con y sin slash final."""
    raw_body = await request.body()
    if not verify_signature(raw_body, ycloud_signature):
        raise HTTPException(status_code=401, detail="Invalid signature")

    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON")

    background_tasks.add_task(_process_event, payload)
    response.status_code = 200
    return {"status": "accepted"}


@app.api_route("/webhook", methods=["GET", "HEAD", "OPTIONS", "POST"])
async def webhook(
    request: Request,
    response: Response,
    background_tasks: BackgroundTasks,
    ycloud_signature: str | None = Header(default=None, alias="YCloud-Signature"),
):
    if request.method == "POST":
        return await _handle_webhook_request(request, response, background_tasks, ycloud_signature)
    logger.info("Webhook %s received on GET/HEAD/OPTIONS", request.method)
    return {"status": "ok", "detail": "Webhook endpoint is alive. Send POST for events."}


@app.api_route("/webhook/", methods=["GET", "HEAD", "OPTIONS", "POST"])
async def webhook_slash(
    request: Request,
    response: Response,
    background_tasks: BackgroundTasks,
    ycloud_signature: str | None = Header(default=None, alias="YCloud-Signature"),
):
    if request.method == "POST":
        return await _handle_webhook_request(request, response, background_tasks, ycloud_signature)
    logger.info("Webhook slash %s received on GET/HEAD/OPTIONS", request.method)
    return {"status": "ok", "detail": "Webhook endpoint is alive. Send POST for events."}


# ---------------------------------------------------------------------------
# Panel administrativo de notificaciones
# ---------------------------------------------------------------------------

def _require_admin(authorization: str | None = Header(default=None)):
    """Valida credenciales Basic Auth del panel."""
    if not settings.admin_user or not settings.admin_password:
        raise HTTPException(status_code=503, detail="Panel desactivado: falta ADMIN_USER/ADMIN_PASSWORD")
    if not authorization or not authorization.lower().startswith("basic "):
        raise HTTPException(status_code=401, detail="Se requiere autenticacion")
    try:
        decoded = base64.b64decode(authorization.split(" ", 1)[1]).decode("utf-8")
        user, _, password = decoded.partition(":")
    except Exception:
        raise HTTPException(status_code=401, detail="Credenciales invalidas")
    if user != settings.admin_user or password != settings.admin_password:
        raise HTTPException(status_code=401, detail="Credenciales invalidas")
    return True


@app.post("/api/lead")
async def create_lead_from_web(
    request: Request,
    db: Session = Depends(get_db),
):
    """Recibe solicitudes/cotizaciones desde el formulario de la web."""
    try:
        data = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="JSON invalido")

    phone = str(data.get("telefono") or "").strip()
    name = (data.get("nombre") or "").strip() or None
    service = (data.get("servicio") or "").strip() or None
    message = (data.get("descripcion") or "").strip() or None
    if not phone or (not service and not message):
        raise HTTPException(status_code=400, detail="Faltan datos: telefono y servicio/descripcion")

    lead = models.Lead(
        conversation_id=None,
        whatsapp_phone=phone,
        customer_name=name,
        service=service,
        message=message,
        notified=0,
        source="web",
        status="nuevo",
    )
    db.add(lead)
    db.commit()
    db.refresh(lead)
    logger.info("Nuevo lead web #%s de %s (%s)", lead.id, name or phone, service)
    return {"status": "ok", "id": lead.id}


@app.get("/api/leads")
async def list_leads(db: Session = Depends(get_db), _: bool = Depends(_require_admin)):
    """Lista todas las solicitudes para el panel administrativo."""
    rows = db.execute(
        select(models.Lead).order_by(models.Lead.created_at.desc()).limit(100)
    ).scalars().all()
    return [
        {
            "id": l.id,
            "phone": l.whatsapp_phone,
            "name": l.customer_name,
            "service": l.service,
            "message": l.message,
            "source": l.source,
            "status": l.status,
            "created_at": l.created_at.isoformat() if l.created_at else None,
        }
        for l in rows
    ]


@app.post("/api/leads/{lead_id}/contacted")
async def mark_lead_contacted(
    lead_id: int,
    db: Session = Depends(get_db),
    _: bool = Depends(_require_admin),
):
    """Marca una solicitud como contactada desde el panel."""
    lead = db.get(models.Lead, lead_id)
    if not lead:
        raise HTTPException(status_code=404, detail="Solicitud no encontrada")
    lead.status = "contactado"
    db.commit()
    return {"status": "ok", "id": lead_id}


@app.delete("/api/leads/{lead_id}")
async def delete_lead(
    lead_id: int,
    db: Session = Depends(get_db),
    _: bool = Depends(_require_admin),
):
    """Elimina una solicitud desde el panel."""
    lead = db.get(models.Lead, lead_id)
    if not lead:
        raise HTTPException(status_code=404, detail="Solicitud no encontrada")
    db.delete(lead)
    db.commit()
    return {"status": "ok", "id": lead_id}

