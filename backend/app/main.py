from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.routes.interviews import router as interview_router
from app.api.routes.health import router as health_router

app = FastAPI(
    title="Air-Gapped AI Interviewer System",
    description="Local-first interview workflow using Ollama, Faster-Whisper, and pyttsx3.",
    version="1.0.0"
)

# CORS setup for local React dev server
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include Routers
app.include_router(interview_router)
app.include_router(health_router)