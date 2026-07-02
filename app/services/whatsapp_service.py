"""
Servicio WhatsApp - Integración con Meta API
"""
import httpx
from app.config import config
import logging
import json

logger = logging.getLogger(__name__)


class WhatsAppService:
    def __init__(self):
        self.base_url = f"https://graph.facebook.com/{config.META_API_VERSION}"
        self.headers = {
            "Authorization": f"Bearer {config.META_ACCESS_TOKEN}",
            "Content-Type": "application/json"
        }
    
    async def send_text(self, to_number: str, text: str, phone_number_id: str = None):
        """Enviar mensaje de texto a WhatsApp"""
        try:
            phone_id = phone_number_id or config.META_PHONE_NUMBER_ID
            
            data = {
                "messaging_product": "whatsapp",
                "to": to_number,
                "type": "text",
                "text": {"body": text[:1500]}
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/{phone_id}/messages",
                    headers=self.headers,
                    json=data,
                    timeout=10
                )
                logger.info(f"📤 Mensaje enviado a {to_number}: {response.status_code}")
                return response.json()
        except Exception as e:
            logger.error(f"Error enviando texto: {str(e)}")
            raise
    
    async def send_image(self, to_number: str, image_url: str, caption: str = None):
        """Enviar imagen a WhatsApp"""
        try:
            phone_id = config.META_PHONE_NUMBER_ID
            
            data = {
                "messaging_product": "whatsapp",
                "to": to_number,
                "type": "image",
                "image": {"link": image_url}
            }
            if caption:
                data["image"]["caption"] = caption
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/{phone_id}/messages",
                    headers=self.headers,
                    json=data,
                    timeout=10
                )
                logger.info(f"🖼️ Imagen enviada a {to_number}: {response.status_code}")
                return response.json()
        except Exception as e:
            logger.error(f"Error enviando imagen: {str(e)}")
            raise
    
    async def send_buttons(self, to_number: str, body: str, buttons: list):
        """Enviar mensaje interactivo con botones"""
        try:
            phone_id = config.META_PHONE_NUMBER_ID
            
            data = {
                "messaging_product": "whatsapp",
                "to": to_number,
                "type": "interactive",
                "interactive": {
                    "type": "button",
                    "body": {"text": body},
                    "action": {
                        "buttons": [
                            {"type": "reply", "reply": {"id": btn["id"], "title": btn["title"]}}
                            for btn in buttons[:3]  # Máximo 3 botones
                        ]
                    }
                }
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/{phone_id}/messages",
                    headers=self.headers,
                    json=data,
                    timeout=10
                )
                logger.info(f"🔘 Botones enviados a {to_number}: {response.status_code}")
                return response.json()
        except Exception as e:
            logger.error(f"Error enviando botones: {str(e)}")
            raise


whatsapp_service = WhatsAppService()
