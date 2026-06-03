from personal_context_mcp.repositories.task_outcome_repository import TaskOutcomeRepository
from personal_context_mcp.schemas.task_outcome import TaskOutcomeCreate, TaskOutcomeRead


class TaskOutcomeService:
    def __init__(self, repository: TaskOutcomeRepository) -> None:
        self.repository = repository

    def create_task_outcome(self, payload: TaskOutcomeCreate) -> TaskOutcomeRead:
        task_outcome = self.repository.create(payload)
        return TaskOutcomeRead.model_validate(task_outcome)

    def list_task_outcomes(self, limit: int = 20) -> list[TaskOutcomeRead]:
        task_outcomes = self.repository.list_recent(limit=limit)
        return [TaskOutcomeRead.model_validate(task_outcome) for task_outcome in task_outcomes]
