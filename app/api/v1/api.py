# api/v1/api.py
from fastapi import APIRouter
from app.api.v1.endpoints import auth, users, intents, questions, checklists, feedback

api_router = APIRouter()

# nowwhat 서비스 API 엔드포인트 등록
api_router.include_router(auth.router, prefix="/auth", tags=["authentication"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(intents.router, prefix="/intents", tags=["intents"])
api_router.include_router(questions.router, prefix="/questions", tags=["questions"])
api_router.include_router(checklists.router, prefix="/checklists", tags=["checklists"])
api_router.include_router(feedback.router, prefix="/feedback", tags=["feedback"])