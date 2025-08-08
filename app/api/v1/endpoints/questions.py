from fastapi import APIRouter, HTTPException, Depends, Request
from fastapi.responses import StreamingResponse, Response
from sqlalchemy.orm import Session
import json
import asyncio
import os
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
from app.core.config import settings
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

router = APIRouter()


def get_cors_headers(request: Request = None) -> dict:
    """동적 CORS 헤더 생성"""
    # 요청의 Origin 헤더 확인
    origin = None
    if request:
        origin = request.headers.get("origin")
        logger.debug(f"Request origin: {origin}")
    
    # 허용된 Origin 확인 및 결정
    allowed_origin = None
    
    if origin:
        # 정확한 매치 확인
        if origin in settings.ALLOWED_ORIGINS:
            allowed_origin = origin
        # Vercel 도메인 패턴 확인
        elif origin.endswith(".vercel.app") and ("nowwhat-front" in origin):
            allowed_origin = origin
            logger.info(f"Allowing Vercel domain: {origin}")
        # 개발 환경에서는 localhost 패턴 허용
        elif settings.ENV == "development" and ("localhost" in origin or "127.0.0.1" in origin):
            allowed_origin = origin
    
    # 기본값 설정
    if not allowed_origin:
        allowed_origin = settings.ALLOWED_ORIGINS[0] if settings.ALLOWED_ORIGINS else "https://nowwhat-front.vercel.app"
    
    headers = {
        "Access-Control-Allow-Origin": allowed_origin,
        "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type, Authorization, Accept, X-Requested-With",
        "Access-Control-Allow-Credentials": "true",
        "Access-Control-Max-Age": "86400",  # 24시간
        "Access-Control-Expose-Headers": "*"
    }
    
    logger.debug(f"CORS headers: {headers}")
    return headers


# JSON 완전성 검증 함수
async def verify_json_completeness(content: str, stream_id: str) -> bool:
    """스트리밍된 JSON 데이터의 완전성 검증"""
    try:
        if not content or len(content.strip()) < 50:
            logger.warning(f"🚨 Content too short [{stream_id}]: {len(content)} chars")
            return False
        
        # 마크다운 블록에서 JSON 추출
        clean_content = content.strip()
        if '```json' in clean_content:
            start = clean_content.find('```json') + 7
            end = clean_content.rfind('```')
            if end > start:
                clean_content = clean_content[start:end].strip()
        
        # JSON 파싱 시도
        try:
            parsed = json.loads(clean_content)
        except json.JSONDecodeError as e:
            logger.warning(f"🚨 JSON parsing failed [{stream_id}]: {str(e)}")
            return False
        
        # 기본 구조 검증
        if not isinstance(parsed, dict) or 'questions' not in parsed:
            logger.warning(f"🚨 Invalid structure [{stream_id}]: missing 'questions' field")
            return False
        
        questions = parsed['questions']
        if not isinstance(questions, list) or len(questions) == 0:
            logger.warning(f"🚨 Invalid questions [{stream_id}]: not a list or empty")
            return False
        
        # 각 질문의 필수 필드 검증
        for i, question in enumerate(questions):
            if not isinstance(question, dict):
                logger.warning(f"🚨 Question {i} invalid [{stream_id}]: not a dict")
                return False
            
            required_fields = ['id', 'text', 'type', 'options']
            for field in required_fields:
                if field not in question:
                    logger.warning(f"🚨 Question {i} missing '{field}' [{stream_id}]")
                    return False
            
            # 옵션 검증
            if question['type'] == 'multiple':
                options = question['options']
                if not isinstance(options, list) or len(options) == 0:
                    logger.warning(f"🚨 Question {i} invalid options [{stream_id}]")
                    return False
                
                # 각 옵션이 완전한지 검증
                for j, option in enumerate(options):
                    if isinstance(option, dict):
                        if 'text' not in option or not option['text']:
                            logger.warning(f"🚨 Question {i}, Option {j} incomplete text [{stream_id}]")
                            return False
                        
                        # 텍스트가 중간에 잘렸는지 검증 (괄호나 따옴표가 열려있는지)
                        text = option['text']
                        if text.count('(') != text.count(')') or text.count('"') % 2 != 0:
                            logger.warning(f"🚨 Question {i}, Option {j} truncated text [{stream_id}]: '{text}'")
                            return False
        
        logger.info(f"✅ JSON validation passed [{stream_id}]: {len(questions)} questions verified")
        return True
        
    except Exception as e:
        logger.error(f"🚨 JSON validation error [{stream_id}]: {str(e)}")
        return False


