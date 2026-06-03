from personal_context_mcp.repositories.user_profile_repository import UserProfileRepository
from personal_context_mcp.schemas.user_profile import UserProfileCreate, UserProfileRead


class ProfileService:
    def __init__(self, repository: UserProfileRepository) -> None:
        self.repository = repository

    def get_profile(self) -> UserProfileRead | None:
        profile = self.repository.get_active()
        return UserProfileRead.model_validate(profile) if profile else None

    def upsert_profile(self, payload: UserProfileCreate) -> UserProfileRead:
        profile = self.repository.upsert_active(payload)
        return UserProfileRead.model_validate(profile)

    def merge_profile_updates(self, updates: dict[str, object]) -> UserProfileRead | None:
        clean_updates = {key: value for key, value in updates.items() if value not in (None, "", [])}
        if not clean_updates:
            return self.get_profile()

        profile = self.get_profile()
        payload = profile.model_dump() if profile else UserProfileCreate().model_dump()
        payload.pop("id", None)
        payload.pop("created_at", None)
        payload.pop("updated_at", None)

        for key, value in clean_updates.items():
            if isinstance(value, list):
                payload[key] = self._merge_unique_list(payload.get(key, []), value)
            else:
                payload[key] = value

        return self.upsert_profile(UserProfileCreate.model_validate(payload))

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
