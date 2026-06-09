from collections.abc import Generator
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from personal_context_mcp.auth.api_key import current_user_id_var
from personal_context_mcp.config.settings import get_settings
from personal_context_mcp.db.session import get_db_session
from personal_context_mcp.models.admin import Admin
from personal_context_mcp.repositories.admin_repository import AdminRepository
from personal_context_mcp.repositories.memory_repository import MemoryRepository
from personal_context_mcp.repositories.task_outcome_repository import TaskOutcomeRepository
from personal_context_mcp.repositories.user_auth_repository import UserAuthRepository
from personal_context_mcp.repositories.user_profile_repository import UserProfileRepository
from personal_context_mcp.repositories.user_session_repository import UserSessionRepository
from personal_context_mcp.repositories.work_style_repository import WorkStyleRepository
from personal_context_mcp.services.admin_auth_service import (
    AdminAuthService,
    InvalidAdminTokenError,
)
from personal_context_mcp.services.auth_service import AuthService
from personal_context_mcp.services.memory import MemoryService
from personal_context_mcp.services.profile import ProfileService
from personal_context_mcp.services.retrieval import RetrievalLimits, RetrievalService
from personal_context_mcp.services.task_outcome import TaskOutcomeService
from personal_context_mcp.services.work_style import WorkStyleService

# --- Pure builders (used by MCP tools, tests, and FastAPI deps below) ---

admin_bearer = HTTPBearer(auto_error=False)


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


def get_request_db_session() -> Generator[Session, None, None]:
    session = get_db_session()
    try:
        yield session
    finally:
        session.close()


def get_admin_auth_service(
    session: Annotated[Session, Depends(get_request_db_session)],
) -> AdminAuthService:
    settings = get_settings()
    return AdminAuthService(
        AdminRepository(session),
        token_secret=settings.admin_token_secret,
        token_expire_minutes=settings.admin_token_expire_minutes,
    )


def get_current_admin(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(admin_bearer)],
    service: Annotated[AdminAuthService, Depends(get_admin_auth_service)],
) -> Admin:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Admin bearer token is required.",
        )
    try:
        return service.authenticate_token(credentials.credentials)
    except InvalidAdminTokenError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
        ) from exc


def get_user_auth_service(
    session: Annotated[Session, Depends(get_request_db_session)],
) -> AuthService:
    return AuthService(
        user_repo=UserAuthRepository(session),
        session_repo=UserSessionRepository(session),
    )


# --- FastAPI dependency to resolve current user from contextvar (set by auth middleware) ---

def get_current_user_id() -> str:
    """Return user_id set by auth middleware, or 'default' when auth is disabled."""
    return current_user_id_var.get() or "default"


# --- FastAPI service deps (used with Depends() in routes) ---

def get_profile_service(
    user_id: Annotated[str, Depends(get_current_user_id)],
    session: Annotated[Session, Depends(get_request_db_session)],
) -> ProfileService:
    return ProfileService(UserProfileRepository(session, user_id=user_id))


def get_work_style_service(
    user_id: Annotated[str, Depends(get_current_user_id)],
    session: Annotated[Session, Depends(get_request_db_session)],
) -> WorkStyleService:
    return WorkStyleService(WorkStyleRepository(session, user_id=user_id))


def get_memory_service(
    user_id: Annotated[str, Depends(get_current_user_id)],
    session: Annotated[Session, Depends(get_request_db_session)],
) -> MemoryService:
    return MemoryService(
        MemoryRepository(session, user_id=user_id),
        profile_service=ProfileService(UserProfileRepository(session, user_id=user_id)),
        work_style_service=WorkStyleService(WorkStyleRepository(session, user_id=user_id)),
    )


def get_task_outcome_service(
    user_id: Annotated[str, Depends(get_current_user_id)],
    session: Annotated[Session, Depends(get_request_db_session)],
) -> TaskOutcomeService:
    return TaskOutcomeService(TaskOutcomeRepository(session, user_id=user_id))


def get_retrieval_service(
    user_id: Annotated[str, Depends(get_current_user_id)],
    session: Annotated[Session, Depends(get_request_db_session)],
) -> RetrievalService:
    settings = get_settings()
    profile_service = ProfileService(UserProfileRepository(session, user_id=user_id))
    work_style_service = WorkStyleService(WorkStyleRepository(session, user_id=user_id))
    memory_service = MemoryService(
        MemoryRepository(session, user_id=user_id),
        profile_service=profile_service,
        work_style_service=work_style_service,
    )
    return RetrievalService(
        profile_service=profile_service,
        work_style_service=work_style_service,
        memory_service=memory_service,
        task_outcome_service=TaskOutcomeService(
            TaskOutcomeRepository(session, user_id=user_id)
        ),
        limits=RetrievalLimits(
            memories=settings.context_memory_limit,
            task_outcomes=settings.context_task_limit,
        ),
    )
