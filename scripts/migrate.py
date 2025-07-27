#!/usr/bin/env python3
"""
프로덕션 환경 데이터베이스 마이그레이션 스크립트

사용법:
  python scripts/migrate.py
  
환경변수:
  DATABASE_URL: PostgreSQL 연결 URL
"""

import os
import sys
import asyncio
import logging
from alembic.config import Config
from alembic import command
from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError

# 프로젝트 루트를 Python 경로에 추가
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.core.config import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def run_migrations():
    """마이그레이션 실행"""
    try:
        # 데이터베이스 연결 확인
        engine = create_engine(settings.DATABASE_URL)
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        logger.info("Database connection successful")
        
        # Alembic 설정
        alembic_cfg = Config("alembic.ini")
        
        # 현재 마이그레이션 상태 확인
        logger.info("Checking current migration status...")
        command.current(alembic_cfg)
        
        # 마이그레이션 실행
        logger.info("Running migrations...")
        command.upgrade(alembic_cfg, "head")
        
        logger.info("Migrations completed successfully!")
        return True
        
    except OperationalError as e:
        logger.error(f"Database connection failed: {e}")
        return False
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        return False

if __name__ == "__main__":
    if not settings.DATABASE_URL:
        logger.error("DATABASE_URL environment variable is not set")
        sys.exit(1)
    
    success = run_migrations()
    sys.exit(0 if success else 1) 