from pydantic import BaseModel
from typing import List, Optional

# Request
class QuestionGenerateRequest(BaseModel):
    intentId: str
    sessionId: Optional[str] = None  # 세션 ID (헤더 대신 body로도 전달 가능)

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