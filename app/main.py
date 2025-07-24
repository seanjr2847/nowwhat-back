from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from app.api.v1.api import api_router
from app.schemas.nowwhat import ErrorResponse
from app.core.config import settings

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

# API 라우터 등록
app.include_router(api_router, prefix="/api/v1")

# 글로벌 예외 핸들러
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content=ErrorResponse(
            success=False,
            error="internal_server_error",
            message="내부 서버 오류가 발생했습니다."
        )
    )

@app.get("/")
async def root():
    return {
        "service": "NowWhat API Server", 
        "version": "1.0.0",
        "description": "체크리스트 기반 목표 달성 서비스",
        "docs": "/docs"
    }

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "nowwhat-api"}