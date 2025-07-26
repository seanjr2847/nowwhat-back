# core/config.py
from pydantic_settings import BaseSettings
from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text
from app.core.config import settings
import logging
import os

logger = logging.getLogger(__name__)

# SQLAlchemy Base 클래스
Base = declarative_base()

def get_sync_database_url():
    """동기 데이터베이스 URL 생성 (Alembic용)"""
    url = settings.DATABASE_URL
    if url.startswith("postgresql+asyncpg://"):
        return url.replace("postgresql+asyncpg://", "postgresql+psycopg://")
    elif url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql+psycopg://")
    elif url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+psycopg://")
    return url

def get_async_database_url():
    """비동기 데이터베이스 URL 생성 (FastAPI용) - asyncpg 호환 변환"""
    url = settings.DATABASE_URL
    if not url:
        return ""
    
    logger.info(f"Original URL: {url}")
    
    # asyncpg 호환을 위한 URL 변환
    if not url.startswith("postgresql+asyncpg://"):
        if url.startswith("postgres://"):
            url = url.replace("postgres://", "postgresql+asyncpg://")
        elif url.startswith("postgresql://"):
            url = url.replace("postgresql://", "postgresql+asyncpg://")
    
    logger.info(f"After protocol change: {url}")
    
    # sslmode 파라미터를 완전히 제거하고 ssl 파라미터로 변환 (asyncpg 호환)
    import re
    # sslmode 파라미터 제거
    url = re.sub(r'[?&]sslmode=[^&]*', '', url)
    
    logger.info(f"After sslmode removal: {url}")
    
    # SSL 파라미터 추가 (Neon DB는 SSL이 필요)
    if '?' in url:
        url += "&ssl=true"
    else:
        url += "?ssl=true"
    
    logger.info(f"Final URL: {url}")
    
    return url

# 동기 엔진 (Alembic용) - 완전한 지연 초기화
engine = None

def get_sync_engine():
    """동기 엔진을 안전하게 가져오는 함수"""
    global engine
    if engine is None:
        try:
            engine = create_engine(
                get_sync_database_url(),
                echo=settings.ENV == "development"
            )
            logger.info("동기 엔진이 성공적으로 초기화되었습니다.")
        except Exception as e:
            logger.error(f"동기 엔진 초기화 실패: {e}")
            raise
    return engine

# 비동기 엔진 (FastAPI용) - 지연 초기화
async_engine = None

def get_async_engine():
    """비동기 엔진을 안전하게 가져오는 함수"""
    global async_engine
    if async_engine is None:
        try:
            async_url = get_async_database_url()
            logger.info(f"Connecting to database with URL: {async_url.split('@')[0]}@***")
            
            async_engine = create_async_engine(
                async_url,
                echo=settings.ENV == "development",
                pool_pre_ping=True,
                pool_recycle=300
            )
            logger.info("비동기 엔진이 성공적으로 초기화되었습니다.")
        except Exception as e:
            logger.error(f"비동기 엔진 초기화 실패: {e}")
            raise
    return async_engine

# 비동기 세션 메이커 - 지연 초기화
_AsyncSessionLocal = None

def get_async_session_maker():
    """비동기 세션 메이커를 안전하게 가져오는 함수"""
    global _AsyncSessionLocal
    if _AsyncSessionLocal is None:
        _AsyncSessionLocal = async_sessionmaker(
            get_async_engine(), 
            class_=AsyncSession, 
            expire_on_commit=False
        )
    return _AsyncSessionLocal

# 의존성 주입용 데이터베이스 세션
async def get_database() -> AsyncSession:
    """데이터베이스 세션 의존성"""
    AsyncSessionLocal = get_async_session_maker()
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