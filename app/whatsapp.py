import httpx
import os
import logging

logger = logging.getLogger(__name__)

ZAPI_INSTANCE = os.getenv("ZAPI_INSTANCE_ID")
ZAPI_TOKEN    = os.getenv("ZAPI_TOKEN")
ZAPI_BASE     = f"https://api.z-api.io/instances/{ZAPI_INSTANCE}/token/{ZAPI_TOKEN}"

HEADERS = {"Content-Type": "application/json"}


async def send_message(phone: str, text: str):
    """Envia mensagem de texto."""
    url = f"{ZAPI_BASE}/send-text"
    payload = {"phone": phone, "message": text}
    async with httpx.AsyncClient(timeout=15) as client:
        r = await client.post(url, json=payload, headers=HEADERS)
        if r.status_code != 200:
            logger.error(f"Erro Z-API send-text: {r.text}")
        return r.json()


async def download_image(message: dict) -> str | None:
    """Extrai base64 da imagem recebida via webhook Z-API."""
    try:
        image = message.get("image", {})
        return image.get("imageBase64") or image.get("base64")
    except Exception as e:
        logger.error(f"Erro ao extrair imagem: {e}")
        return None
