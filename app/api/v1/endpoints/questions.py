from fastapi import APIRouter, HTTPException, Depends, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
import json
import asyncio
import uuid
from app.schemas.questions import (
    QuestionGenerateRequest, QuestionGenerateResponse, 
    Question, Option,
    QuestionAnswersRequest, QuestionAnswersResponse
)
from app.core.auth import get_current_user
from app.core.database import get_db
from app.services.gemini_service import gemini_service
# Removed geo utils for performance optimization
from app.crud.session import (
    validate_session_basic,
    save_question_set
)
from app.services.checklist_orchestrator import checklist_orchestrator, ChecklistGenerationError
from app.models.database import User
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
    2. Gemini API를 통한 맞춤 질문 생성 (goal + intentTitle 사용)
    3. 질문 세트 ID 생성 및 DB 저장
    4. 클라이언트 응답
    """
    try:
        # 요청에서 필수 정보 추출
        session_id = question_request.sessionId
        goal = question_request.goal
        intent_title = question_request.intentTitle
        user_country = question_request.userCountry  # 프론트에서 전달, None 가능
        user_language = question_request.userLanguage  # 프론트에서 전달, None 가능
        country_option = question_request.countryOption  # 지역정보 포함 여부
        
        logger.info(f"Question generation request - Session: {session_id}, Goal: '{goal}', Intent: '{intent_title}', Country: {user_country}, Language: {user_language}, CountryOption: {country_option}")
        
        # 1. 세션 유효성 검증 (의도 검증은 생략, 직접 전달받음)
        is_valid, db_session, error_message = validate_session_basic(
            db, session_id
        )
        
        if not is_valid:
            logger.warning(f"Session validation failed: {error_message}")
            raise HTTPException(status_code=400, detail=error_message)
        
        # 2. Gemini API를 통한 맞춤 질문 생성 (성능 최적화를 위해 국가 감지 제거)
        logger.info(f"Generating questions for goal: '{goal}', intent: '{intent_title}'")
        
        try:
            questions = await gemini_service.generate_questions(
                goal=goal,
                intent_title=intent_title,
                user_country=user_country,
                user_language=user_language,
                country_option=country_option
            )
            
            logger.info(f"Generated {len(questions)} questions via Gemini API")
            
        except Exception as e:
            logger.error(f"Gemini question generation failed: {str(e)}")
            # 캐시된 템플릿으로 대체는 이미 서비스 내부에서 처리됨
            questions = await gemini_service.generate_questions(
                goal=goal,
                intent_title=intent_title,
                user_country=user_country,
                user_language=user_language,
                country_option=country_option
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

@router.post("/answer", response_model=QuestionAnswersResponse)
async def submit_answers(
    request: QuestionAnswersRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """모든 답변을 한번에 제출하여 체크리스트 생성
    
    비즈니스 흐름:
    1. 요청 데이터 검증 (goal, selectedIntent, answers)
    2. 사용자 답변 데이터베이스 저장
    3. Gemini AI를 통한 기본 체크리스트 생성
    4. Gemini API를 통한 체크리스트 갯수에 따른 병렬 검색 실행
    5. 검색 결과와 AI 생성 결과 병합 및 보강
    6. 최종 체크리스트 데이터베이스 저장
    7. 체크리스트 ID 및 리다이렉트 URL 반환
    """
    try:
        # 요청 데이터 로깅
        logger.info(f"Answer submission request - User: {current_user.id}, Goal: '{request.goal}', Intent: '{request.selectedIntent}', Answers: {len(request.answers)}")
        
        # 입력 데이터 검증
        if not request.goal.strip():
            raise HTTPException(status_code=400, detail="목표(goal)는 필수입니다.")
        
        if not request.selectedIntent.strip():
            raise HTTPException(status_code=400, detail="선택된 의도(selectedIntent)는 필수입니다.")
        
        if not request.answers or len(request.answers) == 0:
            raise HTTPException(status_code=400, detail="답변(answers)은 최소 1개 이상 필요합니다.")
        
        # 답변 내용 검증
        for i, answer in enumerate(request.answers):
            if not answer.questionText.strip():
                raise HTTPException(status_code=400, detail=f"질문 {i+1}의 내용이 비어있습니다.")
            
            # answer가 문자열이거나 리스트인지 확인
            if not answer.answer:
                raise HTTPException(status_code=400, detail=f"질문 {i+1}의 답변이 비어있습니다.")
            
            if isinstance(answer.answer, list) and len(answer.answer) == 0:
                raise HTTPException(status_code=400, detail=f"질문 {i+1}의 답변이 비어있습니다.")
        
        logger.info(f"Request validation successful for user {current_user.id}")
        
        # 체크리스트 생성 오케스트레이션 실행
        try:
            response = await checklist_orchestrator.process_answers_to_checklist(
                request=request,
                user=current_user,
                db=db
            )
            
            logger.info(f"Checklist generation successful: {response.checklistId}")
            return response
            
        except ChecklistGenerationError as e:
            logger.error(f"Checklist generation error for user {current_user.id}: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))
        
        except Exception as e:
            logger.error(f"Unexpected error during checklist generation: {str(e)}")
            raise HTTPException(
                status_code=500, 
                detail="체크리스트 생성 중 서버 오류가 발생했습니다. 잠시 후 다시 시도해주세요."
            )
    
    except HTTPException:
        # FastAPI HTTPException은 그대로 전파
        raise
    
    except Exception as e:
        # 예상치 못한 모든 오류 처리
        logger.error(f"Unexpected error in submit_answers endpoint: {str(e)}")
        raise HTTPException(
            status_code=500, 
            detail="서버 내부 오류가 발생했습니다. 관리자에게 문의해주세요."
        )

@router.post("/generate/stream")
async def generate_questions_stream(
    request: Request,
    question_request: QuestionGenerateRequest,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """선택된 의도에 따른 맞춤 질문 생성 (스트리밍 버전)
    
    Server-Sent Events (SSE) 형식으로 실시간 응답을 제공합니다.
    """
    try:
        # 요청에서 필수 정보 추출
        session_id = question_request.sessionId
        goal = question_request.goal
        intent_title = question_request.intentTitle
        user_country = question_request.userCountry
        user_language = question_request.userLanguage
        country_option = question_request.countryOption
        
        # 스트리밍 요청 고유 ID 생성
        stream_id = str(uuid.uuid4())[:8]
        logger.info(f"🌊 API: Streaming request [{stream_id}] - Session: {session_id}, Goal: '{goal}', Intent: '{intent_title}', CountryOption: {country_option}")
        
        # 1. 세션 유효성 검증
        is_valid, db_session, error_message = validate_session_basic(db, session_id)
        
        if not is_valid:
            logger.warning(f"Session validation failed: {error_message}")
            
            async def error_stream():
                error_data = {"error": error_message, "status": "error"}
                yield f"data: {json.dumps(error_data, ensure_ascii=False)}\n\n"
                yield f"data: [DONE]\n\n"
            
            return StreamingResponse(
                error_stream(),
                media_type="text/plain",
                headers={
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                    "Access-Control-Allow-Origin": "*",
                    "Access-Control-Allow-Headers": "*"
                }
            )
        
        # 2. 스트리밍 응답 생성
        async def question_stream():
            try:
                # 시작 신호
                start_data = {"status": "started", "message": f"질문 생성을 시작합니다... [{stream_id}]"}
                yield f"data: {json.dumps(start_data, ensure_ascii=False)}\n\n"
                
                logger.info(f"🌊 Starting Gemini stream [{stream_id}]")
                
                # Gemini 스트리밍 호출
                async for chunk in gemini_service.generate_questions_stream(
                    goal=goal,
                    intent_title=intent_title,
                    user_country=user_country,
                    user_language=user_language,
                    country_option=country_option
                ):
                    chunk_data = {
                        "status": "generating",
                        "chunk": chunk,
                        "timestamp": asyncio.get_event_loop().time()
                    }
                    yield f"data: {json.dumps(chunk_data, ensure_ascii=False)}\n\n"
                
                # 완료 신호
                logger.info(f"🌊 Stream completed [{stream_id}]")
                complete_data = {"status": "completed", "message": f"질문 생성이 완료되었습니다. [{stream_id}]"}
                yield f"data: {json.dumps(complete_data, ensure_ascii=False)}\n\n"
                yield f"data: [DONE]\n\n"
                
            except Exception as e:
                logger.error(f"🌊 Streaming error [{stream_id}]: {str(e)}")
                error_data = {"status": "error", "error": str(e)}
                yield f"data: {json.dumps(error_data, ensure_ascii=False)}\n\n"
                yield f"data: [DONE]\n\n"
        
        return StreamingResponse(
            question_stream(),
            media_type="text/plain",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Headers": "*",
                "X-Accel-Buffering": "no"  # Nginx 버퍼링 비활성화
            }
        )
        
    except Exception as e:
        logger.error(f"Streaming endpoint error: {str(e)}")
        raise HTTPException(status_code=500, detail="스트리밍 처리 중 오류가 발생했습니다.")

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