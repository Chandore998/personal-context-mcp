from sqlalchemy import func, select
from sqlalchemy.orm import Session

from personal_context_mcp.models.user_auth import UserAuth


class UserAuthRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def create(self, user: UserAuth) -> UserAuth:
        self.session.add(user)
        self.session.flush()
        self.session.commit()
        return user

    def get_by_key_hash(self, key_hash: str) -> UserAuth | None:
        return self.session.scalar(select(UserAuth).where(UserAuth.key_hash == key_hash))

    def get_by_email(self, email: str) -> UserAuth | None:
        return self.session.scalar(select(UserAuth).where(UserAuth.email == email))

    def get_by_id(self, user_id: str) -> UserAuth | None:
        return self.session.scalar(select(UserAuth).where(UserAuth.id == user_id))

    def list_all(self) -> list[UserAuth]:
        return list(self.session.scalars(select(UserAuth).order_by(UserAuth.created_at.desc())))

    def count(self) -> int:
        return self.session.scalar(select(func.count()).select_from(UserAuth)) or 0

    def save(self, user: UserAuth) -> UserAuth:
        self.session.flush()
        self.session.commit()
        return user

    def delete(self, user: UserAuth) -> None:
        self.session.delete(user)
        self.session.commit()
