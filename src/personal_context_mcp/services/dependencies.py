from personal_context_mcp.config.settings import get_settings
from personal_context_mcp.db.session import get_db_session
from personal_context_mcp.repositories.memory_repository import MemoryRepository
from personal_context_mcp.repositories.task_outcome_repository import TaskOutcomeRepository
from personal_context_mcp.repositories.user_profile_repository import UserProfileRepository
from personal_context_mcp.repositories.work_style_repository import WorkStyleRepository
from personal_context_mcp.services.memory import MemoryService
from personal_context_mcp.services.profile import ProfileService
from personal_context_mcp.services.retrieval import RetrievalLimits, RetrievalService
from personal_context_mcp.services.task_outcome import TaskOutcomeService
from personal_context_mcp.services.work_style import WorkStyleService


def get_profile_service() -> ProfileService:
    repository = UserProfileRepository(get_db_session())
    return ProfileService(repository)


def get_work_style_service() -> WorkStyleService:
    repository = WorkStyleRepository(get_db_session())
    return WorkStyleService(repository)


def get_memory_service() -> MemoryService:
    repository = MemoryRepository(get_db_session())
    return MemoryService(
        repository,
        profile_service=get_profile_service(),
        work_style_service=get_work_style_service(),
    )


def get_task_outcome_service() -> TaskOutcomeService:
    repository = TaskOutcomeRepository(get_db_session())
    return TaskOutcomeService(repository)


def get_retrieval_service() -> RetrievalService:
    settings = get_settings()
    return RetrievalService(
        profile_service=get_profile_service(),
        work_style_service=get_work_style_service(),
        memory_service=get_memory_service(),
        task_outcome_service=get_task_outcome_service(),
        limits=RetrievalLimits(
            memories=settings.context_memory_limit,
            task_outcomes=settings.context_task_limit,
        ),
    )
