from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum

# 공통 응답 모델
class APIResponse(BaseModel):
    success: bool = True
    message: str = ""
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

# 인증 관련 스키마
class GoogleLoginRequest(BaseModel):
    googleToken: str = Field(..., description="구글 OAuth 토큰")
    deviceInfo: Optional[str] = Field(None, description="기기 정보")
    timezone: Optional[str] = Field(None, description="타임존")

class LoginResponse(BaseModel):
    accessToken: str
    refreshToken: str
    user: Dict[str, Any]

class LogoutRequest(BaseModel):
    refreshToken: str

# 사용자 관련 스키마
class UserProfile(BaseModel):
    id: str
    email: str
    name: str
    profileImage: Optional[str] = None
    createdAt: datetime
    lastLoginAt: Optional[datetime] = None

# 의도 관련 스키마
class Intent(BaseModel):
    id: str
    title: str
    description: str
    category: str

class IntentAnalyzeResponse(APIResponse):
    data: List[Intent]

# 새로운 의도 분석 스키마
class IntentAnalyzeRequest(BaseModel):
    goal: str = Field(..., description="사용자가 입력한 목표 텍스트")

# 디버깅용 간단한 모델
class SimpleTestRequest(BaseModel):
    goal: str

class SimpleTestResponse(BaseModel):
    received_goal: str
    success: bool = True

class IntentOption(BaseModel):
    title: str = Field(..., description="의도 제목")
    description: str = Field(..., description="의도 설명")
    icon: str = Field(..., description="아이콘")

class IntentAnalyzeApiResponse(BaseModel):
    sessionId: str = Field(..., description="세션 ID")
    intents: List[IntentOption] = Field(..., description="의도 목록")

# 질문 관련 스키마
class Question(BaseModel):
    id: str
    text: str
    type: str  # single, multiple
    options: List[str]
    category: str

class QuestionGenerateResponse(APIResponse):
    data: List[Question]

class AnswerRequest(BaseModel):
    questionId: str
    answer: str  # 선택된 답변
    answeredAt: datetime = Field(default_factory=datetime.now)

# 체크리스트 관련 스키마
class ChecklistItemBase(BaseModel):
    title: str = Field(..., description="체크리스트 아이템 제목")
    description: Optional[str] = Field(None, description="체크리스트 아이템 설명")

class ChecklistItemCreate(ChecklistItemBase):
    pass

class ChecklistItemResponse(ChecklistItemBase):
    id: str
    order: int
    isCompleted: bool = False
    completedAt: Optional[str] = None

class ChecklistItemUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    isCompleted: Optional[bool] = None
    order: Optional[int] = None

class ChecklistCreate(BaseModel):
    title: str = Field(..., description="체크리스트 제목")
    category: str = Field(..., description="체크리스트 카테고리")
    description: Optional[str] = Field(None, description="체크리스트 설명")
    items: List[ChecklistItemCreate] = Field(..., description="체크리스트 아이템들")

class ChecklistUpdate(BaseModel):
    title: Optional[str] = None
    category: Optional[str] = None
    description: Optional[str] = None

class ChecklistResponse(BaseModel):
    id: str
    title: str
    category: str
    description: Optional[str] = None
    totalItems: int
    completedItems: int
    progressPercentage: float
    isCompleted: bool = False
    items: List[ChecklistItemResponse]
    createdAt: str
    updatedAt: Optional[str] = None
    completedAt: Optional[str] = None

class ChecklistItem(BaseModel):
    id: str
    text: str
    isCompleted: bool = False
    completedAt: Optional[datetime] = None
    order: int

class Checklist(BaseModel):
    id: str
    title: str
    description: Optional[str] = None
    category: str
    items: List[ChecklistItem]
    progress: float = 0.0  # 진행률 (0-100)
    createdAt: datetime
    updatedAt: datetime
    isPublic: bool = True
    customName: Optional[str] = None

class ChecklistSaveRequest(BaseModel):
    saveToMyList: bool = True
    customName: Optional[str] = None

class ItemUpdateRequest(BaseModel):
    isCompleted: bool
    completedAt: Optional[datetime] = None

class ChecklistListQuery(BaseModel):
    page: Optional[int] = 1
    limit: Optional[int] = 20
    category: Optional[str] = None
    status: Optional[str] = None  # all, completed, in_progress
    sortBy: Optional[str] = "createdAt"
    sortOrder: Optional[str] = "desc"

class ChecklistListResponse(APIResponse):
    data: List[Checklist]
    pagination: Dict[str, Any]

# 피드백 관련 스키마
class FeedbackRequest(BaseModel):
    checklistId: str
    isPositive: bool
    rating: Optional[int] = Field(None, ge=1, le=5, description="1-5점 평가")
    comment: Optional[str] = None
    categories: Optional[List[str]] = None
    timestamp: datetime = Field(default_factory=datetime.now)

# 에러 응답
class ErrorResponse(BaseModel):
    success: bool = False
    error: str
    message: str
    code: Optional[str] = None 