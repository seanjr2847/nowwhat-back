from fastapi import APIRouter, HTTPException, Query
from typing import Optional
from app.schemas.notion import Comment, CommentCreateRequest, CommentListResponse

router = APIRouter()

@router.post("/", response_model=Comment)
async def create_comment(comment_data: CommentCreateRequest):
    """새 댓글을 생성합니다."""
    # TODO: 실제 구현 로직
    raise HTTPException(status_code=501, detail="Not implemented")

@router.get("/", response_model=CommentListResponse)
async def get_comments(
    block_id: Optional[str] = Query(None),
    start_cursor: Optional[str] = Query(None),
    page_size: Optional[int] = Query(100, le=100)
):
    """댓글 목록을 조회합니다."""
    # TODO: 실제 구현 로직
    return CommentListResponse(
        object="list",
        results=[],
        has_more=False,
        next_cursor=None
    ) 