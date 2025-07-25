# core/config.py
from pydantic_settings import BaseSettings
from typing import List

class Settings(BaseSettings):
    # 서버 설정
    PORT: int = 8000
    HOST: str = "0.0.0.0"
    ENV: str = "development"
    
    # Neon PostgreSQL 데이터베이스 설정
    DATABASE_URL: str = "postgresql+asyncpg://neondb_owner:npg_0PAEIUGMxJq6@ep-orange-hall-ad5vlgl8-pooler.c-2.us-east-1.aws.neon.tech/neondb?sslmode=require"
    
    # JWT 설정
    SECRET_KEY: str = "nowwhat-super-secret-key-for-production-change-this"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # CORS 설정
    ALLOWED_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:8080", "*"]
    
    # 로깅 설정
    LOG_LEVEL: str = "INFO"
    
    # 레이트 리미팅 설정
    RATE_LIMIT_CALLS: int = 3
    RATE_LIMIT_PERIOD: int = 1
    
    # 노션 API 버전
    NOTION_VERSION: str = "2022-06-28"
    
    class Config:
        case_sensitive = True

settings = Settings()