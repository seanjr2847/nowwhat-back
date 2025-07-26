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
        url = url.replace("postgresql+asyncpg://", "postgresql+psycopg://")
    elif url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql+psycopg://")
    elif url.startswith("postgresql://"):
        url = url.replace("postgresql://", "postgresql+psycopg://")
    
    # 동기 엔진용 sslmode 변환 (psycopg는 sslmode를 지원함)
    # 하지만 혹시 모르니 ssl 파라미터로도 변환
    import re
    if 'sslmode=require' in url:
        # psycopg는 sslmode를 지원하므로 그대로 유지하거나 ssl로 변환
        url = url.replace('sslmode=require', 'sslmode=require')
    
    return url

def get_async_database_url():
    """비동기 데이터베이스 URL 생성 (FastAPI용) - asyncpg 호환 변환"""
    url = settings.DATABASE_URL
    if not url:
        return ""
    
    # 더 직접적인 방법으로 URL 변환
    import re
    
    # 1. 스키마 변경: postgres:// -> postgresql+asyncpg://
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql+asyncpg://")
    elif url.startswith("postgresql://"):
        url = url.replace("postgresql://", "postgresql+asyncpg://")
    
    # 2. sslmode 파라미터를 ssl로 변환
    url = re.sub(r'[?&]sslmode=require', '?ssl=true', url)
    url = re.sub(r'[?&]sslmode=prefer', '?ssl=true', url)
    url = re.sub(r'[?&]sslmode=verify-ca', '?ssl=true', url)
    url = re.sub(r'[?&]sslmode=verify-full', '?ssl=true', url)
    url = re.sub(r'[?&]sslmode=disable', '?ssl=false', url)
    url = re.sub(r'[?&]sslmode=allow', '?ssl=false', url)
    
    # 3. 혹시 ?가 중복되었을 경우 처리
    url = re.sub(r'\?\?', '?', url)
    
    # 디버깅을 위해 실제 URL 로그 출력
    logger.info(f"Converted URL for asyncpg: {url}")
    
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
            # URL 방식 대신 연결 파라미터 딕셔너리 방식 사용
            from urllib.parse import urlparse
            
            parsed = urlparse(settings.DATABASE_URL)
            
            # asyncpg 연결 파라미터 직접 구성
            connect_args = {
                "ssl": True,  # SSL 활성화
                "server_settings": {
                    "application_name": "nowwhat-backend"
                }
            }
            
            # URL 재구성 (sslmode 제거, ssl 파라미터도 제거하고 connect_args에서 처리)
            clean_url = f"postgresql+asyncpg://{parsed.netloc}{parsed.path}"
            
            logger.info(f"Connecting with clean URL: {clean_url} and SSL in connect_args")
            
            async_engine = create_async_engine(
                clean_url,
                echo=settings.ENV == "development",
                pool_pre_ping=True,
                pool_recycle=300,
                connect_args=connect_args
            )
            logger.info("비동기 엔진이 성공적으로 초기화되었습니다.")
        except Exception as e:
            logger.error(f"비동기 엔진 초기화 실패: {e}")
            raise
    return async_engine

def reset_async_engine():
    """비동기 엔진 리셋 (새로운 URL 적용을 위해)"""
    global async_engine
    async_engine = None
    logger.info("비동기 엔진이 리셋되었습니다.")

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