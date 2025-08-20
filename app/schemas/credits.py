"""
크레딧 관련 Pydantic 스키마

비즈니스 로직:
- 크레딧 정보 응답 모델
- 크레딧 사용 내역 응답 모델
- 크레딧 구매 요청 모델 (추후 확장)
"""

from pydantic import BaseModel
from typing import List, Optional


class CreditInfoResponse(BaseModel):
    """사용자 크레딧 정보 응답"""
    user_id: str
    credits: int
    status: str  # "sufficient" | "insufficient"


class CreditLogResponse(BaseModel):
    """크레딧 사용 내역 개별 응답"""
    id: str
    action: str
    credits_before: int
    credits_after: int
    created_at: str


class CreditLogListResponse(BaseModel):
    """크레딧 사용 내역 목록 응답"""
    logs: List[CreditLogResponse]
    total_count: int
    has_more: bool


class CreditPurchaseRequest(BaseModel):
    """크레딧 구매 요청 (추후 확장용)"""
    package_id: str
    payment_method: str = "card"


class CreditPurchaseResponse(BaseModel):
    """크레딧 구매 응답 (추후 확장용)"""
    success: bool
    transaction_id: str
    credits_added: int
    total_credits: int