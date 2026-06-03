from sqlalchemy import Select, or_, select
from sqlalchemy.orm import Session

from personal_context_mcp.models.task_outcome import TaskOutcome
from personal_context_mcp.schemas.task_outcome import TaskOutcomeCreate


class TaskOutcomeRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def create(self, payload: TaskOutcomeCreate) -> TaskOutcome:
        task_outcome = TaskOutcome(**payload.model_dump())
        self.session.add(task_outcome)
        self.session.flush()
        self.session.commit()
        return task_outcome

    def list_recent(self, limit: int = 10) -> list[TaskOutcome]:
        stmt = select(TaskOutcome).order_by(TaskOutcome.updated_at.desc()).limit(limit)
        return list(self.session.scalars(stmt))

    def search_for_context(self, query: str, *, limit: int = 5) -> list[TaskOutcome]:
        stmt: Select[tuple[TaskOutcome]] = select(TaskOutcome).where(
            or_(
                TaskOutcome.task_summary.ilike(f"%{query}%"),
                TaskOutcome.final_solution.ilike(f"%{query}%"),
            )
        )
        stmt = stmt.order_by(TaskOutcome.updated_at.desc()).limit(limit)
        return list(self.session.scalars(stmt))
