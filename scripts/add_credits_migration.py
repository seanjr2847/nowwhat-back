"""
기존 사용자 크레딧 마이그레이션 스크립트

비즈니스 로직:
- 기존 사용자들에게 10크레딧 지급
- credits 컬럼이 없는 사용자들 대상으로만 실행
- 안전한 배치 처리로 대량 데이터 처리
"""

import sys
import os
import asyncio
from sqlalchemy import text

# FastAPI 앱의 루트 디렉토리를 Python 경로에 추가
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from app.core.database import SessionLocal, engine
from app.models.database import User, CreditLog
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def migrate_existing_users():
    """기존 사용자들에게 크레딧 지급"""
    
    # 먼저 credits 컬럼이 존재하는지 확인
    with engine.connect() as connection:
        try:
            # credits 컬럼 추가 (이미 있으면 무시됨)
            connection.execute(text("""
                ALTER TABLE users 
                ADD COLUMN IF NOT EXISTS credits INTEGER DEFAULT 10 NOT NULL;
            """))
            connection.commit()
            logger.info("✅ Credits column added to users table")
            
            # credit_logs 테이블 생성 (이미 있으면 무시됨)
            connection.execute(text("""
                CREATE TABLE IF NOT EXISTS credit_logs (
                    id VARCHAR PRIMARY KEY,
                    user_id VARCHAR,
                    action VARCHAR NOT NULL,
                    credits_before INTEGER NOT NULL,
                    credits_after INTEGER NOT NULL,
                    created_at TIMESTAMP DEFAULT NOW(),
                    FOREIGN KEY (user_id) REFERENCES users(id)
                );
            """))
            connection.commit()
            logger.info("✅ Credit_logs table created")
            
        except Exception as e:
            logger.error(f"❌ Database schema migration failed: {str(e)}")
            connection.rollback()
            return False
    
    # 사용자 크레딧 초기화
    db = SessionLocal()
    try:
        # credits가 0인 사용자들 조회 (NULL 또는 0)
        users_to_update = db.query(User).filter(
            (User.credits == 0) | (User.credits.is_(None))
        ).all()
        
        logger.info(f"Found {len(users_to_update)} users to migrate")
        
        updated_count = 0
        for user in users_to_update:
            try:
                # 10크레딧 지급
                user.credits = 10
                
                # 크레딧 지급 로그 생성
                credit_log = CreditLog(
                    user_id=user.id,
                    action="migration_initial_bonus",
                    credits_before=0,
                    credits_after=10
                )
                
                db.add(user)
                db.add(credit_log)
                updated_count += 1
                
                # 100명씩 배치 커밋
                if updated_count % 100 == 0:
                    db.commit()
                    logger.info(f"✅ Updated {updated_count} users so far...")
                    
            except Exception as e:
                logger.error(f"❌ Failed to update user {user.id}: {str(e)}")
                db.rollback()
                continue
        
        # 최종 커밋
        db.commit()
        
        logger.info(f"✅ Migration completed! Updated {updated_count} users with 10 credits each")
        return True
        
    except Exception as e:
        logger.error(f"❌ Migration failed: {str(e)}")
        db.rollback()
        return False
        
    finally:
        db.close()


def verify_migration():
    """마이그레이션 결과 검증"""
    db = SessionLocal()
    try:
        # 사용자 수 및 크레딧 통계
        total_users = db.query(User).count()
        users_with_credits = db.query(User).filter(User.credits > 0).count()
        total_credits = db.query(User).with_entities(
            text("SUM(credits)")
        ).scalar() or 0
        
        logger.info("📊 Migration Results:")
        logger.info(f"   Total users: {total_users}")
        logger.info(f"   Users with credits: {users_with_credits}")
        logger.info(f"   Total credits distributed: {total_credits}")
        
        # 크레딧 로그 확인
        log_count = db.query(CreditLog).filter(
            CreditLog.action == "migration_initial_bonus"
        ).count()
        logger.info(f"   Migration logs created: {log_count}")
        
        if users_with_credits == total_users:
            logger.info("✅ All users have been migrated successfully!")
        else:
            logger.warning(f"⚠️  {total_users - users_with_credits} users still need migration")
            
    except Exception as e:
        logger.error(f"❌ Verification failed: {str(e)}")
        
    finally:
        db.close()


if __name__ == "__main__":
    logger.info("🚀 Starting credit system migration...")
    
    success = migrate_existing_users()
    
    if success:
        verify_migration()
        logger.info("✅ Credit migration completed successfully!")
    else:
        logger.error("❌ Credit migration failed!")
        sys.exit(1)