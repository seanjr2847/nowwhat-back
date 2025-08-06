from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from typing import List, Optional
from app.schemas.nowwhat import (
    FeedbackRequest, FeedbackUpdateRequest, APIResponse
)
from app.core.auth import get_current_user
from app.core.database import get_db
from app.crud import feedback as feedback_crud
from app.models.database import User
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

@router.post("/", response_model=APIResponse)
async def submit_feedback(
    feedback_data: FeedbackRequest, 
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """피드백 제출 - 만족도 평가"""
    try:
        # 1. 체크리스트 존재 및 소유권 확인
        if not feedback_crud.verify_checklist_ownership(
            db, feedback_data.checklistId, current_user.id
        ):
            raise HTTPException(
                status_code=404, 
                detail="체크리스트를 찾을 수 없거나 접근 권한이 없습니다."
            )
        
        # 2. 피드백 데이터 저장
        feedback = feedback_crud.create_feedback(
            db=db,
            checklist_id=feedback_data.checklistId,
            user_id=current_user.id,
            is_positive=feedback_data.isPositive,
            rating=feedback_data.rating,
            comment=feedback_data.comment,
            categories=feedback_data.categories
        )
        
        logger.info(f"Feedback submitted - User: {current_user.id}, Checklist: {feedback_data.checklistId}, Rating: {feedback_data.rating}")
        
        return APIResponse(
            success=True,
            message="피드백이 성공적으로 제출되었습니다.",
            data={
                "feedbackId": feedback.id,
                "checklistId": feedback.checklist_id,
                "isPositive": feedback.is_positive,
                "rating": feedback.rating,
                "comment": feedback.comment,
                "categories": feedback.categories,
                "timestamp": feedback.created_at
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to submit feedback: {str(e)}")
        raise HTTPException(status_code=500, detail="피드백 제출 중 서버 오류가 발생했습니다.")

@router.get("/my", response_model=APIResponse)
async def get_my_feedbacks(
    limit: int = 50,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """내가 작성한 피드백 목록 조회"""
    try:
        feedbacks = feedback_crud.get_feedbacks_by_user(db, current_user.id, limit)
        
        feedback_list = []
        for feedback in feedbacks:
            feedback_list.append({
                "feedbackId": feedback.id,
                "checklistId": feedback.checklist_id,
                "checklistTitle": feedback.checklist.title if feedback.checklist else None,
                "isPositive": feedback.is_positive,
                "rating": feedback.rating,
                "comment": feedback.comment,
                "categories": feedback.categories,
                "createdAt": feedback.created_at
            })
        
        return APIResponse(
            success=True,
            message="피드백 목록을 조회했습니다.",
            data={
                "feedbacks": feedback_list,
                "total": len(feedback_list)
            }
        )
        
    except Exception as e:
        logger.error(f"Failed to get user feedbacks: {str(e)}")
        raise HTTPException(status_code=500, detail="피드백 조회 중 오류가 발생했습니다.")

@router.get("/checklist/{checklist_id}", response_model=APIResponse)
async def get_checklist_feedbacks(
    checklist_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """특정 체크리스트의 피드백 조회 (본인 체크리스트만)"""
    try:
        # 체크리스트 소유권 확인
        if not feedback_crud.verify_checklist_ownership(db, checklist_id, current_user.id):
            raise HTTPException(
                status_code=404, 
                detail="체크리스트를 찾을 수 없거나 접근 권한이 없습니다."
            )
        
        feedbacks = feedback_crud.get_feedbacks_by_checklist(db, checklist_id)
        
        feedback_list = []
        for feedback in feedbacks:
            feedback_list.append({
                "feedbackId": feedback.id,
                "isPositive": feedback.is_positive,
                "rating": feedback.rating,
                "comment": feedback.comment,
                "categories": feedback.categories,
                "createdAt": feedback.created_at
            })
        
        # 통계 정보도 함께 반환
        statistics = feedback_crud.get_feedback_statistics(db, checklist_id)
        
        return APIResponse(
            success=True,
            message="체크리스트 피드백을 조회했습니다.",
            data={
                "checklistId": checklist_id,
                "feedbacks": feedback_list,
                "statistics": statistics
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get checklist feedbacks: {str(e)}")
        raise HTTPException(status_code=500, detail="피드백 조회 중 오류가 발생했습니다.")

@router.put("/{feedback_id}", response_model=APIResponse)
async def update_feedback(
    feedback_id: str,
    update_data: FeedbackUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """피드백 수정 (본인 작성 피드백만)"""
    try:
        updated_feedback = feedback_crud.update_feedback(
            db=db,
            feedback_id=feedback_id,
            user_id=current_user.id,
            is_positive=update_data.isPositive,
            rating=update_data.rating,
            comment=update_data.comment,
            categories=update_data.categories
        )
        
        if not updated_feedback:
            raise HTTPException(
                status_code=404,
                detail="피드백을 찾을 수 없거나 수정 권한이 없습니다."
            )
        
        return APIResponse(
            success=True,
            message="피드백이 성공적으로 수정되었습니다.",
            data={
                "feedbackId": updated_feedback.id,
                "checklistId": updated_feedback.checklist_id,
                "isPositive": updated_feedback.is_positive,
                "rating": updated_feedback.rating,
                "comment": updated_feedback.comment,
                "categories": updated_feedback.categories,
                "updatedAt": updated_feedback.created_at
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update feedback: {str(e)}")
        raise HTTPException(status_code=500, detail="피드백 수정 중 오류가 발생했습니다.")

@router.delete("/{feedback_id}", response_model=APIResponse)
async def delete_feedback(
    feedback_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """피드백 삭제 (본인 작성 피드백만)"""
    try:
        success = feedback_crud.delete_feedback(db, feedback_id, current_user.id)
        
        if not success:
            raise HTTPException(
                status_code=404,
                detail="피드백을 찾을 수 없거나 삭제 권한이 없습니다."
            )
        
        return APIResponse(
            success=True,
            message="피드백이 성공적으로 삭제되었습니다.",
            data={"feedbackId": feedback_id}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete feedback: {str(e)}")
        raise HTTPException(status_code=500, detail="피드백 삭제 중 오류가 발생했습니다.")

@router.get("/statistics", response_model=APIResponse)
async def get_feedback_statistics(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """전체 피드백 통계 조회 (개발/관리 목적)"""
    try:
        # 현재는 모든 사용자가 전체 통계를 볼 수 있도록 함
        # 필요시 관리자 권한 체크 추가 가능
        
        statistics = feedback_crud.get_feedback_statistics(db)
        
        return APIResponse(
            success=True,
            message="피드백 통계를 조회했습니다.",
            data=statistics
        )
        
    except Exception as e:
        logger.error(f"Failed to get feedback statistics: {str(e)}")
        raise HTTPException(status_code=500, detail="통계 조회 중 오류가 발생했습니다.") 