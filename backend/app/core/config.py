from pathlib import Path

from dotenv import load_dotenv
import os

# backend/app/core/config.py -> parents[3] = repo root (where .env lives)
ROOT = Path(__file__).resolve().parents[3]
load_dotenv(ROOT / ".env")


class Config:
    """Application configuration (reads repo-root .env)."""

    # FastAPI server
    API_PORT = os.getenv("API_PORT", "8000")
    APP_URL = os.getenv("APP_URL", f"http://localhost:{os.getenv('API_PORT', '8000')}")
    # Backwards compat: main.py uses config.app_url (lowercase)
    app_url = APP_URL

    # Database (psycopg3). No fallback — fail fast if .env is missing
    # so no credentials ever live in code.
    DATABASE_URL = os.getenv("DATABASE_URL")
    if not DATABASE_URL:
        raise RuntimeError(
            "DATABASE_URL is not set. Copy .env.example to .env "
            "or set DATABASE_URL in the environment."
        )

    # Ollama / LLM
    OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
    LLM_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2")
    OLLAMA_CLIENT = {"url": OLLAMA_HOST}

    # Audio services
    TTS_ENGINE = "pyttsx3"
    TTS_VOICE = os.getenv("TTS_VOICE", "Zira")
    STT_MODEL = None  # Can be overridden in stt_service

    # Auth / JWT
    SECRET_KEY = os.getenv("SECRET_KEY", "change-me-to-a-long-random-secret")
    ALGORITHM = os.getenv("ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))

    # Env
    ENV = os.getenv("ENV", "development")
    DEBUG = os.getenv("DEBUG", "True").lower() in ("1", "true", "yes")
