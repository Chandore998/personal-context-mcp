from sqlalchemy import select
from sqlalchemy.orm import Session

from personal_context_mcp.models.work_style import WorkStyle
from personal_context_mcp.schemas.work_style import WorkStyleCreate


class WorkStyleRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get_active(self) -> WorkStyle | None:
        stmt = (
            select(WorkStyle)
            .where(WorkStyle.is_active.is_(True))
            .order_by(WorkStyle.updated_at.desc())
            .limit(1)
        )
        return self.session.scalar(stmt)

    def upsert_active(self, payload: WorkStyleCreate) -> WorkStyle:
        work_style = self.get_active()
        if work_style is None:
            work_style = WorkStyle(**payload.model_dump())
            self.session.add(work_style)
        else:
            for field, value in payload.model_dump().items():
                setattr(work_style, field, value)

        self.session.flush()
        self.session.commit()
        return work_style
