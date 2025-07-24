from pydantic import BaseModel
from typing import List, Optional

# Request
class QuestionGenerateRequest(BaseModel):
   intentId: str

# Response
class Option(BaseModel):
   id: str
   text: str
   value: str

class Question(BaseModel):
   id: str
   text: str
   type: str
   options: Optional[List[Option]] = None
   required: bool

class QuestionGenerateResponse(BaseModel):
   questions: List[Question]