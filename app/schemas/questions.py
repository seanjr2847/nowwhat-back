from pydantic import BaseModel, Field
from typing import List, Optional, Union

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

# New schemas for POST /questions/answer endpoint
class SelectedIntentSchema(BaseModel):
    """선택된 의도 정보"""
    index: int = Field(..., ge=0, description="Intent index from analysis")
    title: str = Field(..., min_length=1, description="Selected intent title")

class AnswerItemSchema(BaseModel):
    """개별 답변 항목"""
    questionIndex: int = Field(..., ge=0, description="Question index")
    questionText: str = Field(..., min_length=1, description="Question content")
    answer: Union[str, List[str]] = Field(..., description="User answer(s) - can be single string or array")

class QuestionAnswersRequest(BaseModel):
    """POST /questions/answer 요청 스키마"""
    goal: str = Field(..., min_length=1, max_length=500, description="Initial user goal")
    selectedIntent: SelectedIntentSchema = Field(..., description="Selected intent from analysis")
    answers: List[AnswerItemSchema] = Field(..., min_items=1, description="List of question answers")

    class Config:
        schema_extra = {
            "example": {
                "goal": "일본여행 가고싶어",
                "selectedIntent": {
                    "index": 0,
                    "title": "여행 계획"
                },
                "answers": [
                    {
                        "questionIndex": 0,
                        "questionText": "여행 기간은 얼마나 되나요?",
                        "answer": "3days"
                    },
                    {
                        "questionIndex": 1,
                        "questionText": "예산은 얼마나 되나요?",
                        "answer": "1million"
                    }
                ]
            }
        }

class QuestionAnswersResponse(BaseModel):
    """POST /questions/answer 응답 스키마"""
    checklistId: str = Field(..., description="Generated checklist ID with format cl_{timestamp}_{random}")
    redirectUrl: str = Field(..., description="Result page URL path")

    class Config:
        schema_extra = {
            "example": {
                "checklistId": "cl_abc123",
                "redirectUrl": "/result/cl_abc123"
            }
        }