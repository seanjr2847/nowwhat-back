from fastapi import APIRouter, HTTPException, Depends, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from app.schemas.nowwhat import (
    ChecklistResponse, ChecklistCreate, ChecklistUpdate, 
    ChecklistItemUpdate, APIResponse
)
from app.core.auth import get_current_user
from app.core.database import get_db
from app.crud.checklist import checklist
from app.models.database import ChecklistItem
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

@router.get("/", response_model=List[ChecklistResponse])
async def get_user_checklists(
    category: Optional[str] = Query(None, description="카테고리 필터"),
    skip: int = Query(0, ge=0, description="건너뛸 개수"),
    limit: int = Query(100, ge=1, le=100, description="가져올 개수"),
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """현재 사용자의 체크리스트 목록 조회"""
    try:
        checklists = checklist.get_user_checklists(
            db=db,
            user_id=current_user.id,
            category=category,
            skip=skip,
            limit=limit
        )
        
        result = []
        for cl in checklists:
            # 각 체크리스트의 아이템들도 함께 조회
            cl_with_items = checklist.get_with_items(db=db, checklist_id=cl.id)
            
            result.append(ChecklistResponse(
                id=cl.id,
                title=cl.title,
                category=cl.category,
                description=cl.description,
                totalItems=cl.total_items,
                completedItems=cl.completed_items,
                progressPercentage=cl.progress_percentage,
                isCompleted=cl.is_completed,
                items=[
                    {
                        "id": item.id,
                        "title": item.title,
                        "description": item.description,
                        "order": item.order,
                        "isCompleted": item.is_completed,
                        "completedAt": item.completed_at.isoformat() if item.completed_at else None
                    }
                    for item in (cl_with_items.items if cl_with_items and cl_with_items.items else [])
                ],
                createdAt=cl.created_at.isoformat(),
                updatedAt=cl.updated_at.isoformat() if cl.updated_at else None,
                completedAt=cl.completed_at.isoformat() if cl.completed_at else None
            ))
        
        return result
        
    except Exception as e:
        logger.error(f"Get user checklists error: {e}")
        raise HTTPException(
            status_code=500,
            detail="체크리스트 목록 조회 중 오류가 발생했습니다."
        )

@router.get("/{checklist_id}", response_model=ChecklistResponse)
async def get_checklist(
    checklist_id: str,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """특정 체크리스트 상세 조회"""
    try:
        cl = checklist.get_with_items(db=db, checklist_id=checklist_id)
        
        if not cl:
            raise HTTPException(
                status_code=404,
                detail="체크리스트를 찾을 수 없습니다."
            )
        
        # 권한 확인
        if cl.user_id != current_user.id:
            raise HTTPException(
                status_code=403,
                detail="이 체크리스트에 접근할 권한이 없습니다."
            )
        
        return ChecklistResponse(
            id=cl.id,
            title=cl.title,
            category=cl.category,
            description=cl.description,
            totalItems=cl.total_items,
            completedItems=cl.completed_items,
            progressPercentage=cl.progress_percentage,
            isCompleted=cl.is_completed,
            items=[
                {
                    "id": item.id,
                    "title": item.title,
                    "description": item.description,
                    "order": item.order,
                    "isCompleted": item.is_completed,
                    "completedAt": item.completed_at.isoformat() if item.completed_at else None
                }
                for item in (cl.items if cl.items else [])
            ],
            createdAt=cl.created_at.isoformat(),
            updatedAt=cl.updated_at.isoformat() if cl.updated_at else None,
            completedAt=cl.completed_at.isoformat() if cl.completed_at else None
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get checklist error: {e}")
        raise HTTPException(
            status_code=500,
            detail="체크리스트 조회 중 오류가 발생했습니다."
        )

@router.post("/", response_model=ChecklistResponse)
async def create_checklist(
    checklist_data: ChecklistCreate,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """새 체크리스트 생성"""
    try:
        # 아이템이 있는지 확인
        if not checklist_data.items or len(checklist_data.items) == 0:
            raise HTTPException(
                status_code=400,
                detail="체크리스트에는 최소 1개의 아이템이 필요합니다."
            )
        
        # 체크리스트와 아이템들 생성
        new_checklist = checklist.create_with_items(
            db=db,
            user_id=current_user.id,
            title=checklist_data.title,
            category=checklist_data.category,
            description=checklist_data.description,
            items=[item.dict() for item in checklist_data.items]
        )
        
        return ChecklistResponse(
            id=new_checklist.id,
            title=new_checklist.title,
            category=new_checklist.category,
            description=new_checklist.description,
            totalItems=new_checklist.total_items,
            completedItems=new_checklist.completed_items,
            progressPercentage=new_checklist.progress_percentage,
            isCompleted=new_checklist.is_completed,
            items=[
                {
                    "id": item.id,
                    "title": item.title,
                    "description": item.description,
                    "order": item.order,
                    "isCompleted": item.is_completed,
                    "completedAt": item.completed_at.isoformat() if item.completed_at else None
                }
                for item in new_checklist.items
            ],
            createdAt=new_checklist.created_at.isoformat(),
            updatedAt=new_checklist.updated_at.isoformat() if new_checklist.updated_at else None,
            completedAt=new_checklist.completed_at.isoformat() if new_checklist.completed_at else None
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Create checklist error: {e}")
        raise HTTPException(
            status_code=500,
            detail="체크리스트 생성 중 오류가 발생했습니다."
        )

@router.patch("/{checklist_id}/items/{item_id}", response_model=APIResponse)
async def update_checklist_item(
    checklist_id: str,
    item_id: str,
    item_update: ChecklistItemUpdate,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """체크리스트 아이템 업데이트"""
    try:
        # 체크리스트 확인 및 권한 검증
        cl = checklist.get(db=db, id=checklist_id)
        if not cl:
            raise HTTPException(
                status_code=404,
                detail="체크리스트를 찾을 수 없습니다."
            )
        
        if cl.user_id != current_user.id:
            raise HTTPException(
                status_code=403,
                detail="이 체크리스트에 접근할 권한이 없습니다."
            )
        
        # 아이템 확인
        item = db.query(ChecklistItem).filter(
            ChecklistItem.id == item_id,
            ChecklistItem.checklist_id == checklist_id
        ).first()
        
        if not item:
            raise HTTPException(
                status_code=404,
                detail="체크리스트 아이템을 찾을 수 없습니다."
            )
        
        # 아이템 업데이트
        update_data = item_update.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(item, field, value)
        
        # 완료 시간 설정
        if item_update.isCompleted is not None:
            if item_update.isCompleted:
                from datetime import datetime
                item.completed_at = datetime.utcnow()
            else:
                item.completed_at = None
        
        db.add(item)
        db.commit()
        
        # 체크리스트 진행률 업데이트
        checklist.update_progress(db=db, checklist_id=checklist_id)
        
        return APIResponse(
            success=True,
            message="체크리스트 아이템이 업데이트되었습니다."
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Update checklist item error: {e}")
        raise HTTPException(
            status_code=500,
            detail="체크리스트 아이템 업데이트 중 오류가 발생했습니다."
        ) 