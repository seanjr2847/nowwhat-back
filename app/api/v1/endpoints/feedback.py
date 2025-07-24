from fastapi import APIRouter, HTTPException, Depends
from app.schemas.nowwhat import FeedbackRequest, APIResponse
from app.core.auth import get_current_user

router = APIRouter()

@router.post("/", response_model=APIResponse)
async def submit_feedback(feedback_data: FeedbackRequest, current_user=Depends(get_current_user)):
    """피드백 제출 - 만족도 평가"""
    try:
        # TODO: 실제 피드백 저장 로직
        # 1. 체크리스트 존재 확인
        # 2. 사용자 권한 확인
        # 3. 피드백 데이터 저장
        # 4. 분석용 데이터 집계
        
        return APIResponse(
            success=True,
            message="피드백이 성공적으로 제출되었습니다.",
            data={
                "feedbackId": "feedback_123",
                "checklistId": feedback_data.checklistId,
                "isPositive": feedback_data.isPositive,
                "rating": feedback_data.rating,
                "timestamp": feedback_data.timestamp
            }
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail="피드백 제출에 실패했습니다.") 