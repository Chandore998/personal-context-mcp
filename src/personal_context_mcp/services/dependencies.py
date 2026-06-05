from fastapi import Depends

from personal_context_mcp.auth.api_key import current_user_id_var
from personal_context_mcp.config.settings import get_settings
from personal_context_mcp.db.session import get_db_session
from personal_context_mcp.repositories.memory_repository import MemoryRepository
from personal_context_mcp.repositories.task_outcome_repository import TaskOutcomeRepository
from personal_context_mcp.repositories.user_auth_repository import UserAuthRepository
from personal_context_mcp.repositories.user_profile_repository import UserProfileRepository
from personal_context_mcp.repositories.user_session_repository import UserSessionRepository
from personal_context_mcp.repositories.work_style_repository import WorkStyleRepository
from personal_context_mcp.services.auth_service import AuthService
from personal_context_mcp.services.memory import MemoryService
from personal_context_mcp.services.profile import ProfileService
from personal_context_mcp.services.retrieval import RetrievalLimits, RetrievalService
from personal_context_mcp.services.task_outcome import TaskOutcomeService
from personal_context_mcp.services.work_style import WorkStyleService


# --- Pure builders (used by MCP tools, tests, and FastAPI deps below) ---

def build_profile_service(user_id: str) -> ProfileService:
    return ProfileService(UserProfileRepository(get_db_session(), user_id=user_id))


def build_work_style_service(user_id: str) -> WorkStyleService:
    return WorkStyleService(WorkStyleRepository(get_db_session(), user_id=user_id))


def build_memory_service(user_id: str) -> MemoryService:
    return MemoryService(
        MemoryRepository(get_db_session(), user_id=user_id),
        profile_service=build_profile_service(user_id),
        work_style_service=build_work_style_service(user_id),
    )


def build_task_outcome_service(user_id: str) -> TaskOutcomeService:
    return TaskOutcomeService(TaskOutcomeRepository(get_db_session(), user_id=user_id))


def build_retrieval_service(user_id: str) -> RetrievalService:
    settings = get_settings()
    return RetrievalService(
        profile_service=build_profile_service(user_id),
        work_style_service=build_work_style_service(user_id),
        memory_service=build_memory_service(user_id),
        task_outcome_service=build_task_outcome_service(user_id),
        limits=RetrievalLimits(
            memories=settings.context_memory_limit,
            task_outcomes=settings.context_task_limit,
        ),
    )


def get_auth_service() -> AuthService:
    session = get_db_session()
    return AuthService(
        user_repo=UserAuthRepository(session),
        session_repo=UserSessionRepository(session),
    )


# --- FastAPI dependency to resolve current user from contextvar (set by auth middleware) ---

def get_current_user_id() -> str:
    """Return user_id set by auth middleware, or 'default' when auth is disabled."""
    return current_user_id_var.get() or "default"


# --- FastAPI service deps (used with Depends() in routes) ---

def get_profile_service(user_id: str = Depends(get_current_user_id)) -> ProfileService:
    return build_profile_service(user_id)


def get_work_style_service(user_id: str = Depends(get_current_user_id)) -> WorkStyleService:
    return build_work_style_service(user_id)


def get_memory_service(user_id: str = Depends(get_current_user_id)) -> MemoryService:
    return build_memory_service(user_id)


def get_task_outcome_service(user_id: str = Depends(get_current_user_id)) -> TaskOutcomeService:
    return build_task_outcome_service(user_id)


def get_retrieval_service(user_id: str = Depends(get_current_user_id)) -> RetrievalService:
    return build_retrieval_service(user_id)
