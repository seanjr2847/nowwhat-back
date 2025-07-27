# core/database.py
from sqlalchemy import create_engine, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import QueuePool, StaticPool
from app.core.config import settings
import logging
import os

logger = logging.getLogger(__name__)

# Vercel serverless 환경을 위한 데이터베이스 설정
def get_database_url():
    """환경에 맞는 데이터베이스 URL 생성"""
    if not settings.DATABASE_URL:
        # 로컬 개발용 기본 SQLite 데이터베이스
        return "sqlite:///./nowwhat.db"
    
    url = settings.DATABASE_URL
    
    # asyncpg -> psycopg 동기 드라이버로 변경 (PostgreSQL용)
    if url.startswith("postgresql+asyncpg://"):
        url = url.replace("postgresql+asyncpg://", "postgresql://")
    elif url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql://")
    
    return url

def get_engine_config():
    """데이터베이스 타입에 따른 엔진 설정 반환"""
    url = get_database_url()
    
    if url.startswith("sqlite"):
        # SQLite 설정
        return {
            "poolclass": StaticPool,
            "connect_args": {
                "check_same_thread": False  # SQLite는 멀티스레드 지원
            },
            "echo": settings.ENV == "development"
        }
    else:
        # PostgreSQL 설정 (Vercel 프로덕션)
        return {
            "poolclass": QueuePool,
            "pool_size": 1,
            "max_overflow": 0,
            "pool_pre_ping": True,
            "pool_recycle": 300,
            "connect_args": {
                "connect_timeout": 10,
                "application_name": "nowwhat-api",
            },
            "echo": settings.ENV == "development"
        }

# 동적 엔진 설정
db_url = get_database_url()
engine_config = get_engine_config()

engine = create_engine(db_url, **engine_config)

SessionLocal = sessionmaker(
    autocommit=False, 
    autoflush=False, 
    bind=engine,
    expire_on_commit=False
)

Base = declarative_base()

def get_db():
    """데이터베이스 세션 생성 및 관리"""
    db = None
    try:
        db = SessionLocal()
        yield db
    except Exception as e:
        logger.error(f"Database session error: {e}")
        if db:
            try:
                db.rollback()
            except Exception:
                pass
        raise
    finally:
        if db:
            try:
                db.close()
            except Exception as e:
                logger.error(f"Error closing database session: {e}")

# 레거시 호환성을 위한 별칭들
get_database = get_db

def reset_async_engine():
    """레거시 호환성을 위한 더미 함수"""
    pass

def create_tables():
    """데이터베이스 테이블 생성"""
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables created successfully")
        logger.info(f"Database URL: {db_url}")
    except Exception as e:
        logger.error(f"Error creating database tables: {e}")
        raise

def test_connection():
    """데이터베이스 연결 테스트"""
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        logger.info("Database connection test successful")
        logger.info(f"Connected to: {db_url}")
        return True
    except Exception as e:
        logger.error(f"Database connection test failed: {e}")
        return False