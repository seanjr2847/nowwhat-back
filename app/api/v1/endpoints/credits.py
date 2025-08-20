"""
크레딧 관리 API 엔드포인트

비즈니스 로직:
- 사용자 크레딧 조회
- 크레딧 사용 내역 조회
- 크레딧 구매 (추후 확장)
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
import logging

from app.core.auth import get_current_user
from app.core.database import get_db
from app.models.database import User, CreditLog
from app.core.credits import get_user_credits
from app.schemas.credits import (
    CreditInfoResponse,
    CreditLogResponse,
    CreditLogListResponse
)

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/", response_model=CreditInfoResponse)
async def get_credits(
    current_user: User = Depends(get_current_user)
):
    """현재 사용자의 크레딧 정보 조회"""
    try:
        credit_info = get_user_credits(current_user)
        
        return CreditInfoResponse(
            user_id=current_user.id,
            credits=current_user.credits,
            status="sufficient" if current_user.credits > 0 else "insufficient"
        )
        
    except Exception as e:
        logger.error(f"Failed to get credits for user {current_user.id}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="크레딧 정보 조회 중 오류가 발생했습니다."
        )


@router.get("/history", response_model=CreditLogListResponse)
async def get_credit_history(
    limit: int = 50,
    offset: int = 0,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """사용자의 크레딧 사용 내역 조회"""
    try:
        # 크레딧 로그 조회 (최신순)
        credit_logs = db.query(CreditLog).filter(
            CreditLog.user_id == current_user.id
        ).order_by(
            CreditLog.created_at.desc()
        ).offset(offset).limit(limit).all()
        
        # 응답 형식으로 변환
        logs = []
        for log in credit_logs:
            logs.append(CreditLogResponse(
                id=log.id,
                action=log.action,
                credits_before=log.credits_before,
                credits_after=log.credits_after,
                created_at=log.created_at.isoformat()
            ))
        
        return CreditLogListResponse(
            logs=logs,
            total_count=len(logs),
            has_more=len(logs) == limit
        )
        
    except Exception as e:
        logger.error(f"Failed to get credit history for user {current_user.id}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="크레딧 사용 내역 조회 중 오류가 발생했습니다."
        )