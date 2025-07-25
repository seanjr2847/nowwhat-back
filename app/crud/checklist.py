from typing import List, Optional
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.crud.base import CRUDBase
from app.models.database import Checklist, ChecklistItem
from app.schemas.nowwhat import Checklist as ChecklistSchema

class CRUDChecklist(CRUDBase[Checklist, ChecklistSchema, ChecklistSchema]):
    async def get_with_items(self, db: AsyncSession, *, checklist_id: str) -> Optional[Checklist]:
        """체크리스트와 항목들을 함께 조회"""
        result = await db.execute(
            select(Checklist)
            .options(selectinload(Checklist.items))
            .where(Checklist.id == checklist_id)
        )
        return result.scalars().first()
    
    async def get_user_checklists(
        self, 
        db: AsyncSession, 
        *, 
        user_id: str,
        skip: int = 0,
        limit: int = 100,
        category: Optional[str] = None,
        status: Optional[str] = None
    ) -> List[Checklist]:
        """사용자의 체크리스트 목록 조회"""
        query = select(Checklist).where(Checklist.user_id == user_id)
        
        # 필터링
        if category:
            query = query.where(Checklist.category == category)
        
        if status:
            if status == "completed":
                query = query.where(Checklist.progress >= 100.0)
            elif status == "in_progress":
                query = query.where(and_(Checklist.progress > 0.0, Checklist.progress < 100.0))
        
        # 페이지네이션
        query = query.offset(skip).limit(limit)
        
        result = await db.execute(query)
        return result.scalars().all()
    
    async def update_progress(self, db: AsyncSession, *, checklist_id: str) -> Optional[Checklist]:
        """체크리스트 진행률 업데이트"""
        # 체크리스트와 항목들 조회
        checklist = await self.get_with_items(db, checklist_id=checklist_id)
        if not checklist:
            return None
        
        # 진행률 계산
        total_items = len(checklist.items)
        completed_items = len([item for item in checklist.items if item.is_completed])
        progress = (completed_items / total_items * 100) if total_items > 0 else 0.0
        
        # 진행률 업데이트
        checklist.progress = progress
        db.add(checklist)
        await db.commit()
        await db.refresh(checklist)
        
        return checklist

class CRUDChecklistItem(CRUDBase[ChecklistItem, ChecklistItem, ChecklistItem]):
    async def update_completion(
        self, 
        db: AsyncSession, 
        *, 
        item_id: str, 
        is_completed: bool,
        completed_at: Optional[str] = None
    ) -> Optional[ChecklistItem]:
        """체크리스트 항목 완료 상태 업데이트"""
        result = await db.execute(select(ChecklistItem).where(ChecklistItem.id == item_id))
        item = result.scalars().first()
        
        if not item:
            return None
        
        item.is_completed = is_completed
        item.completed_at = completed_at
        
        db.add(item)
        await db.commit()
        await db.refresh(item)
        
        return item

checklist = CRUDChecklist(Checklist)
checklist_item = CRUDChecklistItem(ChecklistItem) 