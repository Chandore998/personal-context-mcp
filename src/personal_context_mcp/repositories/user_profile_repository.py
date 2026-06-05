from sqlalchemy import select
from sqlalchemy.orm import Session

from personal_context_mcp.models.user_profile import UserProfile
from personal_context_mcp.schemas.user_profile import UserProfileCreate


class UserProfileRepository:
    def __init__(self, session: Session, user_id: str = "default") -> None:
        self.session = session
        self.user_id = user_id

    def get_active(self) -> UserProfile | None:
        stmt = (
            select(UserProfile)
            .where(UserProfile.user_id == self.user_id)
            .where(UserProfile.is_active.is_(True))
            .order_by(UserProfile.updated_at.desc())
            .limit(1)
        )
        return self.session.scalar(stmt)

    def upsert_active(self, payload: UserProfileCreate) -> UserProfile:
        profile = self.get_active()
        if profile is None:
            profile = UserProfile(**payload.model_dump(), user_id=self.user_id)
            self.session.add(profile)
        else:
            for field, value in payload.model_dump().items():
                setattr(profile, field, value)

        self.session.flush()
        self.session.commit()
        return profile
