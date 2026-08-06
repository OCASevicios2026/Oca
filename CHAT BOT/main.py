"""API principal del chatbot de OCA (WhatsApp via YCloud).

Despliegue: Railway ejecuta `uvicorn main:app`.
"""

import asyncio
import hashlib
import hmac
import logging
from contextlib import asynccontextmanager

from fastapi import BackgroundTasks, FastAPI, Header, HTTPException, Request, Response
from sqlalchemy import select

import chatbot
import models
import ycloud_client
from config import settings
from database import Base, SessionLocal, engine

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("oca-chatbot")


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    logger.info("Tablas verificadas. OCA Chatbot listo.")
    yield


app = FastAPI(title="OCA WhatsApp Chatbot", version="1.0.0", lifespan=lifespan)


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


def _send_sync(phone: str, body: str, conversation_id: int | None = None) -> None:
    """Envía un mensaje (async) dentro de un hilo de BackgroundTasks."""
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

        text = _inbound_text(msg)
        db.add(
            models.Message(
                conversation_id=conversation.id,
                direction="in",
                content=text or f"[{msg.get('type')}]",
                wamid=wamid,
            )
        )

        if text is None:
            db.commit()
            logger.info("Mensaje no-texto ignorado de %s", phone)
            return

        result = chatbot.handle_inbound(
            text, conversation.state, conversation.customer_name
        )

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
