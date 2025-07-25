from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from app.schemas.nowwhat import ErrorResponse
from app.core.config import settings
from app.api.v1.api import api_router
from app.core.database import create_tables, test_connection
import logging

# 로깅 설정
logging.basicConfig(level=getattr(logging, settings.LOG_LEVEL))
logger = logging.getLogger(__name__)

app = FastAPI(
    title="NowWhat API Server",
    description="인텐트 분석 및 체크리스트 생성을 위한 API 서버",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS 미들웨어 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API 라우터 포함
app.include_router(api_router, prefix="/api/v1")

# 전역 예외 핸들러
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
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

# Vercel 서버리스 환경에서는 startup 이벤트 대신 첫 요청 시 초기화
_db_initialized = False

async def initialize_database():
    """데이터베이스 초기화 (한 번만 실행)"""
    global _db_initialized
    if not _db_initialized:
        try:
            logger.info("Testing database connection...")
            await test_connection()
            logger.info("✅ Database connection successful!")
            
            logger.info("Creating database tables...")
            await create_tables()
            logger.info("✅ Database tables ready!")
            
            _db_initialized = True
        except Exception as e:
            logger.error(f"❌ Database initialization failed: {e}")
            # Vercel에서는 데이터베이스 연결 실패해도 서버는 계속 실행

@app.get("/")
async def root():
    """루트 엔드포인트 - 서비스 정보 반환"""
    await initialize_database()  # 첫 요청 시 DB 초기화
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
    try:
        await test_connection()
        db_status = "connected"
    except Exception as e:
        logger.warning(f"Database health check failed: {e}")
        db_status = "disconnected"
    
    return {
        "status": "healthy",
        "database": db_status,
        "version": "1.0.0"
    }

# Vercel용 handler (필요한 경우)
handler = app