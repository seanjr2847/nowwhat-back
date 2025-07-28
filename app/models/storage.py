from typing import Dict, List, Any, Optional
from datetime import datetime
from enum import Enum

# 메모리 내 저장소 (실제 구현에서는 데이터베이스 사용)
class InMemoryStore:
    def __init__(self):
        self.users: Dict[str, Dict[str, Any]] = {}
        self.intents: Dict[str, Dict[str, Any]] = {}
        self.questions: Dict[str, Dict[str, Any]] = {}
        self.answers: Dict[str, Dict[str, Any]] = {}
        self.checklists: Dict[str, Dict[str, Any]] = {}
        self.checklist_items: Dict[str, Dict[str, Any]] = {}
        self.feedback: Dict[str, Dict[str, Any]] = {}
        self.user_sessions: Dict[str, Dict[str, Any]] = {}
    
    def create_id(self, prefix: str = "") -> str:
        """UUID 스타일의 ID 생성"""
        import uuid
        return f"{prefix}{str(uuid.uuid4()).replace('-', '')}"
    
    def save_user(self, user_data: Dict[str, Any]) -> str:
        """사용자 저장"""
        user_id = user_data.get("id") or self.create_id("user_")
        user_data["id"] = user_id
        user_data["createdAt"] = user_data.get("createdAt", datetime.now())
        self.users[user_id] = user_data
        return user_id
    
    def get_user(self, user_id: str) -> Optional[Dict[str, Any]]:
        """사용자 조회"""
        return self.users.get(user_id)
    
    def save_checklist(self, checklist_data: Dict[str, Any]) -> str:
        """체크리스트 저장"""
        checklist_id = checklist_data.get("id") or self.create_id("checklist_")
        checklist_data["id"] = checklist_id
        checklist_data["createdAt"] = checklist_data.get("createdAt", datetime.now())
        checklist_data["updatedAt"] = datetime.now()
        self.checklists[checklist_id] = checklist_data
        return checklist_id
    
    def get_checklist(self, checklist_id: str) -> Optional[Dict[str, Any]]:
        """체크리스트 조회"""
        return self.checklists.get(checklist_id)
    
    def get_user_checklists(self, user_id: str, filters: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """사용자 체크리스트 목록 조회"""
        user_checklists = [
            checklist for checklist in self.checklists.values()
            if checklist.get("userId") == user_id
        ]
        
        # 필터링 로직 적용 (category, status 등)
        if filters:
            if filters.get("category"):
                user_checklists = [
                    cl for cl in user_checklists 
                    if cl.get("category") == filters["category"]
                ]
            if filters.get("status"):
                # status 필터링 로직
                pass
        
        return user_checklists
    
    def save_feedback(self, feedback_data: Dict[str, Any]) -> str:
        """피드백 저장"""
        feedback_id = feedback_data.get("id") or self.create_id("feedback_")
        feedback_data["id"] = feedback_id
        feedback_data["createdAt"] = feedback_data.get("createdAt", datetime.now())
        self.feedback[feedback_id] = feedback_data
        return feedback_id
    
    def save_answer(self, answer_data: Dict[str, Any]) -> str:
        """답변 저장"""
        answer_id = answer_data.get("id") or self.create_id("answer_")
        answer_data["id"] = answer_id
        answer_data["createdAt"] = answer_data.get("createdAt", datetime.now())
        self.answers[answer_id] = answer_data
        return answer_id

# 전역 저장소 인스턴스
store = InMemoryStore() 