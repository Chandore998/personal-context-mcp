import re
from dataclasses import dataclass, field

from personal_context_mcp.schemas.memory import MemoryCreate

KNOWN_LANGUAGES = {
    "python",
    "javascript",
    "typescript",
    "java",
    "c#",
    "c++",
    "go",
    "rust",
    "ruby",
    "php",
    "swift",
    "kotlin",
}
KNOWN_FRAMEWORKS = {
    "fastapi",
    "django",
    "flask",
    "react",
    "next.js",
    "nextjs",
    "vue",
    "angular",
    "spring",
    "laravel",
    "express",
}
CONNECTOR_WORDS = {
    "and",
    "with",
    "using",
    "prefer",
    "like",
    "usually",
    "mainly",
    "mostly",
    "currently",
    "often",
}


@dataclass
class PromotionUpdates:
    profile: dict[str, object] = field(default_factory=dict)
    work_style: dict[str, object] = field(default_factory=dict)


class MemoryFactPromotionService:
    def extract_updates(self, payload: MemoryCreate) -> PromotionUpdates:
        updates = PromotionUpdates()
        segments = self._build_segments(payload)
        for segment in segments:
            lowered = segment.lower()
            self._extract_name(lowered, segment, updates)
            self._extract_role(lowered, segment, updates)
            self._extract_stack(lowered, segment, updates)
            self._extract_preferences(lowered, segment, updates)
            self._extract_workflow(lowered, segment, updates)
        return updates

    def _build_segments(self, payload: MemoryCreate) -> list[str]:
        parts = [payload.title, payload.content, " ".join(payload.tags)]
        text = ". ".join(part for part in parts if part)
        return [segment.strip() for segment in re.split(r"[.!?\n]+", text) if segment.strip()]

    def _extract_name(self, lowered: str, original: str, updates: PromotionUpdates) -> None:
        match = re.search(r"\bmy name is\s+([a-z][a-z .'\-]{0,60})$", lowered)
        if not match:
            match = re.search(r"\bthe user's name is\s+([a-z][a-z .'\-]{0,60})$", lowered)
        if match:
            updates.profile["name"] = self._to_title_case(match.group(1))

    def _extract_role(self, lowered: str, original: str, updates: PromotionUpdates) -> None:
        patterns = [
            r"\bi am\s+(?:an?\s+)?(.+)$",
            r"\bi'm\s+(?:an?\s+)?(.+)$",
            r"\bi work as\s+(?:an?\s+)?(.+)$",
            r"\bmy role is\s+(.+)$",
            r"\bthe user is\s+(?:an?\s+)?(.+)$",
        ]
        for pattern in patterns:
            match = re.search(pattern, lowered)
            if match:
                role = self._clean_phrase(match.group(1))
                if role:
                    updates.profile["role"] = role
                return

    def _extract_stack(self, lowered: str, original: str, updates: PromotionUpdates) -> None:
        patterns = [
            r"\bi use\s+(.+)$",
            r"\bi work with\s+(.+)$",
            r"\bmy stack is\s+(.+)$",
            r"\bi know\s+(.+)$",
            r"\bskills?\s*[:\-]\s*(.+)$",
        ]
        for pattern in patterns:
            match = re.search(pattern, lowered)
            if not match:
                continue
            values = self._split_values(match.group(1))
            if not values:
                continue
            languages: list[str] = []
            frameworks: list[str] = []
            skills: list[str] = []
            for value in values:
                normalized = value.lower()
                if normalized in KNOWN_LANGUAGES:
                    languages.append(self._format_stack_value(value))
                elif normalized in KNOWN_FRAMEWORKS:
                    frameworks.append(self._format_stack_value(value))
                else:
                    skills.append(self._format_stack_value(value))

            if languages:
                updates.profile["preferred_languages"] = languages
            if frameworks:
                updates.profile["preferred_frameworks"] = frameworks
            if skills:
                updates.profile["primary_skills"] = skills
            return

    def _extract_preferences(self, lowered: str, original: str, updates: PromotionUpdates) -> None:
        if "explanation" in lowered or "explain" in lowered:
            match = re.search(r"\bi prefer\s+(.+)$", lowered) or re.search(
                r"\bexplain(?: things)? (?:in|with)\s+(.+)$", lowered
            )
            if match:
                value = self._clean_phrase(match.group(1))
                if value:
                    updates.profile["preferred_explanation_style"] = value
                    updates.work_style["explanation_preference"] = value

        if "code style" in lowered:
            match = re.search(r"\b(?:my )?code style is\s+(.+)$", lowered) or re.search(
                r"\bi prefer\s+(.+?)\s+code style$", lowered
            )
            if match:
                value = self._clean_phrase(match.group(1))
                if value:
                    updates.profile["preferred_code_style"] = value

        if "architecture" in lowered:
            match = re.search(r"\b(?:my )?architecture style is\s+(.+)$", lowered) or re.search(
                r"\bi prefer\s+(.+?)\s+architecture$", lowered
            )
            if match:
                value = self._clean_phrase(match.group(1))
                if value:
                    updates.profile["preferred_architecture_style"] = value

        if "communicat" in lowered:
            match = re.search(r"\bi prefer communication(?: that is)?\s+(.+)$", lowered) or re.search(
                r"\bcommunication preference is\s+(.+)$", lowered
            )
            if match:
                value = self._clean_phrase(match.group(1))
                if value:
                    updates.profile["communication_preferences"] = value

    def _extract_workflow(self, lowered: str, original: str, updates: PromotionUpdates) -> None:
        if any(token in lowered for token in ("workflow", "break tasks", "task approach")):
            match = re.search(r"\b(?:my workflow is|my task approach is)\s+(.+)$", lowered) or re.search(
                r"\bi break tasks\s+(.+)$", lowered
            )
            if match:
                value = self._clean_phrase(match.group(1))
                if value:
                    updates.work_style["task_approach"] = value
                    updates.work_style["workflow_patterns"] = [value]

        if "production example" in lowered:
            match = re.search(r"\bi prefer\s+(.+?)\s+production examples?$", lowered)
            if match:
                value = self._clean_phrase(match.group(1))
                if value:
                    updates.work_style["production_example_preference"] = value

        if "common mistake" in lowered or "avoid" in lowered:
            match = re.search(r"\bi want to avoid\s+(.+)$", lowered)
            if match:
                value = self._clean_phrase(match.group(1))
                if value:
                    updates.work_style["common_mistakes_to_avoid"] = [value]

        if "prefer" in lowered and not any(
            token in lowered for token in ("explanation", "code style", "architecture", "communication")
        ):
            match = re.search(r"\bi prefer\s+(.+)$", lowered)
            if match:
                value = self._clean_phrase(match.group(1))
                if value:
                    updates.work_style["common_preferences"] = [value]

    def _split_values(self, text: str) -> list[str]:
        cleaned = re.sub(r"[()]", " ", text.lower())
        for connector in CONNECTOR_WORDS:
            cleaned = re.sub(rf"\b{re.escape(connector)}\b", ",", cleaned)
        values = [self._clean_phrase(item) for item in cleaned.split(",")]
        return [value for value in values if value]

    def _clean_phrase(self, value: str) -> str:
        value = re.sub(r"\b(the user|user|i am|i'm)\b", "", value, flags=re.IGNORECASE)
        value = re.sub(r"\s+", " ", value).strip(" ,.-")
        return value

    def _format_stack_value(self, value: str) -> str:
        normalized = value.lower()
        if normalized == "javascript":
            return "JavaScript"
        if normalized == "typescript":
            return "TypeScript"
        if normalized == "c#":
            return "C#"
        if normalized == "c++":
            return "C++"
        if normalized in {"next.js", "nextjs"}:
            return "Next.js"
        if normalized == "fastapi":
            return "FastAPI"
        return self._to_title_case(normalized)

    def _to_title_case(self, value: str) -> str:
        return " ".join(part.capitalize() for part in value.strip().split())
