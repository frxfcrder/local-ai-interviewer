import uuid
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field

class InterviewCreate(BaseModel):
    role_type: str = Field(..., example="Senior Backend Engineer", description="Target role for the AI interview")

class InterviewResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    role_type: str
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)