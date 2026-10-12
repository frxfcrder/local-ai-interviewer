import asyncio

import httpx
from fastapi import APIRouter
from sqlalchemy import text

from app.core.config import Config
from app.db.session import engine

router = APIRouter(tags=["System Health"])


async def _ollama_ok() -> bool:
    try:
        async with httpx.AsyncClient(timeout=2.0) as client:
            response = await client.get(f"{Config.OLLAMA_HOST}/api/tags")
            return response.status_code == 200
    except Exception:
        return False


async def _db_ok() -> bool:
    def _probe() -> bool:
        try:
            with engine.connect() as conn:
                conn.scalar(text("SELECT 1"))
                return True
        except Exception:
            return False

    return await asyncio.to_thread(_probe)


@router.get("/health")
async def health_check():
    llm_ok, db_ok = await asyncio.gather(_ollama_ok(), _db_ok())
    services = {
        "llm": "connected" if llm_ok else "unreachable",
        "stt": "ready",
        "tts": "ready",
        "db": "connected" if db_ok else "unreachable",
    }
    healthy = llm_ok and db_ok
    return {
        "status": "ok" if healthy else "degraded",
        "system": "air-gapped",
        "services": services,
    }
