from sqlalchemy import func, select
from sqlalchemy.orm import Session

from personal_context_mcp.models.admin import Admin


class AdminRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def create(self, admin: Admin) -> Admin:
        self.session.add(admin)
        self.session.commit()
        self.session.refresh(admin)
        return admin

    def get_by_email(self, email: str) -> Admin | None:
        return self.session.scalar(
            select(Admin).where(func.lower(Admin.email) == email.lower())
        )

    def get_by_id(self, admin_id: str) -> Admin | None:
        return self.session.get(Admin, admin_id)

    def count(self) -> int:
        return self.session.scalar(select(func.count()).select_from(Admin)) or 0
