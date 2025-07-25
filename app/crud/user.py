from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.crud.base import CRUDBase
from app.models.database import User
from app.schemas.nowwhat import UserProfile

class CRUDUser(CRUDBase[User, UserProfile, UserProfile]):
    async def get_by_email(self, db: AsyncSession, *, email: str) -> Optional[User]:
        """이메일로 사용자 조회"""
        result = await db.execute(select(User).where(User.email == email))
        return result.scalars().first()
    
    async def get_by_google_id(self, db: AsyncSession, *, google_id: str) -> Optional[User]:
        """구글 ID로 사용자 조회"""
        result = await db.execute(select(User).where(User.google_id == google_id))
        return result.scalars().first()
    
    async def create_user(self, db: AsyncSession, *, user_data: dict) -> User:
        """새 사용자 생성"""
        db_user = User(**user_data)
        db.add(db_user)
        await db.commit()
        await db.refresh(db_user)
        return db_user

user = CRUDUser(User) 