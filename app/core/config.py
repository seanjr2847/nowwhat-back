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
    DATABASE_URL: str = os.getenv("DATABASE_URL", "")
    
    # JWT 설정
    SECRET_KEY: str = os.getenv("SECRET_KEY", "nowwhat-super-secret-key-for-production-change-this")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
    
    # 구글 OAuth 설정
    GOOGLE_CLIENT_ID: str = os.getenv("GOOGLE_CLIENT_ID", "")
    GOOGLE_CLIENT_SECRET: str = os.getenv("GOOGLE_CLIENT_SECRET", "")
    
    # Gemini API 설정
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
    MAX_CONCURRENT_SEARCHES: int = int(os.getenv("MAX_CONCURRENT_SEARCHES", "15"))
    SEARCH_TIMEOUT_SECONDS: int = int(os.getenv("SEARCH_TIMEOUT_SECONDS", "15"))
    
    # CORS 설정 - 환경 변수 기반
    ALLOWED_ORIGINS: List[str] = []
    ALLOW_ALL_ORIGINS: bool = False
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # 환경 변수에서 CORS 도메인 읽기 (쉼표로 구분)
        cors_origins = os.getenv("ALLOWED_ORIGINS", "")
        
        # CORS_ALLOW_ALL 환경 변수가 true이면 모든 origin 허용 (개발용)
        allow_all = os.getenv("CORS_ALLOW_ALL", "false").lower() == "true"
        
        if allow_all and self.ENV == "development":
            self.ALLOW_ALL_ORIGINS = True
            self.ALLOWED_ORIGINS = ["*"]
        elif cors_origins:
            self.ALLOWED_ORIGINS = [origin.strip() for origin in cors_origins.split(",")]
        else:
            # 기본값 설정
            if self.ENV == "development":
                self.ALLOWED_ORIGINS = [
                    "http://localhost:3000",
                    "http://localhost:8080", 
                    "http://127.0.0.1:3000"
                ]
            else:
                # 프로덕션: 명시적 도메인들
                self.ALLOWED_ORIGINS = [
                    "https://nowwhat-front.vercel.app",
                    "https://nowwhat-front-git-main.vercel.app",
                ]
    
    # 로깅 설정
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    
    # 레이트 리미팅 설정
    RATE_LIMIT_CALLS: int = int(os.getenv("RATE_LIMIT_CALLS", "100"))
    RATE_LIMIT_PERIOD: int = int(os.getenv("RATE_LIMIT_PERIOD", "60"))
    
    # 체크리스트 생성 설정
    MIN_CHECKLIST_ITEMS: int = int(os.getenv("MIN_CHECKLIST_ITEMS", "8"))
    MAX_CHECKLIST_ITEMS: int = int(os.getenv("MAX_CHECKLIST_ITEMS", "15"))
    
    
    class Config:
        case_sensitive = True
        env_file = ".env"
        env_file_encoding = 'utf-8'
        extra = "ignore"  # 추가 환경변수 허용

settings = Settings()