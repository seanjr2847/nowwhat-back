from pydantic import BaseModel
from typing import List, Optional

# Request
class QuestionGenerateRequest(BaseModel):
    sessionId: str
    goal: str
    intentTitle: str

# Response models
class Option(BaseModel):
    id: str
    text: str
    value: str

class Question(BaseModel):
    id: str
    text: str
    type: str  # "multiple" or "text"
    options: Optional[List[Option]] = None
    required: bool

class QuestionGenerateResponse(BaseModel):
    questions: List[Question]

# Additional models for question set management
class QuestionSetCreate(BaseModel):
    session_id: str
    intent_id: str
    questions: List[Question]

class QuestionSetResponse(BaseModel):
    questionSetId: str
    sessionId: str
    intentId: str
    questions: List[Question]
    createdAt: str