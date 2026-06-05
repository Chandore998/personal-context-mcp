from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from personal_context_mcp.models.user_session import UserSession


class UserSessionRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def upsert(self, user_id: str, ip_address: str | None = None) -> UserSession:
        sess = self.session.scalar(select(UserSession).where(UserSession.user_id == user_id))
        if sess is None:
            sess = UserSession(
                id=str(uuid4()),
                user_id=user_id,
                ip_address=ip_address,
                last_seen_at=datetime.now(UTC),
            )
            self.session.add(sess)
        else:
            sess.last_seen_at = datetime.now(UTC)
            if ip_address:
                sess.ip_address = ip_address
        self.session.flush()
        self.session.commit()
        return sess

    def get_by_user_id(self, user_id: str) -> UserSession | None:
        return self.session.scalar(select(UserSession).where(UserSession.user_id == user_id))

    def list_all(self) -> list[UserSession]:
        return list(
            self.session.scalars(select(UserSession).order_by(UserSession.last_seen_at.desc()))
        )
