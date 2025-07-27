from typing import Optional
from sqlalchemy.orm import Session
from app.crud.base import CRUDBase
from app.models.database import User
from app.schemas.nowwhat import UserProfile

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

user = CRUDUser(User) 