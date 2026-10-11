from pydantic import BaseModel, Field

class EvaluationResponse(BaseModel):
    technical_score: int = Field(..., ge=1, le=10, description="Technical proficiency score from 1 to 10")
    problem_solving_score: int = Field(..., ge=1, le=10, description="System design and problem solving score")
    communication_score: int = Field(..., ge=1, le=10, description="Clarity and articulation score")
    strengths: list[str] = Field(..., description="Key strengths demonstrated during the interview")
    areas_for_improvement: list[str] = Field(..., description="Actionable feedback for growth")
    summary_verdict: str = Field(..., description="Final overall assessment")