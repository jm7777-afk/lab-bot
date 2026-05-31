from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.sql import func

from app.database import Base


class Conversation(Base):
    __tablename__ = "conversations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    company_id = Column(Integer, nullable=False)
    session_id = Column(String(255), nullable=False)
    channel = Column(String(20), default="web")
    started_at = Column(DateTime, server_default=func.now())
    last_activity = Column(DateTime, server_default=func.now(), onupdate=func.now())


class Message(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, autoincrement=True)
    conversation_id = Column(Integer, nullable=False)
    role = Column(String(10), nullable=False)
    content = Column(Text, nullable=False)
    model_used = Column(String(50), nullable=True)
    tokens_used = Column(Integer, default=0)
    created_at = Column(DateTime, server_default=func.now())
