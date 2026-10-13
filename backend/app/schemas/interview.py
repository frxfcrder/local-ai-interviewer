from pydantic import BaseModel, ConfigDict, Field
from typing import List, Optional
from datetime import datetime
import uuid

# --- Interview Session Schemas ---
class InterviewCreate(BaseModel):
    user_id: Optional[uuid.UUID] = Field(default_factory=uuid.uuid4, description="Owning user ID (generated when omitted)")
    role_type: str = Field(..., description="Target role, e.g. 'Senior Backend Engineer'")

class InterviewResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    role_type: str
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

# --- LLM Schemas ---
class ChatMessage(BaseModel):
    role: str = Field(..., description="Role of the speaker: 'system', 'user', or 'assistant'")
    content: str = Field(..., description="Content of the message")

class InterviewChatRequest(BaseModel):
    messages: List[ChatMessage] = Field(..., description="Full conversation context for the interview")
    candidate_id: Optional[str] = Field(None, description="Optional ID tracking candidate session")
    interview_id: Optional[uuid.UUID] = Field(None, description="Persist turns to this session when set")

# --- STT Schemas ---
class TranscriptionResponse(BaseModel):
    transcript: str = Field(..., description="Transcribed audio content")
    filename: str = Field(..., description="Original name of processed file")

# --- TTS Schemas ---
class SpeechSynthesizeRequest(BaseModel):
    text: str = Field(..., description="Text content to synthesize into speech")
    output_filename: Optional[str] = Field(None, description="Target audio file name (generated when omitted)")

class SpeechSynthesizeResponse(BaseModel):
    audio_url: str = Field(..., description="Relative path or URL to access the generated audio file")

# --- Greeting Schemas ---
class GreetResponse(BaseModel):
    text: str = Field(..., description="Greeting spoken by the interviewer")
    audio_url: str = Field(..., description="Relative path or URL to access the greeting audio")

# --- Evaluation Schemas ---
class EvaluateRequest(BaseModel):
    chat_history: List[ChatMessage] = Field(..., description="Full interview transcript to evaluate")