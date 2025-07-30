from sqlalchemy import Column, String, Boolean, DateTime, Float, Integer, Text, ForeignKey, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base
import uuid

def generate_uuid():
    return str(uuid.uuid4())

class User(Base):
    __tablename__ = "users"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    email = Column(String, unique=True, nullable=False)
    name = Column(String, nullable=False)
    profile_image = Column(String, nullable=True)
    google_id = Column(String, unique=True, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    last_login_at = Column(DateTime, nullable=True)
    
    # 관계
    checklists = relationship("Checklist", back_populates="user")
    answers = relationship("Answer", back_populates="user")
    feedbacks = relationship("Feedback", back_populates="user")

class Intent(Base):
    __tablename__ = "intents"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    category = Column(String, nullable=False)
    created_at = Column(DateTime, server_default=func.now())
    
    # 관계
    questions = relationship("Question", back_populates="intent")

class Question(Base):
    __tablename__ = "questions"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    text = Column(Text, nullable=False)
    type = Column(String, nullable=False)  # single, multiple
    options = Column(JSON, nullable=False)  # 선택지 배열
    category = Column(String, nullable=False)
    intent_id = Column(String, ForeignKey("intents.id"), nullable=False)
    created_at = Column(DateTime, server_default=func.now())
    
    # 관계
    intent = relationship("Intent", back_populates="questions")
    answers = relationship("Answer", back_populates="question")

class Answer(Base):
    __tablename__ = "answers"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    question_id = Column(String, ForeignKey("questions.id"), nullable=False)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    answer = Column(String, nullable=False)
    answered_at = Column(DateTime, server_default=func.now())
    
    # 관계
    question = relationship("Question", back_populates="answers")
    user = relationship("User", back_populates="answers")

class Checklist(Base):
    __tablename__ = "checklists"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    category = Column(String, nullable=False)
    progress = Column(Float, default=0.0)
    is_public = Column(Boolean, default=True)
    custom_name = Column(String, nullable=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    # 관계
    user = relationship("User", back_populates="checklists")
    items = relationship("ChecklistItem", back_populates="checklist", cascade="all, delete-orphan")
    feedbacks = relationship("Feedback", back_populates="checklist")

class ChecklistItem(Base):
    __tablename__ = "checklist_items"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    checklist_id = Column(String, ForeignKey("checklists.id"), nullable=False)
    text = Column(Text, nullable=False)
    is_completed = Column(Boolean, default=False)
    completed_at = Column(DateTime, nullable=True)
    order = Column(Integer, nullable=False)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    # 관계
    checklist = relationship("Checklist", back_populates="items")
    details = relationship("ChecklistItemDetails", back_populates="item", uselist=False, cascade="all, delete-orphan")

class ChecklistItemDetails(Base):
    __tablename__ = "checklist_item_details"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    item_id = Column(String, ForeignKey("checklist_items.id"), nullable=False, unique=True)
    
    # 퍼플렉시티 검색 결과 저장
    tips = Column(JSON, nullable=True)  # ["실용적 팁1", "실용적 팁2", ...]
    contacts = Column(JSON, nullable=True)  # [{"name": "이름", "phone": "번호", "email": "메일"}, ...]
    links = Column(JSON, nullable=True)  # [{"title": "제목", "url": "링크"}, ...]
    price = Column(String, nullable=True)  # "예상 비용 정보"
    location = Column(String, nullable=True)  # "위치/주소 정보"
    
    # 메타데이터
    search_source = Column(String, default="perplexity")  # 검색 소스
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    # 관계
    item = relationship("ChecklistItem", back_populates="details")

class Feedback(Base):
    __tablename__ = "feedbacks"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    checklist_id = Column(String, ForeignKey("checklists.id"), nullable=False)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    is_positive = Column(Boolean, nullable=False)
    rating = Column(Integer, nullable=True)
    comment = Column(Text, nullable=True)
    categories = Column(JSON, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    
    # 관계
    checklist = relationship("Checklist", back_populates="feedbacks")
    user = relationship("User", back_populates="feedbacks")

class UserSession(Base):
    __tablename__ = "user_sessions"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    refresh_token = Column(String, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, server_default=func.now())
    
    # 관계
    user = relationship("User")

class IntentSession(Base):
    __tablename__ = "intent_sessions"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    session_id = Column(String, unique=True, nullable=False)
    goal = Column(Text, nullable=False)
    user_ip = Column(String, nullable=True)
    user_country = Column(String, nullable=True)
    generated_intents = Column(JSON, nullable=True)  # 생성된 의도 옵션들
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

 