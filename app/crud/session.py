from sqlalchemy.orm import Session
from app.models.database import IntentSession
from typing import Optional, List, Dict, Any
import time
import random
import string
import json
import uuid
from datetime import datetime, timedelta

def generate_session_id() -> str:
    """세션 ID 생성: sess_{timestamp}_{random}"""
    timestamp = int(time.time())
    random_str = ''.join(random.choices(string.ascii_lowercase + string.digits, k=6))
    return f"sess_{timestamp}_{random_str}"

def generate_question_set_id() -> str:
    """질문 세트 ID 생성: qs_{timestamp}_{random}"""
    timestamp = int(time.time())
    random_str = ''.join(random.choices(string.ascii_lowercase + string.digits, k=6))
    return f"qs_{timestamp}_{random_str}"

def create_intent_session(
    db: Session,
    goal: str,
    user_ip: Optional[str] = None,
    user_country: Optional[str] = None
) -> IntentSession:
    """새로운 의도 분석 세션 생성"""
    session_id = generate_session_id()
    
    db_session = IntentSession(
        session_id=session_id,
        goal=goal,
        user_ip=user_ip,
        user_country=user_country
    )
    
    db.add(db_session)
    db.commit()
    db.refresh(db_session)
    
    return db_session

def update_intent_session_with_intents(
    db: Session,
    session_id: str,
    intents: List[Dict[str, Any]]
) -> Optional[IntentSession]:
    """생성된 의도 옵션으로 세션 업데이트"""
    db_session = db.query(IntentSession).filter(
        IntentSession.session_id == session_id
    ).first()
    
    if db_session:
        db_session.generated_intents = intents
        db.commit()
        db.refresh(db_session)
        return db_session
    
    return None

def update_intent_session_with_selection(
    db: Session,
    session_id: str,
    selected_intent: str
) -> Optional[IntentSession]:
    """선택된 의도로 세션 업데이트"""
    db_session = db.query(IntentSession).filter(
        IntentSession.session_id == session_id
    ).first()
    
    if db_session:
        # 기존 데이터에 선택된 의도 추가
        if not hasattr(db_session, 'selected_intent') or db_session.selected_intent is None:
            # 새로운 필드가 없으면 generated_intents에 선택 정보 추가
            if db_session.generated_intents:
                for intent in db_session.generated_intents:
                    intent["selected"] = intent.get("title") == selected_intent
        
        db_session.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(db_session)
        return db_session
    
    return None

def save_question_set(
    db: Session,
    session_id: str,
    intent_id: str,
    questions: List[Dict[str, Any]]
) -> str:
    """질문 세트 저장 (세션의 추가 정보로 저장)"""
    question_set_id = generate_question_set_id()
    
    # 세션에 질문 세트 정보 추가
    db_session = db.query(IntentSession).filter(
        IntentSession.session_id == session_id
    ).first()
    
    if db_session:
        # 질문 세트 데이터 구성
        question_set_data = {
            "question_set_id": question_set_id,
            "intent_id": intent_id,
            "questions": questions,
            "created_at": datetime.utcnow().isoformat()
        }
        
        # 세션에 질문 세트 정보 저장 (JSON 형태)
        if not hasattr(db_session, 'question_sets') or db_session.question_sets is None:
            # 새로운 컬럼이 없으면 generated_intents에 추가
            if not db_session.generated_intents:
                db_session.generated_intents = []
            
            # 기존 데이터 구조 유지하면서 질문 정보 추가
            db_session.generated_intents.append({
                "type": "question_set",
                "data": question_set_data
            })
        
        db_session.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(db_session)
    
    return question_set_id

def get_intent_session_by_session_id(
    db: Session,
    session_id: str
) -> Optional[IntentSession]:
    """세션 ID로 의도 분석 세션 조회"""
    return db.query(IntentSession).filter(
        IntentSession.session_id == session_id
    ).first()

def validate_session_for_questions(
    db: Session,
    session_id: str,
    intent_id: str
) -> tuple[bool, Optional[IntentSession], Optional[str]]:
    """질문 생성을 위한 세션 유효성 검증"""
    # 세션 존재 여부 확인
    db_session = get_intent_session_by_session_id(db, session_id)
    if not db_session:
        return False, None, "세션을 찾을 수 없습니다."
    
    # 24시간 유효기간 확인
    if db_session.created_at < datetime.utcnow() - timedelta(hours=24):
        return False, db_session, "세션이 만료되었습니다."
    
    # 의도 선택 여부 확인
    if not db_session.generated_intents:
        return False, db_session, "의도 분석이 완료되지 않았습니다."
    
    # 선택된 의도 확인
    intent_found = False
    if isinstance(db_session.generated_intents, list):
        for intent in db_session.generated_intents:
            if isinstance(intent, dict):
                if intent.get("type") == "question_set":
                    continue  # 질문 세트 데이터는 건너뛰기
                if intent.get("title") == intent_id or intent.get("id") == intent_id:
                    intent_found = True
                    break
    
    if not intent_found:
        return False, db_session, "선택된 의도를 찾을 수 없습니다."
    
    return True, db_session, None

def get_intent_title_from_session(
    db_session: IntentSession,
    intent_id: str
) -> Optional[str]:
    """세션에서 의도 ID에 해당하는 제목 반환"""
    if not db_session.generated_intents:
        return None
    
    for intent in db_session.generated_intents:
        if isinstance(intent, dict) and intent.get("type") != "question_set":
            if intent.get("title") == intent_id or intent.get("id") == intent_id:
                return intent.get("title")
    
    return intent_id  # ID가 곧 제목인 경우 