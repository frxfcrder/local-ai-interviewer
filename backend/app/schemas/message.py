import uuid
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field

class MessageCreate(BaseModel):
    transcript: str = Field(..., examples=["I would use an async connection pool with asyncpg..."])
    sender: str = Field(..., examples=["candidate"], description="Must be 'candidate' or 'interviewer'")

class MessageResponse(BaseModel):
    id: uuid.UUID
    interview_id: uuid.UUID
    sender: str
    transcript: str
    audio_path: str | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)