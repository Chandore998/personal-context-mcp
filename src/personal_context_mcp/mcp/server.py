from collections.abc import Callable
from typing import Any

from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings

from personal_context_mcp.auth.api_key import current_user_id_var
from personal_context_mcp.config.settings import get_settings
from personal_context_mcp.models.enums import MemoryType
from personal_context_mcp.schemas.context import ContextQuery
from personal_context_mcp.schemas.memory import MemoryCreate, MemorySearchQuery
from personal_context_mcp.schemas.task_outcome import TaskOutcomeCreate
from personal_context_mcp.services.dependencies import (
    build_memory_service,
    build_profile_service,
    build_retrieval_service,
    build_task_outcome_service,
    build_work_style_service,
)


def _require_user_id() -> str:
    """Return the current user_id, or 'default' when auth is disabled."""
    return current_user_id_var.get() or "default"


class PersonalContextMCPServer:
    def create_fastmcp_server(self, streamable_http_path: str = "/mcp") -> FastMCP:
        settings = get_settings()
        allowed_hosts = ["127.0.0.1:*", "localhost:*", "[::1]:*"]
        allowed_origins = ["http://127.0.0.1:*", "http://localhost:*", "http://[::1]:*"]

        if settings.railway_public_domain:
            allowed_hosts.append(settings.railway_public_domain)
            allowed_origins.extend(
                [
                    f"https://{settings.railway_public_domain}",
                    f"http://{settings.railway_public_domain}",
                ]
            )

        allowed_hosts.extend(settings.mcp_allowed_hosts)
        allowed_origins.extend(settings.mcp_allowed_origins)

        mcp = FastMCP(
            name=settings.mcp_server_name,
            log_level=settings.log_level,
            streamable_http_path=streamable_http_path,
            stateless_http=True,
            json_response=True,
            transport_security=TransportSecuritySettings(
                enable_dns_rebinding_protection=settings.mcp_enable_dns_rebinding_protection,
                allowed_hosts=sorted(set(allowed_hosts)),
                allowed_origins=sorted(set(allowed_origins)),
            ),
        )

        @mcp.tool()
        def get_user_profile() -> dict[str, Any] | None:
            """Return the user's stored profile for personalization.

            Use this before answering when stable identity, skills, or preferences
            matter. Returns the current profile record or null if none is stored.
            """
            user_id = _require_user_id()
            service = build_profile_service(user_id)
            profile = service.get_profile()
            return profile.model_dump() if profile else None

        @mcp.tool()
        def get_work_style() -> dict[str, Any] | None:
            """Return the user's preferred working and communication style.

            Use this before planning or execution when workflow preferences should
            shape the response. Returns the active work-style record or null.
            """
            user_id = _require_user_id()
            service = build_work_style_service(user_id)
            work_style = service.get_work_style()
            return work_style.model_dump() if work_style else None

        @mcp.tool()
        def search_memory(
            query: str,
            tags: list[str] | None = None,
            limit: int = 5,
        ) -> list[dict[str, Any]]:
            """Search stored memories for specific facts, preferences, or notes.

            Use this for targeted lookup when you already know what kind of detail
            you need. Returns matching memory entries filtered by query and tags.
            """
            user_id = _require_user_id()
            service = build_memory_service(user_id)
            results = service.search_memories(
                MemorySearchQuery(query=query, tags=tags or [], limit=limit)
            )
            return [result.model_dump() for result in results]

        @mcp.tool()
        def get_relevant_context(
            query: str,
            tags: list[str] | None = None,
            limit: int = 5,
        ) -> dict[str, Any]:
            """Return the most relevant stored context for the current task.

            Use this as the primary context-loading tool before handling a query or
            request. Returns a compact bundle with profile, work style, memories,
            task outcomes, and a compressed context summary.
            """
            user_id = _require_user_id()
            service = build_retrieval_service(user_id)
            context = service.get_relevant_context(ContextQuery(query=query, limit=limit))
            return context.model_dump()

        @mcp.tool()
        def save_memory(
            title: str,
            content: str,
            memory_type: MemoryType,
            tags: list[str] | None = None,
            source: str | None = None,
            importance: int = 1,
        ) -> dict[str, Any]:
            """Save a reusable memory for future conversations and tasks.

            Use this when the user shares a durable fact, preference, decision, or
            project note worth remembering. Persists a memory record and returns it.
            """
            user_id = _require_user_id()
            service = build_memory_service(user_id)
            memory = service.create_memory(
                MemoryCreate.model_validate(
                    {
                        "title": title,
                        "content": content,
                        "memory_type": memory_type,
                        "tags": tags or [],
                        "source": source,
                        "importance": importance,
                    }
                )
            )
            return memory.model_dump()

        @mcp.tool()
        def save_task_outcome(
            task_summary: str,
            final_solution: str | None = None,
            decisions: list[str] | None = None,
            mistakes: list[str] | None = None,
            corrections: list[str] | None = None,
            learned_preferences: list[str] | None = None,
            source: str | None = None,
        ) -> dict[str, Any]:
            """Save the outcome of a completed task for future reference.

            Use this after finishing work to record the solution, decisions,
            mistakes, corrections, or learned preferences. Persists the completed
            task outcome and returns the saved record.
            """
            user_id = _require_user_id()
            service = build_task_outcome_service(user_id)
            task_outcome = service.create_task_outcome(
                TaskOutcomeCreate.model_validate(
                    {
                        "task_summary": task_summary,
                        "final_solution": final_solution,
                        "decisions": decisions or [],
                        "mistakes": mistakes or [],
                        "corrections": corrections or [],
                        "learned_preferences": learned_preferences or [],
                        "source": source,
                    }
                )
            )
            return task_outcome.model_dump()

        return mcp


    # --- Instance methods (used by get_tool_registry / tests) ---

    def get_user_profile(self) -> dict[str, Any] | None:
        service = build_profile_service(_require_user_id())
        profile = service.get_profile()
        return profile.model_dump() if profile else None

    def get_work_style(self) -> dict[str, Any] | None:
        service = build_work_style_service(_require_user_id())
        work_style = service.get_work_style()
        return work_style.model_dump() if work_style else None

    def search_memory(
        self,
        query: str,
        tags: list[str] | None = None,
        limit: int = 5,
    ) -> list[dict[str, Any]]:
        service = build_memory_service(_require_user_id())
        results = service.search_memories(MemorySearchQuery(query=query, tags=tags or [], limit=limit))
        return [result.model_dump() for result in results]

    def get_relevant_context(
        self,
        query: str,
        tags: list[str] | None = None,
        limit: int = 5,
    ) -> dict[str, Any]:
        service = build_retrieval_service(_require_user_id())
        context = service.get_relevant_context(ContextQuery(query=query, limit=limit))
        return context.model_dump()

    def save_memory(self, payload: dict[str, Any]) -> dict[str, Any]:
        service = build_memory_service(_require_user_id())
        memory = service.create_memory(MemoryCreate.model_validate(payload))
        return memory.model_dump()

    def save_task_outcome(self, payload: dict[str, Any]) -> dict[str, Any]:
        service = build_task_outcome_service(_require_user_id())
        task_outcome = service.create_task_outcome(TaskOutcomeCreate.model_validate(payload))
        return task_outcome.model_dump()


def get_tool_registry(server: PersonalContextMCPServer) -> dict[str, Callable[..., Any]]:
    return {
        "get_user_profile": server.get_user_profile,
        "get_work_style": server.get_work_style,
        "search_memory": server.search_memory,
        "get_relevant_context": server.get_relevant_context,
        "save_memory": server.save_memory,
        "save_task_outcome": server.save_task_outcome,
    }


def build_personal_context_mcp_server() -> PersonalContextMCPServer:
    return PersonalContextMCPServer()
