from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from typing import Optional
from app.schemas.nowwhat import UserProfile, APIResponse
from app.core.auth import get_current_user
from app.core.database import get_db
from app.crud.user import user as user_crud
from app.models.database import User
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

@router.get("/profile", response_model=UserProfile)
async def get_profile(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """내 프로필 조회"""
    try:
        # current_user는 이미 User 객체이므로 직접 사용
        user = user_crud.get(db, current_user.id)
        
        if not user:
            raise HTTPException(status_code=404, detail="사용자를 찾을 수 없습니다.")
        
        # 마지막 로그인 시간 업데이트
        user_crud.update_last_login(db, user.id)
        
        return UserProfile(
            id=user.id,
            email=user.email,
            name=user.name,
            profileImage=user.profile_image,
            createdAt=user.created_at,
            lastLoginAt=user.last_login_at
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get user profile: {str(e)}")
        raise HTTPException(status_code=500, detail="프로필 조회 중 오류가 발생했습니다.")

@router.put("/profile", response_model=APIResponse)
async def update_profile(
    name: Optional[str] = None,
    profile_image: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """프로필 업데이트"""
    try:
        updated_user = user_crud.update_profile(
            db=db,
            user_id=current_user.id,
            name=name,
            profile_image=profile_image
        )
        
        if not updated_user:
            raise HTTPException(status_code=404, detail="사용자를 찾을 수 없습니다.")
        
        return APIResponse(
            success=True,
            message="프로필이 성공적으로 업데이트되었습니다.",
            data={
                "id": updated_user.id,
                "name": updated_user.name,
                "profileImage": updated_user.profile_image,
                "updatedAt": updated_user.updated_at
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update profile: {str(e)}")
        raise HTTPException(status_code=500, detail="프로필 업데이트 중 오류가 발생했습니다.")

@router.get("/statistics", response_model=APIResponse)
async def get_user_statistics(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """사용자 통계 조회"""
    try:
        statistics = user_crud.get_user_statistics(db, current_user.id)
        
        return APIResponse(
            success=True,
            message="사용자 통계를 조회했습니다.",
            data={
                "userId": current_user.id,
                "statistics": statistics
            }
        )
        
    except Exception as e:
        logger.error(f"Failed to get user statistics: {str(e)}")
        raise HTTPException(status_code=500, detail="통계 조회 중 오류가 발생했습니다.")

@router.delete("/account", response_model=APIResponse)
async def delete_account(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """계정 삭제 (모든 관련 데이터 포함)"""
    try:
        success = user_crud.delete_user_account(db, current_user.id)
        
        if not success:
            raise HTTPException(
                status_code=404,
                detail="계정을 찾을 수 없습니다."
            )
        
        logger.info(f"User account deleted: {current_user.id}")
        
        return APIResponse(
            success=True,
            message="계정이 성공적으로 삭제되었습니다.",
            data={"userId": current_user.id}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete account: {str(e)}")
        raise HTTPException(status_code=500, detail="계정 삭제 중 오류가 발생했습니다.")

@router.get("/activity", response_model=APIResponse)
async def get_user_activity(
    limit: int = 10,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """사용자 최근 활동 조회"""
    try:
        user_with_relations = user_crud.get_user_with_relations(db, current_user.id)
        
        if not user_with_relations:
            raise HTTPException(status_code=404, detail="사용자를 찾을 수 없습니다.")
        
        # 최근 체크리스트와 피드백 조회 (간단한 버전)
        from app.models.database import Checklist, Feedback
        from sqlalchemy import desc
        
        recent_checklists = (
            db.query(Checklist)
            .filter(Checklist.user_id == current_user.id)
            .order_by(desc(Checklist.created_at))
            .limit(limit)
            .all()
        )
        
        recent_feedbacks = (
            db.query(Feedback)
            .filter(Feedback.user_id == current_user.id)
            .order_by(desc(Feedback.created_at))
            .limit(limit)
            .all()
        )
        
        activity_data = {
            "recentChecklists": [
                {
                    "id": checklist.id,
                    "title": checklist.title,
                    "category": checklist.category,
                    "progress": checklist.progress,
                    "createdAt": checklist.created_at
                }
                for checklist in recent_checklists
            ],
            "recentFeedbacks": [
                {
                    "id": feedback.id,
                    "checklistId": feedback.checklist_id,
                    "isPositive": feedback.is_positive,
                    "rating": feedback.rating,
                    "createdAt": feedback.created_at
                }
                for feedback in recent_feedbacks
            ]
        }
        
        return APIResponse(
            success=True,
            message="사용자 활동 내역을 조회했습니다.",
            data=activity_data
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get user activity: {str(e)}")
        raise HTTPException(status_code=500, detail="활동 내역 조회 중 오류가 발생했습니다.") 