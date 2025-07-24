from fastapi import APIRouter, HTTPException, Depends
from app.schemas.nowwhat import GoogleLoginRequest, LoginResponse, LogoutRequest, APIResponse
from app.core.auth import get_current_user

router = APIRouter()

@router.post("/google", response_model=LoginResponse)
async def google_login(login_data: GoogleLoginRequest):
    """구글 OAuth 로그인"""
    try:
        # TODO: 실제 구글 OAuth 토큰 검증
        # 1. googleToken 검증
        # 2. 사용자 정보 추출
        # 3. DB에서 사용자 조회/생성
        # 4. JWT 토큰 생성
        
        # 임시 응답
        return LoginResponse(
            accessToken="eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
            refreshToken="refresh_token_placeholder",
            user={
                "id": "user_123",
                "email": "user@example.com",
                "name": "테스트 사용자",
                "profileImage": None
            }
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail="로그인 실패")

@router.post("/logout", response_model=APIResponse)
async def logout(logout_data: LogoutRequest, current_user=Depends(get_current_user)):
    """로그아웃"""
    try:
        # TODO: 실제 로그아웃 처리
        # 1. refreshToken 무효화
        # 2. 세션 삭제
        # 3. 로그 기록
        
        return APIResponse(
            success=True,
            message="로그아웃되었습니다."
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail="로그아웃 실패") 