import asyncio
import json
import logging
import os
import uuid
import shutil
from functools import lru_cache
from typing import List
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, Response, status
from fastapi.responses import StreamingResponse, FileResponse
from sqlalchemy.orm import Session

from app.core.config import Config
from app.db.session import get_db
from app.prompts.interviewer import get_interviewer_prompt
from app.schemas.interview import (
    ChatMessage,
    EvaluateRequest,
    GreetResponse,
    InterviewChatRequest,
    InterviewCreate,
    InterviewResponse,
    SessionRoleUpdate,
    TranscriptionResponse,
    SpeechSynthesizeRequest,
    SpeechSynthesizeResponse
)
from app.schemas.message import MessageCreate, MessageResponse
from app.services.interview_service import DEFAULT_ROLE, InterviewService
from app.services.llm_service import LLMService
from app.services.stt_service import STTService
from app.services.tts_service import TTSService
from app.services.evaluation_service import EvaluationService


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/interview", tags=["Interview Core"])

AUDIO_DIR = "storage/audio"
TEMP_DIR = "storage/temp"

# Dependency Injections (cached singletons — STT especially must not
# reload the Whisper model on every request)
@lru_cache(maxsize=1)
def get_llm_service() -> LLMService:
    return LLMService(base_url=Config.OLLAMA_HOST, model_name=Config.LLM_MODEL)

@lru_cache(maxsize=1)
def get_stt_service() -> STTService:
    # Uses local Whisper instance
    return STTService(model_size="base")

@lru_cache(maxsize=1)
def get_tts_service() -> TTSService:
    return TTSService(output_dir=AUDIO_DIR, voice=Config.TTS_VOICE)

def get_eval_service() -> EvaluationService:
    return EvaluationService(llm_service=get_llm_service())


def get_interview_service(db: Session = Depends(get_db)) -> InterviewService:
    return InterviewService(db)


def _safe_audio_path(filename: str) -> str:
    """Resolve filename inside AUDIO_DIR, blocking path traversal."""
    base = os.path.realpath(AUDIO_DIR)
    path = os.path.realpath(os.path.join(base, os.path.basename(filename)))
    if path != base and not path.startswith(base + os.sep):
        raise HTTPException(status_code=400, detail="Invalid filename")
    return path


# --- Endpoint 1: LLM Streaming Chat (valid SSE framing) ---
@router.post("/chat/stream")
async def chat_stream(
    request: InterviewChatRequest,
    llm_service: LLMService = Depends(get_llm_service),
    service: InterviewService = Depends(get_interview_service),
):
    """
    Streams the LLM response as Server-Sent Events:
    `data: {"content": "<chunk>"}` frames followed by `data: [DONE]`.
    When `interview_id` is set, the latest user turn and the full
    assistant reply are persisted to that session.
    """
    formatted_messages = [msg.model_dump() for msg in request.messages]
    # Ground the model: role-aware system prompt + brevity rules. The routes
    # previously sent raw history with no system message, so replies drifted
    # and ballooned (452 → 2350 chars observed). Skip if caller set its own.
    session = None
    if request.interview_id is not None:
        session = service.get_session(request.interview_id)
        if session is None:
            raise HTTPException(status_code=404, detail="Interview session not found")
        # First answer in a role-less session names the target: extract it so
        # the rest of the interview (and the greeting follow-up) is grounded.
        if session.role_type == DEFAULT_ROLE:
            first_answers = [m for m in request.messages if m.role == "user"]
            if first_answers:
                extracted = await llm_service.extract_role(first_answers[-1].content)
                if extracted:
                    session = service.set_role(session.id, extracted)
    if not formatted_messages or formatted_messages[0].get("role") != "system":
        role = session.role_type if session is not None else "Software Engineer"
        formatted_messages.insert(
            0, {"role": "system", "content": get_interviewer_prompt(role)}
        )

    if request.interview_id is None:
        async def _anonymous_stream():
            async for chunk in llm_service.stream_response(formatted_messages):
                yield f"data: {json.dumps({'content': chunk})}\n\n"
            yield "data: [DONE]\n\n"

        return StreamingResponse(_anonymous_stream(), media_type="text/event-stream")

    user_turns = [msg for msg in request.messages if msg.role == "user"]
    if user_turns:
        service.add_message(
            interview_id=request.interview_id,
            sender="candidate",
            transcript=user_turns[-1].content,
        )

    async def _persisted_stream():
        chunks: List[str] = []
        try:
            async for chunk in llm_service.stream_response(formatted_messages):
                chunks.append(chunk)
                yield f"data: {json.dumps({'content': chunk})}\n\n"
        finally:
            text = "".join(chunks).strip()
            if text:
                try:
                    service.add_message(
                        interview_id=request.interview_id,
                        sender="interviewer",
                        transcript=text,
                    )
                except Exception:
                    logger.warning("failed to persist assistant turn", exc_info=True)
        yield "data: [DONE]\n\n"

    return StreamingResponse(_persisted_stream(), media_type="text/event-stream")


