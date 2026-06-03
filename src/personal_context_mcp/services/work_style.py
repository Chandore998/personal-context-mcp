from personal_context_mcp.repositories.work_style_repository import WorkStyleRepository
from personal_context_mcp.schemas.work_style import WorkStyleCreate, WorkStyleRead


class WorkStyleService:
    def __init__(self, repository: WorkStyleRepository) -> None:
        self.repository = repository

    def get_work_style(self) -> WorkStyleRead | None:
        work_style = self.repository.get_active()
        return WorkStyleRead.model_validate(work_style) if work_style else None

    def upsert_work_style(self, payload: WorkStyleCreate) -> WorkStyleRead:
        work_style = self.repository.upsert_active(payload)
        return WorkStyleRead.model_validate(work_style)

    def merge_work_style_updates(self, updates: dict[str, object]) -> WorkStyleRead | None:
        clean_updates = {key: value for key, value in updates.items() if value not in (None, "", [])}
        if not clean_updates:
            return self.get_work_style()

        work_style = self.get_work_style()
        payload = work_style.model_dump() if work_style else WorkStyleCreate().model_dump()
        payload.pop("id", None)
        payload.pop("created_at", None)
        payload.pop("updated_at", None)

        for key, value in clean_updates.items():
            if isinstance(value, list):
                payload[key] = self._merge_unique_list(payload.get(key, []), value)
            else:
                payload[key] = value

        return self.upsert_work_style(WorkStyleCreate.model_validate(payload))

    @staticmethod
    def _merge_unique_list(existing: list[object], incoming: list[object]) -> list[object]:
        merged = list(existing)
        seen = {str(item).strip().lower() for item in merged}
        for item in incoming:
            normalized = str(item).strip().lower()
            if normalized and normalized not in seen:
                merged.append(item)
                seen.add(normalized)
        return merged
