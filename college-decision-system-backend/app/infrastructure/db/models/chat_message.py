from sqlalchemy import Column, String, DateTime, Text, JSON
from datetime import datetime, timezone
import uuid

from app.infrastructure.db.session import Base
from app.infrastructure.db.models.decision_common import utcnow

class ChatMessageModel(Base):
    __tablename__ = "chat_messages"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    session_id = Column(String, index=True, nullable=False)
    role = Column(String, nullable=False) # 'user' or 'model'
    content = Column(Text, nullable=False)
    tool_calls = Column(JSON, nullable=True) # Optional JSON array tracking any tools used
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)
