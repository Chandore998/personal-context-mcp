from fastapi import APIRouter, Depends, Query, status

from personal_context_mcp.schemas.context import ContextQuery, RelevantContext
from personal_context_mcp.schemas.memory import MemoryCreate, MemoryRead, MemorySearchQuery
from personal_context_mcp.schemas.task_outcome import TaskOutcomeCreate, TaskOutcomeRead
from personal_context_mcp.schemas.user_profile import UserProfileCreate, UserProfileRead
from personal_context_mcp.schemas.work_style import WorkStyleCreate, WorkStyleRead
from personal_context_mcp.services.dependencies import (
    get_memory_service,
    get_profile_service,
    get_retrieval_service,
    get_task_outcome_service,
    get_work_style_service,
)
from personal_context_mcp.services.memory import MemoryService
from personal_context_mcp.services.profile import ProfileService
from personal_context_mcp.services.retrieval import RetrievalService
from personal_context_mcp.services.task_outcome import TaskOutcomeService
from personal_context_mcp.services.work_style import WorkStyleService

api_router = APIRouter()


@api_router.get("/health")
def healthcheck() -> dict[str, str]:
    return {"status": "ok"}


@api_router.get("/profile", response_model=UserProfileRead | None)
def get_profile(service: ProfileService = Depends(get_profile_service)) -> UserProfileRead | None:
    return service.get_profile()


@api_router.put("/profile", response_model=UserProfileRead, status_code=status.HTTP_200_OK)
def upsert_profile(
    payload: UserProfileCreate,
    service: ProfileService = Depends(get_profile_service),
) -> UserProfileRead:
    return service.upsert_profile(payload)


@api_router.get("/work-style", response_model=WorkStyleRead | None)
def get_work_style(
    service: WorkStyleService = Depends(get_work_style_service),
) -> WorkStyleRead | None:
    return service.get_work_style()


@api_router.put("/work-style", response_model=WorkStyleRead, status_code=status.HTTP_200_OK)
def upsert_work_style(
    payload: WorkStyleCreate,
    service: WorkStyleService = Depends(get_work_style_service),
) -> WorkStyleRead:
    return service.upsert_work_style(payload)


@api_router.post("/memories", response_model=MemoryRead, status_code=status.HTTP_201_CREATED)
def create_memory(
    payload: MemoryCreate,
    service: MemoryService = Depends(get_memory_service),
) -> MemoryRead:
    return service.create_memory(payload)


@api_router.get("/memories", response_model=list[MemoryRead])
def search_memories(
    query: str = Query(default=""),
    tags: list[str] | None = Query(default=None),
    limit: int = Query(default=5, ge=1, le=20),
    service: MemoryService = Depends(get_memory_service),
) -> list[MemoryRead]:
    return service.search_memories(MemorySearchQuery(query=query, tags=tags or [], limit=limit))


@api_router.get("/memories/recent", response_model=list[MemoryRead])
def list_recent_memories(
    limit: int = Query(default=10, ge=1, le=20),
    service: MemoryService = Depends(get_memory_service),
) -> list[MemoryRead]:
    return service.list_recent_memories(limit=limit)


@api_router.post(
    "/task-outcomes",
    response_model=TaskOutcomeRead,
    status_code=status.HTTP_201_CREATED,
)
def create_task_outcome(
    payload: TaskOutcomeCreate,
    service: TaskOutcomeService = Depends(get_task_outcome_service),
) -> TaskOutcomeRead:
    return service.create_task_outcome(payload)


@api_router.get("/task-outcomes", response_model=list[TaskOutcomeRead])
def list_task_outcomes(
    limit: int = Query(default=20, ge=1, le=50),
    service: TaskOutcomeService = Depends(get_task_outcome_service),
) -> list[TaskOutcomeRead]:
    return service.list_task_outcomes(limit=limit)


@api_router.post("/context", response_model=RelevantContext)
def get_relevant_context(
    payload: ContextQuery,
    service: RetrievalService = Depends(get_retrieval_service),
) -> RelevantContext:
    return service.get_relevant_context(payload)
