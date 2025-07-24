from fastapi import APIRouter, HTTPException, Depends
from app.schemas.nowwhat import UserProfile, APIResponse
from app.core.auth import get_current_user

router = APIRouter()

@router.get("/profile", response_model=UserProfile)
async def get_profile(current_user=Depends(get_current_user)):
    """내 프로필 조회"""
    try:
        # TODO: 실제 사용자 프로필 조회
        # 1. current_user에서 사용자 ID 추출
        # 2. DB에서 사용자 정보 조회
        # 3. 프로필 정보 반환
        
        from datetime import datetime
        
        return UserProfile(
            id=current_user.get("id", "user_123"),
            email="user@example.com",
            name=current_user.get("name", "테스트 사용자"),
            profileImage=current_user.get("avatar_url"),
            createdAt=datetime.now(),
            lastLoginAt=datetime.now()
        )
    except Exception as e:
        raise HTTPException(status_code=404, detail="사용자를 찾을 수 없습니다.") 