# 향상된 JSON 검증 및 자동 수정 함수
async def verify_and_fix_json_completeness(content: str, stream_id: str) -> tuple[bool, list]:
    """JSON 완전성 검증하고 불완전한 경우 최대한 복구 시도"""
    try:
        if not content or len(content.strip()) < 50:
            logger.warning(f"🚨 Content too short [{stream_id}]: {len(content)} chars")
            return False, []
        
        # 마크다운 블록에서 JSON 추출
        clean_content = content.strip()
        if '```json' in clean_content:
            start = clean_content.find('```json') + 7
            end = clean_content.rfind('```')
            if end > start:
                clean_content = clean_content[start:end].strip()
            else:
                # 마크다운 블록이 닫히지 않은 경우 - 마지막 ``` 없이 처리
                clean_content = clean_content[clean_content.find('```json') + 7:].strip()
        
        # JSON 파싱 시도
        try:
            parsed = json.loads(clean_content)
            questions = parsed.get('questions', [])
            
            # 완전한 구조인지 검증
            valid_questions = []
            for i, question in enumerate(questions):
                if isinstance(question, dict) and all(field in question for field in ['id', 'text', 'type', 'options']):
                    # 옵션 검증 및 수정
                    if question['type'] == 'multiple' and isinstance(question['options'], list):
                        fixed_options = []
                        for option in question['options']:
                            if isinstance(option, dict) and 'text' in option and option['text']:
                                # 불완전한 텍스트 감지 및 수정
                                text = option['text']
                                if text.count('(') != text.count(')'):
                                    # 열린 괄호가 있으면 닫아줌
                                    text += ')' * (text.count('(') - text.count(')'))
                                    option['text'] = text
                                    logger.info(f"🔧 Auto-fixed unbalanced parentheses in question {i} [{stream_id}]")
                                
                                # id와 value 필드가 없으면 생성
                                if 'id' not in option:
                                    option['id'] = f"opt_{len(fixed_options) + 1}"
                                if 'value' not in option:
                                    option['value'] = option['id']
                                
                                fixed_options.append(option)
                        
                        question['options'] = fixed_options
                        if len(fixed_options) > 0:  # 최소 하나의 유효한 옵션이 있는 경우만 포함
                            valid_questions.append(question)
            
            if len(valid_questions) > 0:
                logger.info(f"✅ JSON validated with fixes [{stream_id}]: {len(valid_questions)} valid questions")
                return True, valid_questions
            
        except json.JSONDecodeError as e:
            # JSON 파싱 실패 시 부분적 복구 시도
            logger.info(f"🔧 Attempting partial JSON recovery [{stream_id}]: {str(e)}")
            recovered_questions = attempt_partial_json_recovery(clean_content, stream_id)
            if recovered_questions:
                return True, recovered_questions
        
        logger.warning(f"🚨 Could not validate or fix JSON [{stream_id}]")
        return False, []
        
    except Exception as e:
        logger.error(f"🚨 JSON validation/fix error [{stream_id}]: {str(e)}")
        return False, []


def attempt_partial_json_recovery(content: str, stream_id: str) -> list:
    """부분적으로 손상된 JSON에서 최대한 질문 데이터 복구"""
    try:
        # 완전하지 않은 JSON에서 질문 객체들 추출 시도
        questions = []
        
        # "questions": [ 이후 부분 찾기
        start_marker = '"questions"'
        if start_marker in content:
            questions_start = content.find(start_marker)
            bracket_start = content.find('[', questions_start)
            if bracket_start != -1:
                # 각 질문 객체를 개별적으로 파싱 시도
                remaining = content[bracket_start + 1:]
                question_objects = []
                
                # { 로 시작하는 객체들 찾기
                brace_count = 0
                current_obj = ""
                for char in remaining:
                    if char == '{':
                        if brace_count == 0:
                            current_obj = "{"
                        else:
                            current_obj += char
                        brace_count += 1
                    elif char == '}':
                        current_obj += char
                        brace_count -= 1
                        if brace_count == 0 and current_obj:
                            # 완성된 객체 파싱 시도
                            try:
                                question_obj = json.loads(current_obj)
                                if isinstance(question_obj, dict) and 'text' in question_obj:
                                    # 최소 필수 필드 보완
                                    if 'id' not in question_obj:
                                        question_obj['id'] = f"recovered_q_{len(question_objects) + 1}"
                                    if 'type' not in question_obj:
                                        question_obj['type'] = "multiple"
                                    if 'options' not in question_obj or not question_obj['options']:
                                        question_obj['options'] = [{"id": "opt_1", "text": "기타", "value": "other"}]
                                    
                                    question_objects.append(question_obj)
                                    logger.info(f"🔧 Recovered question object [{stream_id}]: {question_obj.get('text', '')[:50]}...")
                                    
                            except json.JSONDecodeError:
                                pass  # 개별 객체 파싱 실패는 무시
                            current_obj = ""
                    else:
                        if brace_count > 0:
                            current_obj += char
                
                if question_objects:
                    logger.info(f"✅ Partial recovery successful [{stream_id}]: {len(question_objects)} questions recovered")
                    return question_objects
        
        logger.warning(f"🚨 Partial recovery failed [{stream_id}]")
        return []
        
    except Exception as e:
        logger.error(f"🚨 Partial recovery error [{stream_id}]: {str(e)}")
        return []


