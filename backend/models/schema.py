from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean
from sqlalchemy.dialects.postgresql import JSONB
from pgvector.sqlalchemy import Vector
from core.database import Base
import datetime

class Email(Base):
    __tablename__ = "emails"

    id = Column(Integer, primary_key=True, index=True)
    message_id = Column(String, unique=True, index=True)
    sender = Column(String)
    subject = Column(String)
    body = Column(Text)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)
    embedding = Column(Vector(384)) # sentence-transformers all-MiniLM-L6-v2 uses 384 dimensions

class Session(Base):
    __tablename__ = "sessions"

    id = Column(Integer, primary_key=True, index=True)
    phone_number = Column(String, unique=True, index=True)
    
    # Stores arrays of messages {"role": "user/agent", "content": "..."}
    conversation_history = Column(JSONB, default=list)
    
    # Execution plan history
    execution_history = Column(JSONB, default=list)
    
    # Store draft details
    draft_history = Column(JSONB, default=list)
    
    # Store output from tools
    tool_outputs = Column(JSONB, default=list)
    
    # Pending approval state
    pending_approval_state = Column(Boolean, default=False)
