import os
from pathlib import Path
from dotenv import load_dotenv

# Force load .env from the same folder as this file
BASE_DIR = Path(__file__).resolve().parent
ENV_FILE = BASE_DIR / ".env"

# Load it explicitly BEFORE anything else
load_dotenv(dotenv_path=ENV_FILE, override=True)

from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    PORT: int = 8000
    MONGODB_URI: str = "mongodb://localhost:27017/pdf_chatbot"
    JWT_SECRET: str = "change-this-secret"
    JWT_EXPIRE_HOURS: int = 168
    OPENROUTER_API_KEY: str = ""
    HUGGINGFACE_API_KEY: str = ""
    MAX_FILE_SIZE_MB: int = 5
    CHUNK_SIZE_WORDS: int = 800
    CHUNK_OVERLAP_WORDS: int = 100
    ALLOWED_ORIGINS: str = "http://localhost:3000,http://localhost:5173"

    @property
    def origins(self) -> List[str]:
        if self.ALLOWED_ORIGINS.strip() == "*":
            return ["*"]
        return [o.strip() for o in self.ALLOWED_ORIGINS.split(",")]

    class Config:
        env_file = str(BASE_DIR / ".env")
        env_file_encoding = "utf-8"
        extra = "ignore"


settings = Settings()

# Debug: print key status on startup
import logging
logger = logging.getLogger(__name__)

key = settings.OPENROUTER_API_KEY
if key and len(key) > 10:
    logger.info(f"✅ OpenRouter API key loaded: {key[:12]}...{key[-4:]}")
else:
    logger.warning("❌ OpenRouter API key NOT loaded — check your .env file")