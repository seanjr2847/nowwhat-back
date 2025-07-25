from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from app.api.v1.api import api_router
from app.schemas.nowwhat import ErrorResponse
from app.core.config import settings
from app.core.database import create_tables, test_connection
import logging

logger = logging.getLogger(__name__)

app = FastAPI(
    title="NowWhat API Server",
    description="체크리스트 기반 목표 달성 서비스 API",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS 미들웨어 추가
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 애플리케이션 시작 시 이벤트
@app.on_event("startup")
async def startup_event():
    """서버 시작 시 데이터베이스 연결 및 테이블 생성"""
    logger.info("Starting NowWhat API Server...")
    
    # 데이터베이스 연결 테스트
    connection_ok = await test_connection()
    if connection_ok:
        logger.info("✅ Database connection successful")
        
        # 테이블 생성 (필요한 경우)
        try:
            await create_tables()
            logger.info("✅ Database tables ready")
        except Exception as e:
            logger.error(f"❌ Failed to create tables: {e}")
    else:
        logger.error("❌ Database connection failed - running with limited functionality")

# API 라우터 등록
app.include_router(api_router, prefix="/api/v1")

# 글로벌 예외 핸들러
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Global exception: {exc}")
    return JSONResponse(
        status_code=500,
        content=ErrorResponse(
            success=False,
            error="internal_server_error",
            message="내부 서버 오류가 발생했습니다."
        ).dict()
    )

@app.get("/")
async def root():
    return {
        "service": "NowWhat API Server", 
        "version": "1.0.0",
        "description": "체크리스트 기반 목표 달성 서비스",
        "docs": "/docs",
        "database": "PostgreSQL"
    }

@app.get("/health")
async def health_check():
    # 데이터베이스 연결 상태 확인
    db_status = await test_connection()
    return {
        "status": "healthy" if db_status else "degraded", 
        "service": "nowwhat-api",
        "database": "connected" if db_status else "disconnected"
    }