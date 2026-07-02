"""
Servicio de integración con Groq (LLaMA 3, Whisper)
"""
from groq import AsyncGroq
from tenacity import retry, stop_after_attempt, wait_exponential
from app.config import config
import logging
import httpx
import tempfile
import os

logger = logging.getLogger(__name__)


class GroqService:
    def __init__(self):
        self.client = AsyncGroq(api_key=config.GROQ_API_KEY)
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    async def chat_completion(self, messages: list, temperature: float = 0.7, max_tokens: int = 500):
        """Chat completion con Groq (LLaMA 3)"""
        try:
            response = await self.client.chat.completions.create(
                model=config.GROQ_MODEL,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens
            )
            return {
                "content": response.choices[0].message.content,
                "tokens": response.usage.total_tokens,
                "model": config.GROQ_MODEL
            }
        except Exception as e:
            logger.error(f"Error en chat completion: {str(e)}")
            raise
    
    async def transcribe_audio(self, audio_url: str) -> str:
        """Transcribir audio con Whisper (Groq) - Ultra rápido"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(audio_url, timeout=30)
                temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".ogg")
                temp_file.write(response.content)
                temp_file.close()
            
            try:
                with open(temp_file.name, "rb") as f:
                    transcription = await self.client.audio.transcriptions.create(
                        file=(os.path.basename(temp_file.name), f),
                        model="whisper-large-v3",
                        language="es",
                        response_format="text"
                    )
                logger.info(f"🎤 Audio transcrito: {transcription[:100]}")
                return transcription
            finally:
                os.unlink(temp_file.name)
        except Exception as e:
            logger.error(f"Error en transcripción: {str(e)}")
            return "[Hubo un error al procesar el audio]"
    
    async def analyze_image(self, image_url: str, prompt: str = "Describe esta imagen") -> str:
        """Análisis de imagen con visión"""
        try:
            response = await self.client.chat.completions.create(
                model="llama-3.2-11b-vision-preview",
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {"type": "image_url", "image_url": {"url": image_url}}
                        ]
                    }
                ]
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"Error en análisis de imagen: {str(e)}")
            return "No pude procesar la imagen"


groq_service = GroqService()
