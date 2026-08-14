from core.database import SessionLocal
from models.schema import Session
from sqlalchemy.orm import Session as DBSession

class SessionManager:
    def __init__(self, phone_number: str):
        self.phone_number = phone_number

    def get_or_create_session(self, db: DBSession) -> Session:
        session_obj = db.query(Session).filter(Session.phone_number == self.phone_number).first()
        if not session_obj:
            session_obj = Session(
                phone_number=self.phone_number,
                conversation_history=[],
                execution_history=[],
                draft_history=[],
                tool_outputs=[],
                pending_approval_state=False
            )
            db.add(session_obj)
            db.commit()
            db.refresh(session_obj)
        return session_obj

    def append_conversation(self, db: DBSession, role: str, content: str):
        session_obj = self.get_or_create_session(db)
        history = list(session_obj.conversation_history)
        history.append({"role": role, "content": content})
        session_obj.conversation_history = history
        db.commit()

    def set_pending_approval(self, db: DBSession, state: bool):
        session_obj = self.get_or_create_session(db)
        session_obj.pending_approval_state = state
        db.commit()