# 인라인 폴백 질문 생성 함수
async def generate_fallback_questions_inline(goal: str, intent_title: str, user_country: str, user_language: str, country_option: bool) -> str:
    """스트리밍 실패 시 즉시 완전한 질문 생성"""
    try:
        logger.info(f"🚀 Generating immediate fallback questions for: {goal} (intent: {intent_title})")
        
        # GeminiService의 일반 API로 완전한 질문 생성 (스트리밍 아님)
        questions = await gemini_service.generate_questions(
            goal=goal,
            intent_title=intent_title,
            user_country=user_country,
            user_language=user_language,
            country_option=country_option
        )
        
        if questions and len(questions) > 0:
            # 완전한 JSON 형태로 변환
            questions_data = [{
                "id": q.id,
                "text": q.text,
                "type": q.type,
                "options": [{
                    "id": opt.id,
                    "text": opt.text,
                    "value": opt.value
                } for opt in q.options] if hasattr(q, 'options') and q.options else [],
                "category": getattr(q, 'category', 'general')
            } for q in questions]
            
            fallback_json = json.dumps({"questions": questions_data}, ensure_ascii=False, indent=2)
            logger.info(f"✅ Immediate fallback generated: {len(questions)} questions, {len(fallback_json)} chars")
            return fallback_json
        
    except Exception as e:
        logger.error(f"🚨 Immediate fallback generation failed: {str(e)}")
        
        # 최후의 수단: 하드코딩된 기본 질문
        default_questions = {
            "questions": [
                {
                    "id": "default_q1",
                    "text": f"{intent_title}을(를) 위해 가장 중요하게 생각하는 것은 무엇인가요?",
                    "type": "multiple",
                    "options": [
                        {"id": "opt_quality", "text": "품질과 완성도", "value": "quality"},
                        {"id": "opt_speed", "text": "빠른 시작과 진행", "value": "speed"},
                        {"id": "opt_cost", "text": "비용 효율성", "value": "cost"},
                        {"id": "opt_learning", "text": "학습과 경험", "value": "learning"}
                    ],
                    "category": "priority"
                }
            ]
        }
        return json.dumps(default_questions, ensure_ascii=False, indent=2)
    
    return None

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

