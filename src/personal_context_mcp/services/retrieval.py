from dataclasses import dataclass

from personal_context_mcp.schemas.context import ContextQuery, RelevantContext
from personal_context_mcp.schemas.memory import MemoryRead, MemorySearchQuery
from personal_context_mcp.schemas.task_outcome import TaskOutcomeRead
from personal_context_mcp.schemas.user_profile import UserProfileRead
from personal_context_mcp.schemas.work_style import WorkStyleRead
from personal_context_mcp.services.memory import MemoryService
from personal_context_mcp.services.profile import ProfileService
from personal_context_mcp.services.task_outcome import TaskOutcomeService
from personal_context_mcp.services.work_style import WorkStyleService


@dataclass
class RetrievalLimits:
    memories: int = 5
    task_outcomes: int = 3


class RetrievalService:
    def __init__(
        self,
        profile_service: ProfileService,
        work_style_service: WorkStyleService,
        memory_service: MemoryService,
        task_outcome_service: TaskOutcomeService,
        limits: RetrievalLimits | None = None,
    ) -> None:
        self.profile_service = profile_service
        self.work_style_service = work_style_service
        self.memory_service = memory_service
        self.task_outcome_service = task_outcome_service
        self.limits = limits or RetrievalLimits()

    def get_relevant_context(self, payload: ContextQuery) -> RelevantContext:
        profile = self.profile_service.get_profile()
        work_style = self.work_style_service.get_work_style()
        memories = self.memory_service.search_memories(
            MemorySearchQuery(
                query=payload.query,
                limit=payload.limit or self.limits.memories,
            )
        )
        task_outcome_models = self.task_outcome_service.repository.search_for_context(
            query=payload.query, limit=self.limits.task_outcomes
        )
        task_outcomes = [TaskOutcomeRead.model_validate(item) for item in task_outcome_models]
        return RelevantContext(
            query=payload.query,
            profile=profile,
            work_style=work_style,
            memories=memories,
            task_outcomes=task_outcomes,
            context_summary=self._compress_context(profile, work_style, memories, task_outcomes),
        )

    def _compress_context(
        self,
        profile: UserProfileRead | None,
        work_style: WorkStyleRead | None,
        memories: list[MemoryRead],
        task_outcomes: list[TaskOutcomeRead],
    ) -> str:
        parts: list[str] = []
        if profile:
            preferred_stack = profile.preferred_languages + profile.preferred_frameworks
            parts.append(
                "Profile: "
                + ", ".join(
                    item
                    for item in [
                        f"name={profile.name}" if profile.name else "",
                        profile.role,
                        (
                            f"skills={', '.join(profile.primary_skills)}"
                            if profile.primary_skills
                            else ""
                        ),
                        (
                            f"stack={', '.join(preferred_stack)}"
                            if preferred_stack
                            else ""
                        ),
                        f"style={profile.preferred_explanation_style}"
                        if profile.preferred_explanation_style
                        else "",
                    ]
                    if item
                )
            )
        if work_style:
            parts.append(
                "Work style: "
                + ", ".join(
                    item
                    for item in [
                        work_style.task_approach,
                        work_style.explanation_preference,
                        (
                            f"workflow={', '.join(work_style.workflow_patterns)}"
                            if work_style.workflow_patterns
                            else ""
                        ),
                    ]
                    if item
                )
            )
        if memories:
            parts.append(
                "Memories: "
                + "; ".join(
                    f"{memory.title}: {memory.content}"
                    for memory in memories[: self.limits.memories]
                )
            )
        if task_outcomes:
            parts.append(
                "Past outcomes: "
                + "; ".join(
                    f"{outcome.task_summary}: {outcome.final_solution}"
                    for outcome in task_outcomes[: self.limits.task_outcomes]
                )
            )
        return "\n".join(parts)
