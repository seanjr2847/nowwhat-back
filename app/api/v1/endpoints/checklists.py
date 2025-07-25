from fastapi import APIRouter, HTTPException, Depends, Query
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from app.schemas.nowwhat import (
    Checklist, ChecklistSaveRequest, ItemUpdateRequest, 
    ChecklistListResponse, APIResponse, ChecklistItem
)
from app.core.auth import get_current_user
from app.core.database import get_database
from app.crud.checklist import checklist, checklist_item
from datetime import datetime

router = APIRouter()

@router.get("/{checklist_id}", response_model=Checklist)
async def get_checklist(
    checklist_id: str, 
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_database)
):
    """특정 체크리스트 조회"""
    try:
        # 데이터베이스에서 체크리스트 조회
        db_checklist = await checklist.get_with_items(db, checklist_id=checklist_id)
        
        if not db_checklist:
            raise HTTPException(status_code=404, detail="체크리스트를 찾을 수 없습니다.")
        
        # 권한 확인 (본인 소유 또는 public)
        user_id = current_user.get("id")
        if db_checklist.user_id != user_id and not db_checklist.is_public:
            raise HTTPException(status_code=403, detail="접근 권한이 없습니다.")
        
        # Pydantic 모델로 변환
        checklist_items = [
            ChecklistItem(
                id=item.id,
                text=item.text,
                isCompleted=item.is_completed,
                completedAt=item.completed_at,
                order=item.order
            )
            for item in db_checklist.items
        ]
        
        return Checklist(
            id=db_checklist.id,
            title=db_checklist.title,
            description=db_checklist.description,
            category=db_checklist.category,
            items=checklist_items,
            progress=db_checklist.progress,
            createdAt=db_checklist.created_at,
            updatedAt=db_checklist.updated_at,
            isPublic=db_checklist.is_public,
            customName=db_checklist.custom_name
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail="체크리스트 조회 중 오류가 발생했습니다.")

@router.get("/my", response_model=ChecklistListResponse)
async def get_my_checklists(
    page: Optional[int] = Query(1, ge=1),
    limit: Optional[int] = Query(20, ge=1, le=100),
    category: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    sortBy: Optional[str] = Query("createdAt"),
    sortOrder: Optional[str] = Query("desc"),
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_database)
):
    """내 체크리스트 목록 조회 - 페이지네이션"""
    try:
        user_id = current_user.get("id")
        skip = (page - 1) * limit
        
        # 데이터베이스에서 사용자 체크리스트 조회
        db_checklists = await checklist.get_user_checklists(
            db,
            user_id=user_id,
            skip=skip,
            limit=limit,
            category=category,
            status=status
        )
        
        # Pydantic 모델로 변환
        checklists = [
            Checklist(
                id=cl.id,
                title=cl.title,
                description=cl.description,
                category=cl.category,
                items=[],  # 목록에서는 items를 제외
                progress=cl.progress,
                createdAt=cl.created_at,
                updatedAt=cl.updated_at,
                isPublic=cl.is_public,
                customName=cl.custom_name
            )
            for cl in db_checklists
        ]
        
        return ChecklistListResponse(
            success=True,
            message="체크리스트 목록을 조회했습니다.",
            data=checklists,
            pagination={
                "currentPage": page,
                "totalPages": (len(checklists) + limit - 1) // limit,
                "totalItems": len(checklists),
                "itemsPerPage": limit
            }
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail="체크리스트 목록 조회에 실패했습니다.")

@router.post("/{checklist_id}/save", response_model=APIResponse)
async def save_checklist(
    checklist_id: str, 
    save_data: ChecklistSaveRequest,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_database)
):
    """체크리스트 저장 - 내 리스트에 추가"""
    try:
        user_id = current_user.get("id")
        
        # 원본 체크리스트 조회
        original_checklist = await checklist.get_with_items(db, checklist_id=checklist_id)
        if not original_checklist:
            raise HTTPException(status_code=404, detail="체크리스트를 찾을 수 없습니다.")
        
        # TODO: 체크리스트 복사 로직 구현
        # 지금은 임시 응답
        return APIResponse(
            success=True,
            message="체크리스트가 내 리스트에 저장되었습니다.",
            data={
                "savedId": f"saved_{checklist_id}",
                "customName": save_data.customName
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail="체크리스트 저장에 실패했습니다.")

@router.patch("/{checklist_id}/items/{item_id}", response_model=APIResponse)
async def update_item(
    checklist_id: str,
    item_id: str,
    item_data: ItemUpdateRequest,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_database)
):
    """체크리스트 항목 완료 처리 - 진행률 업데이트"""
    try:
        user_id = current_user.get("id")
        
        # 체크리스트 권한 확인
        db_checklist = await checklist.get(db, id=checklist_id)
        if not db_checklist or db_checklist.user_id != user_id:
            raise HTTPException(status_code=403, detail="접근 권한이 없습니다.")
        
        # 항목 업데이트
        updated_item = await checklist_item.update_completion(
            db,
            item_id=item_id,
            is_completed=item_data.isCompleted,
            completed_at=item_data.completedAt
        )
        
        if not updated_item:
            raise HTTPException(status_code=404, detail="체크리스트 항목을 찾을 수 없습니다.")
        
        # 전체 진행률 재계산
        updated_checklist = await checklist.update_progress(db, checklist_id=checklist_id)
        
        return APIResponse(
            success=True,
            message="항목이 업데이트되었습니다.",
            data={
                "itemId": item_id,
                "isCompleted": item_data.isCompleted,
                "completedAt": item_data.completedAt,
                "newProgress": updated_checklist.progress if updated_checklist else 0.0
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail="항목 업데이트에 실패했습니다.")

@router.delete("/{checklist_id}", response_model=APIResponse)
async def delete_checklist(
    checklist_id: str, 
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_database)
):
    """체크리스트 삭제"""
    try:
        user_id = current_user.get("id")
        
        # 체크리스트 조회 및 권한 확인
        db_checklist = await checklist.get(db, id=checklist_id)
        if not db_checklist:
            raise HTTPException(status_code=404, detail="체크리스트를 찾을 수 없습니다.")
        
        if db_checklist.user_id != user_id:
            raise HTTPException(status_code=403, detail="접근 권한이 없습니다.")
        
        # 체크리스트 삭제
        await checklist.remove(db, id=checklist_id)
        
        return APIResponse(
            success=True,
            message="체크리스트가 삭제되었습니다."
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail="체크리스트 삭제에 실패했습니다.") 