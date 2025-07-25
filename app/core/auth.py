from fastapi import HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, Dict, Any
from app.core.security import verify_token
from app.core.database import get_database
from app.crud.user import user
import logging

logger = logging.getLogger(__name__)

security = HTTPBearer(auto_error=False)

async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: AsyncSession = Depends(get_database)
) -> Dict[str, Any]:
    """
    Bearer 토큰을 통해 현재 사용자를 인증합니다.
    실제 JWT 토큰 검증과 데이터베이스 조회를 수행합니다.
    """
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="인증이 필요합니다.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    token = credentials.credentials
    
    # JWT 토큰 검증
    user_id = verify_token(token, token_type="access")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="유효하지 않은 토큰입니다.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # 데이터베이스에서 사용자 조회
    try:
        db_user = await user.get(db, id=user_id)
        if not db_user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="사용자를 찾을 수 없습니다.",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        return {
            "id": db_user.id,
            "email": db_user.email,
            "name": db_user.name,
            "profile_image": db_user.profile_image,
            "google_id": db_user.google_id
        }
        
    except Exception as e:
        logger.error(f"Database error during user authentication: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="인증 처리 중 오류가 발생했습니다."
        )

async def get_current_user_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: AsyncSession = Depends(get_database)
) -> Optional[Dict[str, Any]]:
    """
    선택적 사용자 인증 (토큰이 없어도 None 반환)
    """
    if not credentials:
        return None
    
    try:
        return await get_current_user(credentials, db)
    except HTTPException:
        return None

async def verify_notion_version(version: str = "2022-06-28"):
    """
    노션 API 버전을 확인합니다.
    헤더에서 Notion-Version을 확인해야 합니다.
    """
    # TODO: 실제 버전 확인 로직 구현
    return True 