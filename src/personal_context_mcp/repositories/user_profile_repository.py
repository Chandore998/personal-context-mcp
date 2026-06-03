from sqlalchemy import select
from sqlalchemy.orm import Session

from personal_context_mcp.models.user_profile import UserProfile
from personal_context_mcp.schemas.user_profile import UserProfileCreate


class UserProfileRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get_active(self) -> UserProfile | None:
        stmt = (
            select(UserProfile)
            .where(UserProfile.is_active.is_(True))
            .order_by(UserProfile.updated_at.desc())
            .limit(1)
        )
        return self.session.scalar(stmt)

    def upsert_active(self, payload: UserProfileCreate) -> UserProfile:
        profile = self.get_active()
        if profile is None:
            profile = UserProfile(**payload.model_dump())
            self.session.add(profile)
        else:
            for field, value in payload.model_dump().items():
                setattr(profile, field, value)

        self.session.flush()
        self.session.commit()
        return profile
