from fastapi import APIRouter, HTTPException, Depends, Request
from app.schemas.nowwhat import (
    Intent, IntentAnalyzeResponse, 
    IntentAnalyzeRequest, IntentAnalyzeApiResponse, IntentOption
)
from app.core.auth import get_current_user
from app.core.database import get_db
from app.services.gemini_service import gemini_service
from app.utils.geo_utils import detect_country_from_ip, get_client_ip
from app.crud.session import (
    create_intent_session, 
    update_intent_session_with_intents
)
from sqlalchemy.orm import Session
import logging
import asyncio

logger = logging.getLogger(__name__)

router = APIRouter()

@router.post("/analyze", response_model=IntentAnalyzeApiResponse)
async def analyze_intents(
    request: Request,
    intent_request: IntentAnalyzeRequest,
    db: Session = Depends(get_db)
):
    """사용자 입력을 분석하여 의도 옵션 생성"""
    try:
        # 1. 입력 검증 (Pydantic이 자동으로 처리하지만 추가 검증)
        goal = intent_request.goal.strip()
        if not goal:
            raise HTTPException(status_code=400, detail="목표를 입력해주세요.")
        
        # 2. 클라이언트 IP 추출 및 국가 감지
        client_ip = get_client_ip(request)
        logger.info(f"Client IP: {client_ip}")
        
        user_country = await detect_country_from_ip(client_ip)
        logger.info(f"Detected country: {user_country}")
        
        # 3. 세션 생성 및 DB 저장
        db_session = create_intent_session(
            db=db,
            goal=goal,
            user_ip=client_ip,
            user_country=user_country
        )
        
        # 4. Gemini API를 통한 의도 분석
        intents = await gemini_service.analyze_intent(goal, user_country)
        
        # 5. 생성된 의도 옵션을 DB에 업데이트
        intents_data = [intent.dict() for intent in intents]
        update_intent_session_with_intents(
            db=db,
            session_id=db_session.session_id,
            intents=intents_data
        )
        
        # 6. 응답 반환
        return IntentAnalyzeApiResponse(
            sessionId=db_session.session_id,
            intents=intents
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Intent analysis failed: {str(e)}")
        raise HTTPException(status_code=500, detail="의도 분석 중 오류가 발생했습니다.")

@router.get("/analyze/{goal_id}", response_model=IntentAnalyzeResponse)
def analyze_intents_legacy(goal_id: str, current_user=Depends(get_current_user)):
    """분석된 목표의 의도 옵션 조회 - 4가지 의도 제공 (기존 엔드포인트)"""
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