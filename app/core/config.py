# core/config.py
from pydantic_settings import BaseSettings
from typing import List
import os

class Settings(BaseSettings):
    # 서버 설정
    PORT: int = int(os.getenv("PORT", "8000"))
    HOST: str = os.getenv("HOST", "0.0.0.0")
    ENV: str = os.getenv("ENV", "development")
    
    # Neon PostgreSQL 데이터베이스 설정
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL", 
        "postgresql+asyncpg://neondb_owner:npg_0PAEIUGMxJq6@ep-orange-hall-ad5vlgl8-pooler.c-2.us-east-1.aws.neon.tech/neondb?sslmode=require"
    )
    
    # JWT 설정
    SECRET_KEY: str = os.getenv("SECRET_KEY", "nowwhat-super-secret-key-for-production-change-this")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
    
    # CORS 설정
    ALLOWED_ORIGINS: List[str] = [
        "http://localhost:3000", 
        "http://localhost:8080", 
        "https://nowwhat-front.vercel.app",  # Vercel 프론트엔드 도메인
        "*"  # 개발용, 프로덕션에서는 제거 권장
    ]
    
    # 로깅 설정
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    
    # 레이트 리미팅 설정
    RATE_LIMIT_CALLS: int = int(os.getenv("RATE_LIMIT_CALLS", "100"))
    RATE_LIMIT_PERIOD: int = int(os.getenv("RATE_LIMIT_PERIOD", "60"))
    
    # 노션 API 버전
    NOTION_VERSION: str = "2022-06-28"
    
    class Config:
        case_sensitive = True
        # .env 파일 의존성 완전 제거

settings = Settings()