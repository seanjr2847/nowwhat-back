from fastapi import APIRouter, HTTPException, Depends, Request
from app.schemas.nowwhat import (
    Intent, IntentAnalyzeResponse, 
    IntentAnalyzeRequest, IntentAnalyzeApiResponse, IntentOption,
    SimpleTestRequest, SimpleTestResponse
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
import json

logger = logging.getLogger(__name__)

router = APIRouter()

@router.post("/test-simple", response_model=SimpleTestResponse)
async def test_simple_model(request: Request, simple_request: SimpleTestRequest):
    """간단한 모델을 사용한 테스트 엔드포인트"""
    try:
        logger.info(f"Simple test - Request headers: {dict(request.headers)}")
        logger.info(f"Simple test - Received simple_request: {simple_request}")
        logger.info(f"Simple test - Goal: {simple_request.goal}")
        
        return SimpleTestResponse(
            received_goal=simple_request.goal,
            success=True
        )
        
    except Exception as e:
        logger.error(f"Simple test error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/test-body")
async def test_request_body(request: Request):
    """요청 body 디버깅용 테스트 엔드포인트"""
    try:
        # 요청 헤더 로깅
        logger.info(f"Request headers: {dict(request.headers)}")
        
        # Content-Type 확인
        content_type = request.headers.get("content-type", "")
        logger.info(f"Content-Type: {content_type}")
        
        # Raw body 읽기
        body = await request.body()
        logger.info(f"Raw body (bytes): {body}")
        logger.info(f"Raw body (str): {body.decode('utf-8') if body else 'Empty'}")
        
        # JSON 파싱 시도
        try:
            if body:
                json_data = json.loads(body.decode('utf-8'))
                logger.info(f"Parsed JSON: {json_data}")
            else:
                json_data = None
                logger.info("No body data")
        except Exception as json_error:
            logger.error(f"JSON parsing error: {json_error}")
            json_data = None
        
        return {
            "success": True,
            "headers": dict(request.headers),
            "content_type": content_type,
            "raw_body": body.decode('utf-8') if body else None,
            "parsed_json": json_data,
            "body_length": len(body) if body else 0
        }
        
    except Exception as e:
        logger.error(f"Test endpoint error: {str(e)}")
        return {"error": str(e)}

@router.post("/debug-analyze")
async def debug_analyze_intents(request: Request):
    """analyze 엔드포인트를 단계별로 디버깅"""
    try:
        logger.info("=== DEBUG ANALYZE START ===")
        
        # 1. Raw body 읽기
        body = await request.body()
        logger.info(f"1. Raw body: {body.decode('utf-8') if body else 'Empty'}")
        
        # 2. JSON 파싱
        if body:
            json_data = json.loads(body.decode('utf-8'))
            goal = json_data.get('goal', '')
            logger.info(f"2. Parsed goal: {goal}")
        else:
            return {"error": "No body"}
        
        # 3. Pydantic 모델 직접 생성 테스트
        try:
            intent_request = IntentAnalyzeRequest(goal=goal)
            logger.info(f"3. Pydantic model created: {intent_request}")
        except Exception as pydantic_error:
            logger.error(f"3. Pydantic error: {pydantic_error}")
            return {"error": f"Pydantic model error: {pydantic_error}"}
        
        # 4. 데이터베이스 연결 테스트 (dependency 없이)
        try:
            from app.core.database import SessionLocal
            db = SessionLocal()
            logger.info("4. Database connection created")
            db.close()
        except Exception as db_error:
            logger.error(f"4. Database error: {db_error}")
            return {"error": f"Database error: {db_error}"}
        
        # 5. IP 추출 테스트
        try:
            client_ip = get_client_ip(request)
            logger.info(f"5. Client IP: {client_ip}")
        except Exception as ip_error:
            logger.error(f"5. IP error: {ip_error}")
            return {"error": f"IP error: {ip_error}"}
        
        return {
            "success": True,
            "message": "All steps completed successfully",
            "goal": goal,
            "client_ip": client_ip
        }
        
    except Exception as e:
        logger.error(f"Debug analyze error: {str(e)}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return {"error": str(e), "traceback": traceback.format_exc()}

@router.post("/test-dependencies")
async def test_dependencies(request: Request, db: Session = Depends(get_db)):
    """각 dependency를 개별적으로 테스트"""
    results = {}
    
    # 1. 데이터베이스 연결 테스트
    try:
        from app.core.database import test_connection
        db_test = test_connection()
        results["database"] = {
            "status": "success" if db_test else "failed",
            "connection": db_test
        }
    except Exception as e:
        results["database"] = {
            "status": "error",
            "error": str(e)
        }
    
    # 2. Gemini 서비스 테스트
    try:
        from app.core.config import settings
        gemini_status = {
            "api_key_exists": bool(settings.GEMINI_API_KEY),
            "api_key_length": len(settings.GEMINI_API_KEY) if settings.GEMINI_API_KEY else 0
        }
        results["gemini"] = {
            "status": "configured" if settings.GEMINI_API_KEY else "missing_api_key",
            "details": gemini_status
        }
    except Exception as e:
        results["gemini"] = {
            "status": "error", 
            "error": str(e)
        }
    
    # 3. IP 유틸리티 테스트
    try:
        client_ip = get_client_ip(request)
        results["geo_utils"] = {
            "status": "success",
            "client_ip": client_ip
        }
    except Exception as e:
        results["geo_utils"] = {
            "status": "error",
            "error": str(e)
        }
    
    # 4. 세션 CRUD 테스트
    try:
        from app.crud.session import generate_session_id
        session_id = generate_session_id()
        results["session_crud"] = {
            "status": "success",
            "sample_session_id": session_id
        }
    except Exception as e:
        results["session_crud"] = {
            "status": "error",
            "error": str(e)
        }
    
    return {
        "success": True,
        "dependencies": results
    }

@router.post("/analyze", response_model=IntentAnalyzeApiResponse)
async def analyze_intents(
    request: Request,
    intent_request: IntentAnalyzeRequest,
    db: Session = Depends(get_db)
):
    """사용자 입력을 분석하여 의도 옵션 생성"""
    try:
        # 디버깅을 위한 추가 로깅
        logger.info("=== ANALYZE START ===")
        logger.info(f"Request headers: {dict(request.headers)}")
        logger.info(f"Received intent_request: {intent_request}")
        logger.info(f"Goal: {intent_request.goal}")
        
        # 1. 입력 검증 (Pydantic이 자동으로 처리하지만 추가 검증)
        goal = intent_request.goal.strip()
        if not goal:
            raise HTTPException(status_code=400, detail="목표를 입력해주세요.")
        
        logger.info("Step 1: Input validation completed")
        
        # 2. 클라이언트 IP 추출 및 국가 감지
        client_ip = get_client_ip(request)
        logger.info(f"Step 2: Client IP extracted: {client_ip}")
        
        user_country = await detect_country_from_ip(client_ip)
        logger.info(f"Step 3: Country detected: {user_country}")
        
        # 3. 세션 생성 및 DB 저장
        logger.info("Step 4: Creating intent session...")
        db_session = create_intent_session(
            db=db,
            goal=goal,
            user_ip=client_ip,
            user_country=user_country
        )
        logger.info(f"Step 4: Intent session created with ID: {db_session.session_id}")
        
        # 4. Gemini API를 통한 의도 분석
        logger.info("Step 5: Calling Gemini API...")
        intents = await gemini_service.analyze_intent(goal, user_country)
        logger.info(f"Step 5: Gemini API returned {len(intents)} intents")
        
        # 5. 생성된 의도 옵션을 DB에 업데이트
        logger.info("Step 6: Updating session with intents...")
        intents_data = [intent.dict() for intent in intents]
        update_intent_session_with_intents(
            db=db,
            session_id=db_session.session_id,
            intents=intents_data
        )
        logger.info("Step 6: Session updated successfully")
        
        # 6. 응답 반환
        logger.info("Step 7: Creating response...")
        response = IntentAnalyzeApiResponse(
            sessionId=db_session.session_id,
            intents=intents
        )
        logger.info("=== ANALYZE COMPLETED SUCCESSFULLY ===")
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Intent analysis failed: {str(e)}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
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