from sqlalchemy import Column, String, Boolean, ForeignKey, Integer
from sqlalchemy.orm import relationship
from database import Base

class Question(Base):
   __tablename__ = "questions"
   
   id = Column(String, primary_key=True)  # q_duration
   text = Column(String)
   type = Column(String)  # multiple, text, etc
   required = Column(Boolean, default=True)
   intent_id = Column(String, ForeignKey("intents.id"))
   
   options = relationship("Option", back_populates="question")

class Option(Base):
   __tablename__ = "options"
   
   id = Column(String, primary_key=True)  # opt_3days
   text = Column(String)
   value = Column(String)
   question_id = Column(String, ForeignKey("questions.id"))
   
   question = relationship("Question", back_populates="options")

class Intent(Base):
   __tablename__ = "intents"
   
   id = Column(String, primary_key=True)  # intent_travel_plan
   name = Column(String)
   
   questions = relationship("Question")