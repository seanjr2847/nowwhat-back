from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from app.schemas.nowwhat import ErrorResponse
from app.core.config import settings
from app.api.v1.api import api_router
from app.core.database import reset_async_engine
import logging

# 로깅 설정
logging.basicConfig(level=getattr(logging, settings.LOG_LEVEL))
logger = logging.getLogger(__name__)

# FastAPI 앱 생성 - 단순한 구조
app = FastAPI(
    title="NowWhat API Server",
    description="인텐트 분석 및 체크리스트 생성을 위한 API 서버",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS 미들웨어 설정 - 안전한 방식
logger.info(f"CORS Origins: {settings.ALLOWED_ORIGINS}")
logger.info(f"Environment: {settings.ENV}")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# API 라우터 포함
app.include_router(api_router, prefix="/api/v1")

# 애플리케이션 시작 이벤트
@app.on_event("startup")
async def startup_event():
    """애플리케이션 시작 시 실행되는 이벤트"""
    logger.info("Application startup...")
    
    # 엔진 리셋으로 새로운 URL 적용
    reset_async_engine()
    logger.info("Database engine reset completed")
    
    # 프로덕션 환경에서 테이블 자동 생성
    try:
        from app.core.database import create_tables, test_connection
        logger.info("Testing database connection...")
        
        if test_connection():
            logger.info("Database connection successful")
            logger.info("Creating database tables...")
            create_tables()
            logger.info("Database tables created/verified successfully")
        else:
            logger.error("Database connection failed during startup")
    except Exception as e:
        logger.error(f"Database setup error during startup: {e}")
        # 에러가 발생해도 앱은 계속 실행 (기존 테이블이 있을 수 있음)
        pass

# 전역 예외 핸들러
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    # Broken pipe 에러는 클라이언트 연결 종료로 인한 정상적인 상황
    import errno
    if isinstance(exc, OSError) and exc.errno == errno.EPIPE:
        logger.warning(f"Client disconnected (broken pipe): {request.url}")
        return JSONResponse(status_code=200, content={"status": "client_disconnected"})
    
    logger.error(f"Global exception: {exc}")
    return JSONResponse(
        status_code=500,
        content=ErrorResponse(
            success=False,
            error={
                "code": "internal_server_error",
                "message": "서버 내부 오류가 발생했습니다."
            }
        ).dict()
    )

@app.get("/")
async def root():
    """루트 엔드포인트 - 서비스 정보 반환"""
    return {
        "service": "NowWhat API Server",
        "version": "1.0.0",
        "description": "인텐트 분석 및 체크리스트 생성을 위한 API 서버",
        "docs": "/docs",
        "health": "/health"
    }

@app.get("/health")
async def health_check():
    """헬스 체크 엔드포인트"""
    return {
        "status": "healthy",
        "version": "1.0.0"
    }