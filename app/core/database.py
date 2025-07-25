# core/config.py
from pydantic_settings import BaseSettings
from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)

# SQLAlchemy Base 클래스
Base = declarative_base()

# 동기 엔진 (Alembic용) - Vercel 호환성을 위해 psycopg 사용
engine = create_engine(
    settings.DATABASE_URL.replace("postgresql+asyncpg://", "postgresql+psycopg://"),
    echo=settings.ENV == "development"
)

# 비동기 엔진 (FastAPI용)
async_engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.ENV == "development",
    pool_pre_ping=True,
    pool_recycle=300
)

# 비동기 세션 메이커
AsyncSessionLocal = sessionmaker(
    async_engine, 
    class_=AsyncSession, 
    expire_on_commit=False
)

# 의존성 주입용 데이터베이스 세션
async def get_database() -> AsyncSession:
    """데이터베이스 세션 의존성"""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception as e:
            logger.error(f"Database session error: {e}")
            await session.rollback()
            raise
        finally:
            await session.close()

# 데이터베이스 테이블 생성
async def create_tables():
    """데이터베이스 테이블 생성"""
    try:
        from app.models.database import Base
        async with async_engine.begin() as conn:
            # 모든 테이블 생성 (존재하지 않는 경우에만)
            await conn.run_sync(Base.metadata.create_all)
            logger.info("Database tables created successfully")
    except Exception as e:
        logger.error(f"Failed to create database tables: {e}")
        raise

# 데이터베이스 연결 테스트
async def test_connection():
    """데이터베이스 연결 테스트"""
    try:
        async with engine.begin() as conn:
            # text() 함수를 사용하여 명시적으로 SQL 문자열 선언
            result = await conn.execute(text("SELECT 1"))
            return result.scalar() == 1
    except Exception as e:
        logger.error(f"Database connection test failed: {e}")
        raise

async def close_database():
    """데이터베이스 연결 종료"""
    await engine.dispose()