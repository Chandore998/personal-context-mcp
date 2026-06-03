from personal_context_mcp.repositories.memory_repository import MemoryRepository
from personal_context_mcp.schemas.memory import MemoryCreate, MemoryRead, MemorySearchQuery
from personal_context_mcp.services.memory_fact_promotion import MemoryFactPromotionService
from personal_context_mcp.services.profile import ProfileService
from personal_context_mcp.services.work_style import WorkStyleService


class MemoryService:
    def __init__(
        self,
        repository: MemoryRepository,
        profile_service: ProfileService | None = None,
        work_style_service: WorkStyleService | None = None,
        promotion_service: MemoryFactPromotionService | None = None,
    ) -> None:
        self.repository = repository
        self.profile_service = profile_service
        self.work_style_service = work_style_service
        self.promotion_service = promotion_service or MemoryFactPromotionService()

    def create_memory(self, payload: MemoryCreate) -> MemoryRead:
        memory = self.repository.create(payload)
        updates = self.promotion_service.extract_updates(payload)
        if self.profile_service:
            self.profile_service.merge_profile_updates(updates.profile)
        if self.work_style_service:
            self.work_style_service.merge_work_style_updates(updates.work_style)
        return MemoryRead.model_validate(memory)

    def search_memories(self, filters: MemorySearchQuery) -> list[MemoryRead]:
        return [MemoryRead.model_validate(memory) for memory in self.repository.search(filters)]

    def list_recent_memories(self, limit: int = 10) -> list[MemoryRead]:
        return [MemoryRead.model_validate(memory) for memory in self.repository.list_recent(limit=limit)]