@router.options("/generate/stream")
async def options_generate_questions_stream(request: Request):
    """스트리밍 엔드포인트를 위한 프리플라이트 CORS 처리"""
    return Response(
        status_code=200,
        headers=get_cors_headers(request)
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
    stream_id = None
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
            
            cors_headers = get_cors_headers(request)
            streaming_headers = {
                "Cache-Control": "no-cache, no-store, must-revalidate",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
                "Pragma": "no-cache",
                "Expires": "0"
            }
            streaming_headers.update(cors_headers)
            
            # 에러 응답에도 CORS 헤더 강화
            response = StreamingResponse(
                error_stream(),
                media_type="text/plain; charset=utf-8",
                headers=streaming_headers
            )
            
            # 추가적으로 CORS 헤더 직접 설정
            response.headers["Access-Control-Allow-Origin"] = cors_headers.get("Access-Control-Allow-Origin", "https://nowwhat-front.vercel.app")
            response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
            response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization, Accept, X-Requested-With"
            response.headers["Access-Control-Allow-Credentials"] = "true"
            
            return response
        
        # 2. 스트리밍 응답 생성 (Vercel 서버리스 환경 최적화)
        async def question_stream():
            accumulated_content = ""
            try:
                # Pro Plan 환경 최적화
                is_vercel = os.getenv("VERCEL") == "1"
                logger.info(f"🌊 Environment detection [{stream_id}]: Vercel={is_vercel} (Pro Plan)")
                
                # 시작 신호
                start_data = {"status": "started", "message": f"질문 생성을 시작합니다... [{stream_id}]"}
                yield f"data: {json.dumps(start_data, ensure_ascii=False)}\n\n"
                
                # 연결 상태 체크를 위한 초기 flush
                await asyncio.sleep(0.1)
                
                # Pro Plan에서 실제 스트리밍 시도 (더 공격적으로)
                logger.info(f"🌊 Pro Plan streaming attempt [{stream_id}]")
                
                # Gemini 스트리밍 호출 (Pro Plan 최적화, 타임아웃 보호)
                try:
                    streaming_task = gemini_service.generate_questions_stream(
                        goal=goal,
                        intent_title=intent_title,
                        user_country=user_country,
                        user_language=user_language,
                        country_option=country_option
                    )
                    
                    # 타임아웃을 가진 스트리밍 처리
                    start_time = asyncio.get_event_loop().time()
                    async for chunk in streaming_task:
                        # 90초 타임아웃 체크
                        if asyncio.get_event_loop().time() - start_time > 90:
                            logger.warning(f"🕒 Manual timeout triggered [{stream_id}]")
                            raise asyncio.TimeoutError("Manual timeout after 90 seconds")
                        
                        accumulated_content += chunk
                        chunk_data = {
                            "status": "generating", 
                            "chunk": chunk,
                            "timestamp": asyncio.get_event_loop().time()
                        }
                        yield f"data: {json.dumps(chunk_data, ensure_ascii=False)}\n\n"
                        
                        # 연결 상태 주기적 체크
                        await asyncio.sleep(0.01)
                            
                except (asyncio.TimeoutError, OSError, BrokenPipeError) as timeout_error:
                    logger.warning(f"🕒 Streaming timeout or connection lost [{stream_id}]: {str(timeout_error)}")
                    
                    # 타임아웃 시 즉시 폴백 데이터 생성
                    fallback_content = await generate_fallback_questions_inline(
                        goal, intent_title, user_country, user_language, country_option
                    )
                    if fallback_content:
                        yield f"data: {json.dumps({'status': 'timeout_recovery', 'chunk': fallback_content}, ensure_ascii=False)}\n\n"
                        accumulated_content = fallback_content
                    else:
                        # 최후의 수단
                        error_data = {"status": "error", "message": "스트리밍 타임아웃이 발생했습니다. 일반 API를 사용해주세요."}
                        yield f"data: {json.dumps(error_data, ensure_ascii=False)}\n\n"
                        return
                
                logger.info(f"🌊 Primary stream completed [{stream_id}], accumulated: {len(accumulated_content)} chars")
                
                # 최종 JSON 완전성 검증
                is_complete, parsed_questions = await verify_and_fix_json_completeness(accumulated_content, stream_id)
                
                if is_complete:
                    # 완료 신호 (정상)
                    complete_data = {
                        "status": "completed", 
                        "message": f"질문 생성이 완료되었습니다. [{stream_id}]",
                        "validated": True,
                        "total_chars": len(accumulated_content)
                    }
                    yield f"data: {json.dumps(complete_data, ensure_ascii=False)}\n\n"
                else:
                    # 불완전한 데이터 감지 시 자동으로 완성하여 전송
                    logger.warning(f"🚨 Incomplete JSON detected [{stream_id}], auto-completing and sending full data")
                    
                    # 자동 완성 또는 폴백 데이터 생성
                    if parsed_questions:
                        # 부분적으로 파싱된 데이터가 있으면 완성
                        fixed_json = json.dumps({"questions": parsed_questions}, ensure_ascii=False, indent=2)
                        yield f"data: {json.dumps({'status': 'fixed_partial', 'chunk': fixed_json}, ensure_ascii=False)}\n\n"
                        logger.info(f"✅ Auto-completed partial data [{stream_id}]: {len(parsed_questions)} questions")
                    else:
                        # 아예 파싱 불가능한 경우 새로 생성
                        logger.info(f"🔄 Generating fresh questions due to corrupted stream [{stream_id}]")
                        fallback_questions = await generate_fallback_questions_inline(
                            goal, intent_title, user_country, user_language, country_option
                        )
                        if fallback_questions:
                            yield f"data: {json.dumps({'status': 'regenerated', 'chunk': fallback_questions}, ensure_ascii=False)}\n\n"
                            logger.info(f"✅ Fresh questions generated and sent [{stream_id}]")
                    
                    # 어떤 경우든 사용자는 완전한 데이터를 받았다고 알림
                    complete_data = {
                        "status": "completed",
                        "message": f"질문 생성이 완료되었습니다. [{stream_id}]",
                        "auto_completed": True
                    }
                    yield f"data: {json.dumps(complete_data, ensure_ascii=False)}\n\n"
                
                # [DONE] 신호 전솨 전 마지막 검증
                await asyncio.sleep(0.1)  # 짧은 대기 시간
                yield f"data: [DONE]\n\n"
                
            except Exception as e:
                logger.error(f"🚨 Enhanced streaming error [{stream_id}]: {str(e)}")
                import traceback
                logger.error(f"🚨 Stack trace [{stream_id}]: {traceback.format_exc()}")
                
                # 스트리밍 오류 시에도 완전한 질문 제공 시도
                try:
                    fallback_content = await generate_fallback_questions_inline(
                        goal, intent_title, user_country, user_language, country_option
                    )
                    if fallback_content:
                        yield f"data: {json.dumps({'status': 'error_recovery', 'chunk': fallback_content}, ensure_ascii=False)}\n\n"
                        yield f"data: {json.dumps({'status': 'completed', 'message': '오류 복구 완료'}, ensure_ascii=False)}\n\n"
                        yield f"data: [DONE]\n\n"
                        return
                except:
                    pass  # 폴백도 실패하면 아래 오류 응답으로
                
                error_data = {
                    "status": "error", 
                    "error": str(e),
                    "stream_id": stream_id,
                    "accumulated_chars": len(accumulated_content),
                    "recovery_suggestion": "비스트리밍 버전(일반 API)을 사용해주세요."
                }
                yield f"data: {json.dumps(error_data, ensure_ascii=False)}\n\n"
                yield f"data: [DONE]\n\n"
        
        # CORS 헤더와 스트리밍 헤더 합치기
        cors_headers = get_cors_headers(request)
        streaming_headers = {
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Nginx 버퍼링 비활성화
            "Transfer-Encoding": "chunked",  # 청크 전송 명시
            "Pragma": "no-cache",
            "Expires": "0"
        }
        streaming_headers.update(cors_headers)
        
        # CORS 헤더 강화 - 확실히 적용하기 위해 별도 설정
        response = StreamingResponse(
            question_stream(),
            media_type="text/plain; charset=utf-8",
            headers=streaming_headers
        )
        
        # 추가적으로 CORS 헤더 직접 설정
        response.headers["Access-Control-Allow-Origin"] = cors_headers.get("Access-Control-Allow-Origin", "https://nowwhat-front.vercel.app")
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
        response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization, Accept, X-Requested-With"
        response.headers["Access-Control-Allow-Credentials"] = "true"
        
        return response
        
    except Exception as e:
        import traceback
        error_detail = f"Streaming error: {str(e)}\nTraceback: {traceback.format_exc()}"
        logger.error(f"🚨 Top-level streaming error [{stream_id}]: {error_detail}")
        
        # 최상위 예외에서도 스트리밍 응답으로 처리
        async def error_recovery_stream():
            try:
                # 오류 발생 시에도 완전한 질문 제공 시도
                fallback_content = await generate_fallback_questions_inline(
                    question_request.goal, 
                    question_request.intentTitle,
                    question_request.userCountry, 
                    question_request.userLanguage, 
                    question_request.countryOption
                )
                if fallback_content:
                    yield f"data: {json.dumps({'status': 'emergency_recovery', 'chunk': fallback_content}, ensure_ascii=False)}\n\n"
                    yield f"data: {json.dumps({'status': 'completed', 'message': '긴급 복구 완료'}, ensure_ascii=False)}\n\n"
                else:
                    # 최후의 수단
                    error_data = {"status": "error", "message": "서버 오류가 발생했습니다. 잠시 후 다시 시도해주세요."}
                    yield f"data: {json.dumps(error_data, ensure_ascii=False)}\n\n"
            except:
                error_data = {"status": "error", "message": "심각한 오류가 발생했습니다. 페이지를 새로고침해주세요."}
                yield f"data: {json.dumps(error_data, ensure_ascii=False)}\n\n"
            finally:
                yield f"data: [DONE]\n\n"
        
        # CORS 헤더 포함한 스트리밍 응답
        cors_headers = get_cors_headers(request)
        streaming_headers = {
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
            "Pragma": "no-cache",
            "Expires": "0"
        }
        streaming_headers.update(cors_headers)
        
        response = StreamingResponse(
            error_recovery_stream(),
            media_type="text/plain; charset=utf-8",
            headers=streaming_headers
        )
        
        # 추가 CORS 헤더 설정
        response.headers["Access-Control-Allow-Origin"] = cors_headers.get("Access-Control-Allow-Origin", "https://nowwhat-front.vercel.app")
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
        response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization, Accept, X-Requested-With"
        response.headers["Access-Control-Allow-Credentials"] = "true"
        
        return response

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