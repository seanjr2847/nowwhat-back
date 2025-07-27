from typing import Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import and_
from app.crud.base import CRUDBase
from app.models.database import Checklist, ChecklistItem, User
from app.schemas.nowwhat import ChecklistCreate, ChecklistUpdate
from datetime import datetime

class CRUDChecklist(CRUDBase[Checklist, ChecklistCreate, ChecklistUpdate]):
    def get_with_items(self, db: Session, *, checklist_id: str) -> Optional[Checklist]:
        """체크리스트와 아이템들을 함께 조회"""
        # 체크리스트와 연관된 아이템들을 함께 조회
        checklist = db.query(Checklist).filter(Checklist.id == checklist_id).first()
        if checklist:
            # 아이템들을 order 순으로 정렬해서 로드
            items = db.query(ChecklistItem).filter(
                ChecklistItem.checklist_id == checklist_id
            ).order_by(ChecklistItem.order).all()
            checklist.items = items
        return checklist
    
    def create_with_items(
        self,
        db: Session,
        *,
        user_id: str,
        title: str,
        category: str,
        description: str = None,
        items: List[dict]
    ) -> Checklist:
        """체크리스트와 아이템들을 함께 생성"""
        # 1. 체크리스트 생성
        checklist = Checklist(
            user_id=user_id,
            title=title,
            category=category,
            description=description,
            total_items=len(items),
            completed_items=0,
            progress_percentage=0.0
        )
        db.add(checklist)
        db.flush()  # ID 생성을 위해
        
        # 2. 체크리스트 아이템들 생성
        checklist_items = []
        for idx, item_data in enumerate(items):
            item = ChecklistItem(
                checklist_id=checklist.id,
                title=item_data['title'],
                description=item_data.get('description'),
                order=idx + 1,
                is_completed=False
            )
            checklist_items.append(item)
            db.add(item)
        
        db.commit()
        db.refresh(checklist)
        checklist.items = checklist_items
        
        return checklist
    
    def update_progress(self, db: Session, *, checklist_id: str) -> Optional[Checklist]:
        """체크리스트 진행률 업데이트"""
        checklist = db.query(Checklist).filter(Checklist.id == checklist_id).first()
        if not checklist:
            return None
        
        # 완료된 아이템 수 계산
        completed_count = db.query(ChecklistItem).filter(
            and_(
                ChecklistItem.checklist_id == checklist_id,
                ChecklistItem.is_completed == True
            )
        ).count()
        
        # 전체 아이템 수
        total_count = db.query(ChecklistItem).filter(
            ChecklistItem.checklist_id == checklist_id
        ).count()
        
        # 진행률 계산
        progress = (completed_count / total_count * 100) if total_count > 0 else 0
        
        # 업데이트
        checklist.completed_items = completed_count
        checklist.total_items = total_count
        checklist.progress_percentage = round(progress, 1)
        checklist.updated_at = datetime.utcnow()
        
        # 모든 아이템이 완료되면 체크리스트도 완료로 표시
        if completed_count == total_count and total_count > 0:
            checklist.is_completed = True
            checklist.completed_at = datetime.utcnow()
        else:
            checklist.is_completed = False
            checklist.completed_at = None
        
        db.add(checklist)
        db.commit()
        db.refresh(checklist)
        
        return checklist
    
    def get_user_checklists(
        self,
        db: Session,
        *,
        user_id: str,
        category: str = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[Checklist]:
        """사용자의 체크리스트 목록 조회"""
        query = db.query(Checklist).filter(Checklist.user_id == user_id)
        
        if category:
            query = query.filter(Checklist.category == category)
        
        return query.order_by(Checklist.created_at.desc()).offset(skip).limit(limit).all()

checklist = CRUDChecklist(Checklist)

class CRUDChecklistItem(CRUDBase[ChecklistItem, ChecklistItem, ChecklistItem]):
    def update_completion(
        self, 
        db: Session, 
        *, 
        item_id: str, 
        is_completed: bool,
        completed_at: Optional[str] = None
    ) -> Optional[ChecklistItem]:
        """체크리스트 항목 완료 상태 업데이트"""
        item = db.query(ChecklistItem).filter(ChecklistItem.id == item_id).first()
        
        if not item:
            return None
        
        item.is_completed = is_completed
        item.completed_at = completed_at
        
        db.add(item)
        db.commit()
        db.refresh(item)
        
        return item

checklist_item = CRUDChecklistItem(ChecklistItem) 