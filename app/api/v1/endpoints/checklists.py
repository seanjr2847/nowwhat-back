from fastapi import APIRouter, HTTPException, Depends, Query
from typing import Optional
from app.schemas.nowwhat import (
    Checklist, ChecklistSaveRequest, ItemUpdateRequest, 
    ChecklistListResponse, APIResponse, ChecklistItem
)
from app.core.auth import get_current_user

router = APIRouter()

@router.get("/{checklist_id}", response_model=Checklist)
async def get_checklist(checklist_id: str, current_user=Depends(get_current_user)):
    """특정 체크리스트 조회"""
    try:
        # TODO: 실제 체크리스트 조회 로직
        # 1. checklist_id로 체크리스트 조회
        # 2. 권한 확인 (본인 소유 또는 public)
        # 3. 체크리스트 정보 반환
        
        from datetime import datetime
        
        # 임시 체크리스트 데이터
        sample_items = [
            ChecklistItem(id="item_1", text="아침 7시에 기상하기", order=1),
            ChecklistItem(id="item_2", text="물 2L 마시기", order=2),
            ChecklistItem(id="item_3", text="30분 운동하기", order=3, isCompleted=True, completedAt=datetime.now()),
            ChecklistItem(id="item_4", text="건강한 식단 유지하기", order=4),
            ChecklistItem(id="item_5", text="충분한 수면 취하기", order=5)
        ]
        
        return Checklist(
            id=checklist_id,
            title="건강한 하루 루틴",
            description="건강한 생활습관을 위한 일일 체크리스트",
            category="health",
            items=sample_items,
            progress=20.0,  # 5개 중 1개 완료
            createdAt=datetime.now(),
            updatedAt=datetime.now(),
            isPublic=True
        )
    except Exception as e:
        raise HTTPException(status_code=404, detail="체크리스트를 찾을 수 없습니다.")

@router.get("/my", response_model=ChecklistListResponse)
async def get_my_checklists(
    page: Optional[int] = Query(1, ge=1),
    limit: Optional[int] = Query(20, ge=1, le=100),
    category: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    sortBy: Optional[str] = Query("createdAt"),
    sortOrder: Optional[str] = Query("desc"),
    current_user=Depends(get_current_user)
):
    """내 체크리스트 목록 조회 - 페이지네이션"""
    try:
        # TODO: 실제 체크리스트 목록 조회 로직
        # 1. 사용자별 체크리스트 조회
        # 2. 필터링 (category, status)
        # 3. 정렬 (sortBy, sortOrder)
        # 4. 페이지네이션
        
        from datetime import datetime
        
        # 임시 체크리스트 목록
        sample_checklists = [
            Checklist(
                id="checklist_1",
                title="건강한 하루 루틴",
                description="건강한 생활습관을 위한 일일 체크리스트",
                category="health",
                items=[],
                progress=60.0,
                createdAt=datetime.now(),
                updatedAt=datetime.now(),
                isPublic=False,
                customName="내 건강 루틴"
            ),
            Checklist(
                id="checklist_2",
                title="업무 효율성 향상",
                description="생산성을 높이는 업무 체크리스트",
                category="productivity",
                items=[],
                progress=25.0,
                createdAt=datetime.now(),
                updatedAt=datetime.now(),
                isPublic=False
            )
        ]
        
        return ChecklistListResponse(
            success=True,
            message="체크리스트 목록을 조회했습니다.",
            data=sample_checklists,
            pagination={
                "currentPage": page,
                "totalPages": 1,
                "totalItems": len(sample_checklists),
                "itemsPerPage": limit
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail="체크리스트 목록 조회에 실패했습니다.")

@router.post("/{checklist_id}/save", response_model=APIResponse)
async def save_checklist(
    checklist_id: str, 
    save_data: ChecklistSaveRequest,
    current_user=Depends(get_current_user)
):
    """체크리스트 저장 - 내 리스트에 추가"""
    try:
        # TODO: 실제 체크리스트 저장 로직
        # 1. 원본 체크리스트 조회
        # 2. 사용자의 리스트에 복사
        # 3. customName 적용
        
        return APIResponse(
            success=True,
            message="체크리스트가 내 리스트에 저장되었습니다.",
            data={
                "savedId": f"saved_{checklist_id}",
                "customName": save_data.customName
            }
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail="체크리스트 저장에 실패했습니다.")

@router.patch("/{checklist_id}/items/{item_id}", response_model=APIResponse)
async def update_item(
    checklist_id: str,
    item_id: str,
    item_data: ItemUpdateRequest,
    current_user=Depends(get_current_user)
):
    """체크리스트 항목 완료 처리 - 진행률 업데이트"""
    try:
        # TODO: 실제 항목 업데이트 로직
        # 1. 권한 확인 (본인 소유 체크리스트)
        # 2. 항목 상태 업데이트
        # 3. 전체 진행률 재계산
        
        return APIResponse(
            success=True,
            message="항목이 업데이트되었습니다.",
            data={
                "itemId": item_id,
                "isCompleted": item_data.isCompleted,
                "completedAt": item_data.completedAt,
                "newProgress": 40.0  # 예시 진행률
            }
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail="항목 업데이트에 실패했습니다.")

@router.delete("/{checklist_id}", response_model=APIResponse)
async def delete_checklist(checklist_id: str, current_user=Depends(get_current_user)):
    """체크리스트 삭제"""
    try:
        # TODO: 실제 체크리스트 삭제 로직
        # 1. 권한 확인 (본인 소유 체크리스트)
        # 2. 체크리스트 삭제 (소프트 삭제 권장)
        # 3. 관련 데이터 정리
        
        return APIResponse(
            success=True,
            message="체크리스트가 삭제되었습니다."
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail="체크리스트 삭제에 실패했습니다.") 