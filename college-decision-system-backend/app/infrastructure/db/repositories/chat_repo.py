import uuid
from sqlalchemy.orm import Session
from app.infrastructure.db.models.chat_message import ChatMessageModel

class ChatRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_history(self, session_id: str, limit: int = 10) -> list[ChatMessageModel]:
        """Fetch the most recent messages for a session, ordered by created_at ascending."""
        # We query descending to get the latest `limit` messages, then reverse them
        # so they are in chronological order for the LLM.
        messages = (
            self.db.query(ChatMessageModel)
            .filter(ChatMessageModel.session_id == session_id)
            .order_by(ChatMessageModel.created_at.desc())
            .limit(limit)
            .all()
        )
        return list(reversed(messages))

    def add_message(
        self,
        session_id: str,
        role: str,
        content: str,
        tool_calls: list[dict] | None = None
    ) -> ChatMessageModel:
        """Add a new message to the chat history."""
        msg = ChatMessageModel(
            id=str(uuid.uuid4()),
            session_id=session_id,
            role=role,
            content=content,
            tool_calls=tool_calls
        )
        self.db.add(msg)
        self.db.commit()
        self.db.refresh(msg)
        return msg
