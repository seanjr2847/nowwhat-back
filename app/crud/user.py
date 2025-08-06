from typing import Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import desc, func
from app.crud.base import CRUDBase
from app.models.database import User, Checklist, Feedback
from app.schemas.nowwhat import UserProfile
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class CRUDUser(CRUDBase[User, UserProfile, UserProfile]):
    def get_by_email(self, db: Session, *, email: str) -> Optional[User]:
        """이메일로 사용자 조회"""
        return db.query(User).filter(User.email == email).first()
    
    def get_by_google_id(self, db: Session, *, google_id: str) -> Optional[User]:
        """구글 ID로 사용자 조회"""
        return db.query(User).filter(User.google_id == google_id).first()
    
    def create_user(self, db: Session, *, user_data: dict) -> User:
        """새 사용자 생성"""
        db_user = User(**user_data)
        db.add(db_user)
        db.commit()
        db.refresh(db_user)
        return db_user
    
    def update_last_login(self, db: Session, user_id: str) -> bool:
        """마지막 로그인 시간 업데이트"""
        try:
            user = db.query(User).filter(User.id == user_id).first()
            if user:
                user.last_login_at = datetime.now()
                db.commit()
                logger.info(f"Updated last login for user {user_id}")
                return True
            return False
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to update last login for user {user_id}: {str(e)}")
            return False
    
    def update_profile(
        self, 
        db: Session, 
        user_id: str, 
        name: Optional[str] = None,
        profile_image: Optional[str] = None
    ) -> Optional[User]:
        """사용자 프로필 업데이트"""
        try:
            user = db.query(User).filter(User.id == user_id).first()
            if not user:
                return None
            
            if name is not None:
                user.name = name
            if profile_image is not None:
                user.profile_image = profile_image
            
            user.updated_at = datetime.now()
            db.commit()
            db.refresh(user)
            
            logger.info(f"Updated profile for user {user_id}")
            return user
            
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to update profile for user {user_id}: {str(e)}")
            raise
    
    def get_user_statistics(self, db: Session, user_id: str) -> dict:
        """사용자 통계 조회"""
        try:
            # 체크리스트 통계
            checklists_count = db.query(func.count(Checklist.id)).filter(
                Checklist.user_id == user_id
            ).scalar()
            
            completed_checklists = db.query(func.count(Checklist.id)).filter(
                Checklist.user_id == user_id,
                Checklist.progress >= 100
            ).scalar()
            
            # 피드백 통계
            feedbacks_count = db.query(func.count(Feedback.id)).filter(
                Feedback.user_id == user_id
            ).scalar()
            
            positive_feedbacks = db.query(func.count(Feedback.id)).filter(
                Feedback.user_id == user_id,
                Feedback.is_positive == True
            ).scalar()
            
            # 평균 평점
            avg_rating = db.query(func.avg(Feedback.rating)).filter(
                Feedback.user_id == user_id,
                Feedback.rating.isnot(None)
            ).scalar()
            
            # 가장 최근 활동
            latest_checklist = db.query(Checklist).filter(
                Checklist.user_id == user_id
            ).order_by(desc(Checklist.created_at)).first()
            
            latest_feedback = db.query(Feedback).filter(
                Feedback.user_id == user_id
            ).order_by(desc(Feedback.created_at)).first()
            
            return {
                "checklists": {
                    "total": checklists_count or 0,
                    "completed": completed_checklists or 0,
                    "completion_rate": round((completed_checklists / checklists_count * 100), 2) if checklists_count > 0 else 0
                },
                "feedbacks": {
                    "total": feedbacks_count or 0,
                    "positive": positive_feedbacks or 0,
                    "positive_rate": round((positive_feedbacks / feedbacks_count * 100), 2) if feedbacks_count > 0 else 0,
                    "average_rating": round(float(avg_rating), 2) if avg_rating else 0
                },
                "activity": {
                    "latest_checklist_date": latest_checklist.created_at if latest_checklist else None,
                    "latest_feedback_date": latest_feedback.created_at if latest_feedback else None,
                    "has_recent_activity": bool(latest_checklist or latest_feedback)
                }
            }
            
        except Exception as e:
            logger.error(f"Failed to get user statistics for {user_id}: {str(e)}")
            return {
                "checklists": {"total": 0, "completed": 0, "completion_rate": 0},
                "feedbacks": {"total": 0, "positive": 0, "positive_rate": 0, "average_rating": 0},
                "activity": {"latest_checklist_date": None, "latest_feedback_date": None, "has_recent_activity": False}
            }
    
    def delete_user_account(self, db: Session, user_id: str) -> bool:
        """사용자 계정 삭제 (관련 데이터 모두 삭제)"""
        try:
            user = db.query(User).filter(User.id == user_id).first()
            if not user:
                return False
            
            # 관련 데이터 삭제는 데이터베이스의 cascade 설정에 따라 자동 처리
            db.delete(user)
            db.commit()
            
            logger.info(f"Deleted user account {user_id}")
            return True
            
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to delete user account {user_id}: {str(e)}")
            raise
    
    def get_user_with_relations(self, db: Session, user_id: str) -> Optional[User]:
        """관계 데이터와 함께 사용자 조회"""
        return db.query(User).filter(User.id == user_id).first()

user = CRUDUser(User) 