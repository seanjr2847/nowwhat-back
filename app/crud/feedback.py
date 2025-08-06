# crud/feedback.py
from sqlalchemy.orm import Session
from sqlalchemy import desc
from app.models.database import Feedback, Checklist
from typing import List, Optional
import logging

logger = logging.getLogger(__name__)

def create_feedback(
    db: Session,
    checklist_id: str,
    user_id: str,
    is_positive: bool,
    rating: Optional[int] = None,
    comment: Optional[str] = None,
    categories: Optional[List[str]] = None
) -> Feedback:
    """피드백 생성"""
    
    try:
        feedback = Feedback(
            checklist_id=checklist_id,
            user_id=user_id,
            is_positive=is_positive,
            rating=rating,
            comment=comment,
            categories=categories
        )
        
        db.add(feedback)
        db.commit()
        db.refresh(feedback)
        
        logger.info(f"Created feedback {feedback.id} for checklist {checklist_id} by user {user_id}")
        return feedback
        
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to create feedback: {str(e)}")
        raise

def get_feedback_by_id(db: Session, feedback_id: str) -> Optional[Feedback]:
    """ID로 피드백 조회"""
    return db.query(Feedback).filter(Feedback.id == feedback_id).first()

def get_feedbacks_by_checklist(db: Session, checklist_id: str) -> List[Feedback]:
    """체크리스트별 피드백 조회"""
    return (
        db.query(Feedback)
        .filter(Feedback.checklist_id == checklist_id)
        .order_by(desc(Feedback.created_at))
        .all()
    )

def get_feedbacks_by_user(db: Session, user_id: str, limit: int = 50) -> List[Feedback]:
    """사용자별 피드백 조회"""
    return (
        db.query(Feedback)
        .filter(Feedback.user_id == user_id)
        .order_by(desc(Feedback.created_at))
        .limit(limit)
        .all()
    )

def verify_checklist_ownership(db: Session, checklist_id: str, user_id: str) -> bool:
    """체크리스트 소유권 확인"""
    checklist = db.query(Checklist).filter(
        Checklist.id == checklist_id,
        Checklist.user_id == user_id
    ).first()
    
    return checklist is not None

def get_feedback_statistics(db: Session, checklist_id: Optional[str] = None) -> dict:
    """피드백 통계 조회"""
    
    query = db.query(Feedback)
    if checklist_id:
        query = query.filter(Feedback.checklist_id == checklist_id)
    
    feedbacks = query.all()
    
    if not feedbacks:
        return {
            "total_count": 0,
            "positive_count": 0,
            "negative_count": 0,
            "average_rating": 0,
            "rating_distribution": {}
        }
    
    total_count = len(feedbacks)
    positive_count = sum(1 for f in feedbacks if f.is_positive)
    negative_count = total_count - positive_count
    
    # 평점 통계
    ratings = [f.rating for f in feedbacks if f.rating is not None]
    average_rating = sum(ratings) / len(ratings) if ratings else 0
    
    # 평점 분포
    rating_distribution = {}
    for rating in range(1, 6):
        rating_distribution[str(rating)] = len([r for r in ratings if r == rating])
    
    return {
        "total_count": total_count,
        "positive_count": positive_count,
        "negative_count": negative_count,
        "positive_rate": round(positive_count / total_count * 100, 2) if total_count > 0 else 0,
        "average_rating": round(average_rating, 2),
        "rating_distribution": rating_distribution,
        "has_comments": sum(1 for f in feedbacks if f.comment and f.comment.strip())
    }

def delete_feedback(db: Session, feedback_id: str, user_id: str) -> bool:
    """피드백 삭제 (사용자 본인만 가능)"""
    
    feedback = db.query(Feedback).filter(
        Feedback.id == feedback_id,
        Feedback.user_id == user_id
    ).first()
    
    if not feedback:
        return False
    
    try:
        db.delete(feedback)
        db.commit()
        logger.info(f"Deleted feedback {feedback_id} by user {user_id}")
        return True
        
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to delete feedback {feedback_id}: {str(e)}")
        raise

def update_feedback(
    db: Session,
    feedback_id: str,
    user_id: str,
    is_positive: Optional[bool] = None,
    rating: Optional[int] = None,
    comment: Optional[str] = None,
    categories: Optional[List[str]] = None
) -> Optional[Feedback]:
    """피드백 업데이트 (사용자 본인만 가능)"""
    
    feedback = db.query(Feedback).filter(
        Feedback.id == feedback_id,
        Feedback.user_id == user_id
    ).first()
    
    if not feedback:
        return None
    
    try:
        if is_positive is not None:
            feedback.is_positive = is_positive
        if rating is not None:
            feedback.rating = rating
        if comment is not None:
            feedback.comment = comment
        if categories is not None:
            feedback.categories = categories
        
        db.commit()
        db.refresh(feedback)
        
        logger.info(f"Updated feedback {feedback_id} by user {user_id}")
        return feedback
        
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to update feedback {feedback_id}: {str(e)}")
        raise