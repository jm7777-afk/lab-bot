import logging

from groq import AsyncGroq
from openai import AsyncOpenAI
from tenacity import retry, stop_after_attempt, wait_exponential

from app.config import config
from app.services.rate_limiter import rate_limiter

logger = logging.getLogger(__name__)


class LLMService:
    def __init__(self):
        self.groq_client = AsyncGroq(api_key=config.GROQ_API_KEY) if config.GROQ_API_KEY else None
        self.openai_client = AsyncOpenAI(api_key=config.OPENAI_API_KEY) if config.OPENAI_API_KEY else None

    @retry(stop=stop_after_attempt(2), wait=wait_exponential(multiplier=1, min=2, max=10))
    async def generate_response(self, company_id: int, messages: list, model_override: str | None = None, company_config: dict | None = None):
        company_config = company_config or {}

        if company_config.get("is_running") is False:
            return {
                "content": "⚠️ El bot está desactivado para esta empresa. Contacta al administrador para reactivarlo.",
                "model": "disabled",
                "cost_usd": 0,
                "tokens_used": 0,
            }

        system_prompt = company_config.get("system_prompt")
        temperature = float(company_config.get("temperature", 0.7))

        prepared_messages = list(messages)
        if system_prompt:
            prepared_messages = [{"role": "system", "content": str(system_prompt)}] + prepared_messages

        configured_model = model_override or company_config.get("model")
        models = [configured_model] if configured_model and configured_model in config.MODEL_COSTS else config.MODEL_PRIORITY

        for model_name in models:
            if model_name not in config.MODEL_COSTS:
                continue

            estimated_tokens = max(1, sum(len(str(message.get("content", ""))) for message in prepared_messages) // 4)
            estimated_cost = estimated_tokens * config.MODEL_COSTS[model_name]["input"] / 1_000_000

            if not rate_limiter.check_company_cost(company_id, estimated_cost):
                return {
                    "content": "⚠️ Se ha alcanzado el límite diario de uso para esta empresa. Contacta al administrador.",
                    "model": "blocked",
                    "cost_usd": 0,
                    "tokens_used": 0,
                }

            try:
                response = await self._call_model(model_name, prepared_messages, temperature)
                real_cost = response["tokens_used"] * config.MODEL_COSTS[model_name]["input"] / 1_000_000
                rate_limiter.add_cost(company_id, real_cost)
                return {
                    "content": response["content"],
                    "model": model_name,
                    "cost_usd": real_cost,
                    "tokens_used": response["tokens_used"],
                }
            except Exception as exc:
                logger.warning("Fallo en modelo %s: %s", model_name, exc)
                continue

        return {
            "content": "Lo siento, el servicio de IA no está disponible temporalmente. Intenta más tarde.",
            "model": "offline_fallback",
            "cost_usd": 0,
            "tokens_used": 0,
        }

    async def _call_model(self, model_name: str, messages: list, temperature: float):
        if "llama" in model_name or "mixtral" in model_name:
            if self.groq_client is None:
                raise RuntimeError("GROQ_API_KEY no configurada")
            result = await self.groq_client.chat.completions.create(
                model=model_name,
                messages=messages,
                temperature=temperature,
                max_tokens=500,
            )
            return {
                "content": result.choices[0].message.content,
                "tokens_used": getattr(result.usage, "total_tokens", 0),
            }

        if self.openai_client is None:
            raise RuntimeError("OPENAI_API_KEY no configurada")

        result = await self.openai_client.chat.completions.create(
            model=model_name,
            messages=messages,
            temperature=temperature,
            max_tokens=500,
        )
        return {
            "content": result.choices[0].message.content,
            "tokens_used": getattr(result.usage, "total_tokens", 0),
        }


llm_service = LLMService()
