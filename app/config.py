import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    # MySQL Configuration
    MYSQL_HOST = os.getenv("MYSQL_HOST", "localhost")
    MYSQL_PORT = int(os.getenv("MYSQL_PORT", "3306"))
    MYSQL_USER = os.getenv("MYSQL_USER", "root")
    MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", "")
    MYSQL_DATABASE = os.getenv("MYSQL_DATABASE", "bot_enterprise")
    
    DATABASE_URL = f"mysql+aiomysql://{MYSQL_USER}:{MYSQL_PASSWORD}@{MYSQL_HOST}:{MYSQL_PORT}/{MYSQL_DATABASE}?charset=utf8mb4"
    
    # Groq
    GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
    GROQ_MODEL = os.getenv("GROQ_MODEL", "llama3-70b-8192")
    GROQ_WHISPER_MODEL = "whisper-large-v3"
    
    # WhatsApp Meta
    META_API_VERSION = "v18.0"
    META_ACCESS_TOKEN = os.getenv("META_ACCESS_TOKEN", "")
    META_PHONE_NUMBER_ID = os.getenv("META_PHONE_NUMBER_ID", "")
    
    # Security
    SECRET_KEY = os.getenv("SECRET_KEY", "change-me-in-production")
    ALGORITHM = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES = 480
    
    # Limits
    MAX_MESSAGE_LENGTH = 10000
    MAX_CONTEXT_MESSAGES = 10
    RATE_LIMIT_PER_USER_PER_MINUTE = 10
    DAILY_COST_LIMIT_PER_COMPANY = 10.0
    MAX_AUDIO_SIZE_MB = 10
    MAX_IMAGE_SIZE_MB = 5
    
    # Webhook
    WHATSAPP_VERIFY_TOKEN = os.getenv("WHATSAPP_VERIFY_TOKEN", "1234")
    
    # Redis
    REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    
    # Model Costs (USD)
    MODEL_COSTS = {
        "llama3-70b-8192": {"input": 0.00000027, "output": 0.00000027},
        "llama3-8b-8192": {"input": 0.00000013, "output": 0.00000013},
        "mixtral-8x7b-32768": {"input": 0.00000024, "output": 0.00000024},
    }
    
    MODEL_PRIORITY = ["llama3-70b-8192", "llama3-8b-8192", "mixtral-8x7b-32768"]


config = Config()
