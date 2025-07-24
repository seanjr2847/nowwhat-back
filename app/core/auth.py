from fastapi import HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional

security = HTTPBearer(auto_error=False)

async def get_current_user(credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)):
    """
    Bearer 토큰을 통해 현재 사용자를 인증합니다.
    노션 API는 "Bearer secret_xxx" 형태의 토큰을 사용합니다.
    """
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="인증이 필요합니다.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    token = credentials.credentials
    
    # TODO: 실제 토큰 검증 로직 구현
    # 1. 토큰이 "secret_" 으로 시작하는지 확인
    # 2. 데이터베이스에서 토큰 유효성 확인
    # 3. 사용자 정보 반환
    
    if not token.startswith("secret_"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="잘못된 토큰 형식입니다.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # 임시로 더미 사용자 반환
    return {
        "id": "user_id_placeholder",
        "object": "user",
        "type": "person",
        "name": "Test User",
        "avatar_url": None
    }

async def verify_notion_version(version: str = "2022-06-28"):
    """
    노션 API 버전을 확인합니다.
    헤더에서 Notion-Version을 확인해야 합니다.
    """
    # TODO: 실제 버전 확인 로직 구현
    return True 