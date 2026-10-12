import uuid
from typing import List

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.interview import Interview
from app.models.message import Message

ALLOWED_SENDERS = ("candidate", "interviewer")


class InterviewService:
    """Persistence-backed interview sessions (sync SQLAlchemy)."""

    def __init__(self, db: Session):
        self.db = db

    def create_session(self, *, user_id: uuid.UUID, role_type: str) -> Interview:
        session = Interview(user_id=user_id, role_type=role_type, status="in_progress")
        self.db.add(session)
        self.db.commit()
        self.db.refresh(session)
        return session

    def get_session(self, interview_id: uuid.UUID) -> Interview | None:
        return self.db.get(Interview, interview_id)

    def add_message(
        self,
        *,
        interview_id: uuid.UUID,
        sender: str,
        transcript: str,
        audio_path: str | None = None,
    ) -> Message:
        if sender not in ALLOWED_SENDERS:
            raise ValueError(f"sender must be one of {ALLOWED_SENDERS}")
        message = Message(
            interview_id=interview_id,
            sender=sender,
            transcript=transcript,
            audio_path=audio_path,
        )
        self.db.add(message)
        self.db.commit()
        self.db.refresh(message)
        return message

    def get_history(self, interview_id: uuid.UUID) -> List[Message]:
        result = self.db.execute(
            select(Message)
            .where(Message.interview_id == interview_id)
            .order_by(Message.created_at)
        )
        return list(result.scalars().all())

    def complete_session(self, interview_id: uuid.UUID) -> Interview | None:
        session = self.get_session(interview_id)
        if session is None:
            return None
        session.status = "completed"
        self.db.commit()
        self.db.refresh(session)
        return session
