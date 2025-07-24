from fastapi import APIRouter, HTTPException, Depends
from app.schemas.nowwhat import Intent, IntentAnalyzeResponse
from app.core.auth import get_current_user

router = APIRouter()

@router.get("/analyze/{goal_id}", response_model=IntentAnalyzeResponse)
async def analyze_intents(goal_id: str, current_user=Depends(get_current_user)):
    """분석된 목표의 의도 옵션 조회 - 4가지 의도 제공"""
    try:
        # TODO: 실제 의도 분석 로직
        # 1. goal_id로 목표 정보 조회
        # 2. AI를 통한 의도 분석
        # 3. 4가지 의도 옵션 생성
        
        # 임시 의도 목록
        sample_intents = [
            Intent(
                id="intent_1",
                title="건강 개선",
                description="건강한 생활습관을 통한 체력 향상",
                category="health"
            ),
            Intent(
                id="intent_2", 
                title="습관 형성",
                description="꾸준한 루틴을 통한 자기계발",
                category="habit"
            ),
            Intent(
                id="intent_3",
                title="목표 달성",
                description="구체적인 성과를 위한 단계별 실행",
                category="achievement"
            ),
            Intent(
                id="intent_4",
                title="스트레스 관리",
                description="정신건강과 웰빙을 위한 관리",
                category="wellness"
            )
        ]
        
        return IntentAnalyzeResponse(
            success=True,
            message="의도 분석이 완료되었습니다.",
            data=sample_intents
        )
    except Exception as e:
        raise HTTPException(status_code=404, detail="목표를 찾을 수 없습니다.") 