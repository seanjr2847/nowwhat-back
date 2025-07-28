from fastapi import APIRouter, HTTPException, Depends, Request
from sqlalchemy.orm import Session
from app.schemas.questions import (
    QuestionGenerateRequest, QuestionGenerateResponse, 
    Question, Option
)
from app.core.auth import get_current_user
from app.core.database import get_db
from app.services.gemini_service import gemini_service
from app.utils.geo_utils import detect_country_from_ip, get_client_ip
from app.crud.session import (
    validate_session_basic,
    save_question_set
)
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

router = APIRouter()

@router.post("/generate", response_model=QuestionGenerateResponse)
async def generate_questions(
    request: Request,
    question_request: QuestionGenerateRequest,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """선택된 의도에 따른 맞춤 질문 생성 (POST)
    
    비즈니스 흐름:
    1. 세션 유효성 검증 (sessionId)
    2. 사용자 IP 기반 국가 자동 감지
    3. Gemini API를 통한 맞춤 질문 생성 (goal + intentTitle 사용)
    4. 질문 세트 ID 생성 및 DB 저장
    5. 클라이언트 응답
    """
    try:
        # 요청에서 필수 정보 추출
        session_id = question_request.sessionId
        goal = question_request.goal
        intent_title = question_request.intentTitle
        
        logger.info(f"Question generation request - Session: {session_id}, Goal: '{goal}', Intent: '{intent_title}'")
        
        # 1. 세션 유효성 검증 (의도 검증은 생략, 직접 전달받음)
        is_valid, db_session, error_message = validate_session_basic(
            db, session_id
        )
        
        if not is_valid:
            logger.warning(f"Session validation failed: {error_message}")
            raise HTTPException(status_code=400, detail=error_message)
        
        # 2. 사용자 IP 기반 국가 감지
        client_ip = get_client_ip(request)
        user_country = await detect_country_from_ip(client_ip)
        
        logger.info(f"Detected country: {user_country} for IP: {client_ip}")
        
        # 3. Gemini API를 통한 맞춤 질문 생성 (직접 전달받은 정보 사용)
        logger.info(f"Generating questions for goal: '{goal}', intent: '{intent_title}'")
        
        try:
            questions = await gemini_service.generate_questions(
                goal=goal,
                intent_title=intent_title,
                user_country=user_country
            )
            
            logger.info(f"Generated {len(questions)} questions via Gemini API")
            
        except Exception as e:
            logger.error(f"Gemini question generation failed: {str(e)}")
            # 캐시된 템플릿으로 대체는 이미 서비스 내부에서 처리됨
            questions = await gemini_service.generate_questions(
                goal=goal,
                intent_title=intent_title,
                user_country=user_country
            )
        
        # 4. 질문 검증 및 기본값 설정
        if not questions or len(questions) == 0:
            logger.warning("No questions generated, using default template")
            questions = _get_emergency_questions()
        
        # 5. 질문 세트 ID 생성 및 DB 저장
        questions_dict = [question.dict() for question in questions]
        question_set_id = save_question_set(
            db=db,
            session_id=session_id,
            intent_id=intent_title,  # intentTitle을 intent_id로 사용
            questions=questions_dict
        )
        
        logger.info(f"Saved question set with ID: {question_set_id}")
        
        # 6. 성공 응답
        return QuestionGenerateResponse(questions=questions)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in question generation: {str(e)}")
        raise HTTPException(
            status_code=500, 
            detail="질문 생성 중 서버 오류가 발생했습니다."
        )

def _get_emergency_questions() -> list[Question]:
    """비상용 기본 질문 템플릿"""
    return [
        Question(
            id="q_emergency_1",
            text="언제까지 이 목표를 달성하고 싶으신가요?",
            type="multiple",
            options=[
                Option(id="opt_1week", text="1주일 내", value="1week"),
                Option(id="opt_1month", text="1달 내", value="1month"),
                Option(id="opt_3months", text="3달 내", value="3months"),
                Option(id="opt_flexible", text="유연하게", value="flexible")
            ],
            required=True
        ),
        Question(
            id="q_emergency_2",
            text="이 목표를 위해 투자할 수 있는 자원은?",
            type="multiple",
            options=[
                Option(id="opt_time", text="주로 시간", value="time"),
                Option(id="opt_money", text="주로 돈", value="money"),
                Option(id="opt_both", text="시간과 돈 모두", value="both"),
                Option(id="opt_minimal", text="최소한만", value="minimal")
            ],
            required=True
        ),
        Question(
            id="q_emergency_3",
            text="가장 중요하게 생각하는 것은?",
            type="multiple",
            options=[
                Option(id="opt_speed", text="빠른 달성", value="speed"),
                Option(id="opt_quality", text="높은 품질", value="quality"),
                Option(id="opt_cost", text="비용 절약", value="cost"),
                Option(id="opt_balance", text="균형잡힌 접근", value="balance")
            ],
            required=True
        )
    ]

# 기존 엔드포인트들도 유지 (하위 호환성)
@router.get("/generate/{intent_id}")
async def generate_questions_legacy(
    intent_id: str, 
    current_user=Depends(get_current_user)
):
    """기존 GET 방식 엔드포인트 (하위 호환성용)"""
    logger.warning("Legacy GET endpoint used - please migrate to POST /generate")
    
    raise HTTPException(
        status_code=410,
        detail="이 엔드포인트는 더 이상 지원되지 않습니다. POST /questions/generate를 사용해주세요."
    )