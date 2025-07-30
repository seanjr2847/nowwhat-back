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

 