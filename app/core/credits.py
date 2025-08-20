"""
크레딧 시스템 관련 유틸리티 및 미들웨어

비즈니스 로직:
- 질문 생성 및 체크리스트 생성 시 1크레딧 차감
- 크레딧 부족 시 402 Payment Required 에러 반환
- 크레딧 사용 내역 로깅
- 신규 가입자 10크레딧 자동 지급
"""

import logging
from functools import wraps
from typing import Callable, Any
from fastapi import HTTPException, Depends
from sqlalchemy.orm import Session

from app.models.database import User, CreditLog
from app.core.database import get_db

logger = logging.getLogger(__name__)


class CreditError(Exception):
    """크레딧 관련 예외"""
    pass


def require_credits(cost: int = 1):
    """크레딧 차감 데코레이터
    
    Args:
        cost: 필요한 크레딧 수 (기본값: 1)
        
    Raises:
        HTTPException: 크레딧 부족 시 402 Payment Required
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # FastAPI 함수에서 current_user와 db 파라미터 찾기
            current_user = None
            db = None
            
            # kwargs에서 찾기
            if 'current_user' in kwargs:
                current_user = kwargs['current_user']
            if 'db' in kwargs:
                db = kwargs['db']
            
            # args에서 찾기 (일반적인 FastAPI 패턴)
            if not current_user or not db:
                for arg in args:
                    if isinstance(arg, User):
                        current_user = arg
                    elif hasattr(arg, 'query'):  # SQLAlchemy Session 체크
                        db = arg
            
            if not current_user:
                raise HTTPException(
                    status_code=401,
                    detail="인증이 필요합니다."
                )
            
            if not db:
                raise HTTPException(
                    status_code=500,
                    detail="데이터베이스 연결 오류"
                )
            
            # 크레딧 체크
            if current_user.credits < cost:
                logger.warning(f"User {current_user.id} has insufficient credits: {current_user.credits} < {cost}")
                raise HTTPException(
                    status_code=402,  # Payment Required
                    detail={
                        "error": "INSUFFICIENT_CREDITS",
                        "message": f"크레딧이 부족합니다. 현재 {current_user.credits}크레딧, 필요 {cost}크레딧",
                        "current_credits": current_user.credits,
                        "required_credits": cost
                    }
                )
            
            # 크레딧 차감 전 상태 저장
            credits_before = current_user.credits
            
            # 크레딧 차감
            current_user.credits -= cost
            db.add(current_user)
            
            # 크레딧 사용 로그 생성
            credit_log = CreditLog(
                user_id=current_user.id,
                action=func.__name__,  # 함수 이름을 액션으로 사용
                credits_before=credits_before,
                credits_after=current_user.credits
            )
            db.add(credit_log)
            
            try:
                db.commit()
                logger.info(f"User {current_user.id} used {cost} credits. {credits_before} → {current_user.credits}")
            except Exception as e:
                db.rollback()
                logger.error(f"Failed to deduct credits for user {current_user.id}: {str(e)}")
                raise HTTPException(
                    status_code=500,
                    detail="크레딧 차감 중 오류가 발생했습니다."
                )
            
            # 원래 함수 실행
            return await func(*args, **kwargs)
        
        return wrapper
    return decorator


def add_credits_to_user(db: Session, user: User, amount: int, reason: str = "manual_add") -> bool:
    """사용자에게 크레딧 추가
    
    Args:
        db: 데이터베이스 세션
        user: 사용자 객체
        amount: 추가할 크레딧 수
        reason: 추가 사유
        
    Returns:
        bool: 성공 여부
    """
    try:
        credits_before = user.credits
        user.credits += amount
        
        # 크레딧 추가 로그
        credit_log = CreditLog(
            user_id=user.id,
            action=f"add_credits_{reason}",
            credits_before=credits_before,
            credits_after=user.credits
        )
        
        db.add(user)
        db.add(credit_log)
        db.commit()
        
        logger.info(f"Added {amount} credits to user {user.id}. {credits_before} → {user.credits}")
        return True
        
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to add credits to user {user.id}: {str(e)}")
        return False


def get_user_credits(user: User) -> dict:
    """사용자 크레딧 정보 조회
    
    Args:
        user: 사용자 객체
        
    Returns:
        dict: 크레딧 정보
    """
    return {
        "user_id": user.id,
        "credits": user.credits,
        "status": "sufficient" if user.credits > 0 else "insufficient"
    }


def initialize_new_user_credits(db: Session, user: User, initial_credits: int = 10) -> bool:
    """신규 사용자 크레딧 초기화
    
    Args:
        db: 데이터베이스 세션
        user: 사용자 객체
        initial_credits: 초기 크레딧 수 (기본값: 10)
        
    Returns:
        bool: 성공 여부
    """
    try:
        # 이미 크레딧이 설정되어 있으면 스킵
        if user.credits != 0:
            logger.info(f"User {user.id} already has {user.credits} credits, skipping initialization")
            return True
        
        user.credits = initial_credits
        
        # 초기 크레딧 지급 로그
        credit_log = CreditLog(
            user_id=user.id,
            action="initial_signup_bonus",
            credits_before=0,
            credits_after=initial_credits
        )
        
        db.add(user)
        db.add(credit_log)
        db.commit()
        
        logger.info(f"Initialized {initial_credits} credits for new user {user.id}")
        return True
        
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to initialize credits for user {user.id}: {str(e)}")
        return False