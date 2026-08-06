import httpx
import logging

from config import settings

logger = logging.getLogger("oca-chatbot")
YCLOUD_BASE_URL = "https://api.ycloud.com/v2"


async def send_text(to: str, body: str) -> dict | None:
    """Envia un mensaje de texto por WhatsApp usando la API de YCloud."""
    payload = {
        "from": settings.whatsapp_business_phone,
        "to": to,
        "type": "text",
        "text": {"body": body},
    }
    async with httpx.AsyncClient(timeout=20) as client:
        response = await client.post(
            f"{YCLOUD_BASE_URL}/whatsapp/messages/sendDirectly",
            headers={"X-API-Key": settings.ycloud_api_key},
            json=payload,
        )
        logger.info(
            "YCloud send_text status=%s to=%s from=%s response=%s",
            response.status_code,
            to,
            settings.whatsapp_business_phone,
            response.text,
        )
        if response.status_code >= 400:
            raise RuntimeError(f"YCloud error {response.status_code}: {response.text}")
        return response.json()


async def download_media(message_id: str) -> bytes:
    """Descarga el archivo de un mensaje multimedia entrante (imagen, audio, PDF).

    Flujo de la API de YCloud:
    1. GET /whatsapp/messages/{messageID}/media devuelve metadatos y un enlace.
    2. Se descarga el binario desde ese enlace firmado.
    """
    async with httpx.AsyncClient(timeout=30) as client:
        meta = await client.get(
            f"{YCLOUD_BASE_URL}/whatsapp/messages/{message_id}/media",
            headers={"X-API-Key": settings.ycloud_api_key},
        )
        if meta.status_code >= 400:
            raise RuntimeError(f"YCloud media meta error {meta.status_code}: {meta.text}")
        data = meta.json()
        link = data.get("link") or data.get("url")
        if not link:
            raise RuntimeError(f"YCloud media response without link: {data}")

        file_resp = await client.get(link)
        if file_resp.status_code >= 400:
            raise RuntimeError(f"YCloud media download error {file_resp.status_code}")
        return file_resp.content
