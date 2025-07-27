from sqlalchemy.orm import Session
from app.models.database import IntentSession
from typing import Optional, List, Dict, Any
import time
import random
import string

def generate_session_id() -> str:
    """세션 ID 생성: sess_{timestamp}_{random}"""
    timestamp = int(time.time())
    random_str = ''.join(random.choices(string.ascii_lowercase + string.digits, k=6))
    return f"sess_{timestamp}_{random_str}"

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

def get_intent_session_by_session_id(
    db: Session,
    session_id: str
) -> Optional[IntentSession]:
    """세션 ID로 의도 분석 세션 조회"""
    return db.query(IntentSession).filter(
        IntentSession.session_id == session_id
    ).first() 