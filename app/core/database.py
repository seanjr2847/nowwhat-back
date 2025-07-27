# core/config.py
from pydantic_settings import BaseSettings
from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool
from sqlalchemy import text
from app.core.config import settings
import logging
import os

logger = logging.getLogger(__name__)

# Vercel serverless 환경을 위한 데이터베이스 설정
def get_database_url():
    """Vercel serverless 환경에 맞는 데이터베이스 URL 생성"""
    if not settings.DATABASE_URL:
        raise ValueError("DATABASE_URL environment variable is not set")
    
    # asyncpg -> psycopg 동기 드라이버로 변경
    url = settings.DATABASE_URL
    if url.startswith("postgresql+asyncpg://"):
        url = url.replace("postgresql+asyncpg://", "postgresql://")
    elif url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql://")
    
    return url

# Serverless 환경에 최적화된 엔진 설정
engine = create_engine(
    get_database_url(),
    # Serverless 환경을 위한 연결 풀 설정
    poolclass=StaticPool,
    pool_size=1,  # Serverless에서는 연결 수를 최소화
    max_overflow=0,  # 추가 연결 생성 방지
    pool_pre_ping=True,  # 연결 유효성 검사
    pool_recycle=300,  # 5분마다 연결 재생성
    connect_args={
        "connect_timeout": 10,
        "application_name": "nowwhat-api",
        "options": "-c default_transaction_isolation=read_committed"
    },
    echo=settings.ENV == "development"  # 개발 환경에서만 SQL 로깅
)

SessionLocal = sessionmaker(
    autocommit=False, 
    autoflush=False, 
    bind=engine,
    expire_on_commit=False  # Serverless에서 세션 만료 방지
)

Base = declarative_base()

def get_db() -> Session:
    """데이터베이스 세션 생성 및 관리"""
    db = None
    try:
        db = SessionLocal()
        yield db
    except Exception as e:
        logger.error(f"Database session error: {e}")
        if db:
            db.rollback()
        raise
    finally:
        if db:
            try:
                db.close()
            except Exception as e:
                logger.error(f"Error closing database session: {e}")

def create_tables():
    """데이터베이스 테이블 생성"""
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables created successfully")
    except Exception as e:
        logger.error(f"Error creating database tables: {e}")
        raise

def test_connection():
    """데이터베이스 연결 테스트"""
    try:
        with engine.connect() as conn:
            conn.execute("SELECT 1")
        logger.info("Database connection test successful")
        return True
    except Exception as e:
        logger.error(f"Database connection test failed: {e}")
        return False