# --- Endpoint 2: STT Speech-to-Text Transcription ---
@router.post("/transcribe", response_model=TranscriptionResponse)
async def transcribe_audio(
    file: UploadFile = File(...),
    stt_service: STTService = Depends(get_stt_service)
):
    """
    Accepts candidate audio uploads (.wav, .mp3, .m4a), saves them temporarily,
    and transcribes the audio using Faster-Whisper.
    """
    allowed_extensions = (".wav", ".mp3", ".m4a", ".webm")
    original_name = file.filename or "upload"
    if not original_name.lower().endswith(allowed_extensions):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid audio format. Allowed: .wav, .mp3, .m4a, .webm"
        )

    # Save uploaded file temporarily (basename only: no directory traversal)
    os.makedirs(TEMP_DIR, exist_ok=True)

    unique_filename = f"{uuid.uuid4()}_{os.path.basename(original_name)}"
    temp_file_path = os.path.join(TEMP_DIR, unique_filename)

    try:
        with open(temp_file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # Transcribe audio via STT Service (blocking/CPU-bound: run off the loop)
        transcript = await asyncio.to_thread(stt_service.transcribe, temp_file_path)

        return TranscriptionResponse(
            transcript=transcript,
            filename=os.path.basename(original_name)
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Transcription failed: {str(e)}"
        )
    finally:
        # Cleanup temporary audio file
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)


# --- Endpoint 3: TTS Text-to-Speech Synthesis ---
@router.post("/synthesize", response_model=SpeechSynthesizeResponse)
async def synthesize_speech(
    request: SpeechSynthesizeRequest,
    tts_service: TTSService = Depends(get_tts_service)
):
    """
    Synthesizes textual output into a local wav audio file using pyttsx3.
    """
    try:
        # Generate audio file (blocking: run off the loop; basename only).
        # Unique name per turn unless the client asked for a specific file —
        # otherwise every reply would overwrite a single wav.
        if request.output_filename:
            target_name = os.path.basename(request.output_filename)
        else:
            target_name = f"interviewer_{uuid.uuid4().hex}.wav"
        generated_path = await asyncio.to_thread(
            tts_service.synthesize_to_file,
            request.text,
            target_name,
        )

        # Relative stream URL
        filename = os.path.basename(generated_path)
        audio_url = f"/api/interview/audio/{filename}"

        return SpeechSynthesizeResponse(audio_url=audio_url)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Speech synthesis failed: {str(e)}"
        )


# --- Endpoint 4: Serve Generated Audio ---
@router.get("/audio/{filename}")
async def get_audio_file(filename: str):
    """
    Retrieves synthesized audio files from disk.
    """
    file_path = _safe_audio_path(filename)
    if not os.path.isfile(file_path):
        raise HTTPException(status_code=404, detail="Audio file not found")

    return FileResponse(file_path, media_type="audio/wav", filename=os.path.basename(file_path))


