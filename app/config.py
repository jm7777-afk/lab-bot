import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./data/bot.db")
    GROQ_API_KEY = os.getenv("GROQ_API_KEY")
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    SECRET_KEY = os.getenv("SECRET_KEY", "change-me-in-production")
    WHATSAPP_TOKEN = os.getenv("WHATSAPP_TOKEN")
    WHATSAPP_VERIFY_TOKEN = os.getenv("WHATSAPP_VERIFY_TOKEN")

    MAX_MESSAGE_LENGTH = 10000
    MAX_CONTEXT_MESSAGES = 8
    RATE_LIMIT_PER_USER_PER_MINUTE = 10
    DAILY_COST_LIMIT_PER_COMPANY = 5.0

    MODEL_COSTS = {
        "llama3-70b-8192": {"input": 0.00000027, "output": 0.00000027},
        "mixtral-8x7b-32768": {"input": 0.00000024, "output": 0.00000024},
        "gpt-4o-mini": {"input": 0.00000015, "output": 0.00000060},
    }

    MODEL_PRIORITY = ["llama3-70b-8192", "mixtral-8x7b-32768", "gpt-4o-mini"]


config = Config()
