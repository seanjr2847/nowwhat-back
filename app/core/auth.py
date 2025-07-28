from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from app.core.database import get_db
from app.models.database import User
from app.core.security import verify_token
import logging

logger = logging.getLogger(__name__)

security = HTTPBearer()

def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    """현재 인증된 사용자 정보 조회"""
    try:
        # JWT 토큰 검증
        payload = verify_token(credentials.credentials)
        user_id = payload.get("sub")
        
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="유효하지 않은 토큰입니다."
            )
        
        # 데이터베이스에서 사용자 조회 (안전한 에러 처리)
        try:
            user = db.query(User).filter(User.id == user_id).first()
            
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="사용자를 찾을 수 없습니다."
                )
            
            return user
            
        except SQLAlchemyError as e:
            logger.error(f"Database error during user authentication: {e}")
            # 데이터베이스 세션 롤백
            try:
                db.rollback()
            except Exception:
                pass
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="인증 처리 중 오류가 발생했습니다."
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Authentication error: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="인증에 실패했습니다."
        )

def get_optional_user(
    request: Request,
    db: Session = Depends(get_db)
) -> User | None:
    """선택적 사용자 인증 (토큰이 없어도 허용)"""
    try:
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            return None
        
        token = auth_header.split(" ")[1]
        payload = verify_token(token)
        user_id = payload.get("sub")
        
        if not user_id:
            return None
        
        try:
            user = db.query(User).filter(User.id == user_id).first()
            return user
        except SQLAlchemyError as e:
            logger.warning(f"Database error during optional user authentication: {e}")
            return None
            
    except Exception as e:
        logger.warning(f"Optional authentication error: {e}")
        return None