@router.delete("/audio/{filename}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_audio_file(filename: str):
    """
    Deletes a synthesized audio file (lets clients clean up after playback).
    """
    file_path = _safe_audio_path(filename)
    if not os.path.isfile(file_path):
        raise HTTPException(status_code=404, detail="Audio file not found")
    os.remove(file_path)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/evaluate")
async def evaluate_candidate(
    body: EvaluateRequest,
    eval_service: EvaluationService = Depends(get_eval_service)
):
    """
    Generates a post-interview performance evaluation report based on chat transcript.
    """
    try:
        formatted_history = [msg.model_dump() for msg in body.chat_history]
        chunks = [
            chunk async for chunk in eval_service.generate_evaluation(formatted_history)
        ]
        return {"evaluation": "".join(chunks)}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Evaluation failed: {str(e)}")


# --- Interview Session Persistence ---
@router.post("/sessions", response_model=InterviewResponse, status_code=status.HTTP_201_CREATED)
async def create_interview_session(
    body: InterviewCreate,
    service: InterviewService = Depends(get_interview_service),
):
    """Creates a persisted interview session."""
    return service.create_session(user_id=body.user_id, role_type=body.role_type)


@router.get("/sessions/{interview_id}", response_model=InterviewResponse)
async def get_interview_session(
    interview_id: uuid.UUID,
    service: InterviewService = Depends(get_interview_service),
):
    """Fetches a single interview session."""
    session = service.get_session(interview_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Interview session not found")
    return session


@router.get("/sessions/{interview_id}/history", response_model=List[MessageResponse])
async def get_interview_history(
    interview_id: uuid.UUID,
    service: InterviewService = Depends(get_interview_service),
):
    """Returns the persisted message history for a session."""
    if service.get_session(interview_id) is None:
        raise HTTPException(status_code=404, detail="Interview session not found")
    return service.get_history(interview_id)


@router.post(
    "/sessions/{interview_id}/messages",
    response_model=MessageResponse,
    status_code=status.HTTP_201_CREATED,
)
async def add_interview_message(
    interview_id: uuid.UUID,
    body: MessageCreate,
    service: InterviewService = Depends(get_interview_service),
):
    """Persists one message turn to a session."""
    if service.get_session(interview_id) is None:
        raise HTTPException(status_code=404, detail="Interview session not found")
    try:
        return service.add_message(
            interview_id=interview_id,
            sender=body.sender,
            transcript=body.transcript,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/sessions/{interview_id}/complete", response_model=InterviewResponse)
async def complete_interview_session(
    interview_id: uuid.UUID,
    service: InterviewService = Depends(get_interview_service),
):
    """Marks a session as completed."""
    session = service.complete_session(interview_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Interview session not found")
    return session


@router.patch("/sessions/{interview_id}", response_model=InterviewResponse)
async def update_interview_role(
    interview_id: uuid.UUID,
    body: SessionRoleUpdate,
    service: InterviewService = Depends(get_interview_service),
):
    """Sets/overrides the target role for a session."""
    session = service.set_role(interview_id, body.role_type)
    if session is None:
        raise HTTPException(status_code=404, detail="Interview session not found")
    return session


@router.post("/sessions/{interview_id}/greet", response_model=GreetResponse)
async def greet_candidate(
    interview_id: uuid.UUID,
    service: InterviewService = Depends(get_interview_service),
    tts_service: TTSService = Depends(get_tts_service),
):
    """Interviewer opens the session: greeting persisted + synthesized in one call."""
    session = service.get_session(interview_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Interview session not found")
    if session.status != "in_progress":
        raise HTTPException(status_code=400, detail="Session is not in progress")

    if session.role_type == DEFAULT_ROLE:
        text = (
            "Hello! I'm your AI interviewer. "
            "What role are you applying for today?"
        )
    else:
        text = (
            f"Hello! I'm your AI interviewer. I see you're here for the "
            f"{session.role_type} role. Are you ready to begin?"
        )
    service.add_message(interview_id=interview_id, sender="interviewer", transcript=text)
    try:
        generated_path = await asyncio.to_thread(
            tts_service.synthesize_to_file,
            text,
            f"greeting_{uuid.uuid4().hex}.wav",
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Speech synthesis failed: {str(e)}",
        )
    filename = os.path.basename(generated_path)
    return GreetResponse(text=text, audio_url=f"/api/interview/audio/{filename}")
