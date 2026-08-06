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
