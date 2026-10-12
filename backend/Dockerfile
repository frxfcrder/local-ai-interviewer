# Local AI Interviewer — backend
# Build from repo root:  docker build -f backend/Dockerfile -t local-ai-interviewer ./backend
# Run (Ollama stays on the host): docker run -p 8000:8000 --env-file .env local-ai-interviewer
#   On Docker Desktop, point OLLAMA_HOST to http://host.docker.internal:11434
FROM python:3.14-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

# System libs: ffmpeg (faster-whisper/av audio decode), espeak-ng (pyttsx3 TTS)
RUN apt-get update && apt-get install -y --no-install-recommends \
        ffmpeg \
        espeak-ng \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /code

COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

COPY app/ ./app/

RUN mkdir -p storage/audio storage/temp

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
