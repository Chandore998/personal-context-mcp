import re

from sqlalchemy import select
from sqlalchemy.orm import Session

from personal_context_mcp.models.enums import MemoryType
from personal_context_mcp.models.memory import Memory
from personal_context_mcp.schemas.memory import MemoryCreate, MemorySearchQuery


class MemoryRepository:
    def __init__(self, session: Session, user_id: str = "default") -> None:
        self.session = session
        self.user_id = user_id

    def create(self, payload: MemoryCreate) -> Memory:
        memory = Memory(**payload.model_dump(), user_id=self.user_id)
        self.session.add(memory)
        self.session.flush()
        self.session.commit()
        return memory

    def list_recent(self, limit: int = 10) -> list[Memory]:
        stmt = (
            select(Memory)
            .where(Memory.user_id == self.user_id)
            .order_by(Memory.created_at.desc(), Memory.id.desc())
            .limit(limit)
        )
        return list(self.session.scalars(stmt))

    def search(self, query: MemorySearchQuery) -> list[Memory]:
        stmt = select(Memory).where(Memory.user_id == self.user_id)
        memories = list(self.session.scalars(stmt))

        if query.tags:
            normalized_tags = {self._normalize(tag) for tag in query.tags if self._normalize(tag)}
            memories = [
                memory
                for memory in memories
                if normalized_tags.issubset(
                    {self._normalize(tag) for tag in memory.tags if self._normalize(tag)}
                )
            ]

        if query.memory_types:
            allowed_types = set(query.memory_types)
            memories = [memory for memory in memories if memory.memory_type in allowed_types]

        tokens = self._tokenize(query.query)
        if not tokens:
            return sorted(
                memories,
                key=lambda memory: (
                    memory.importance,
                    memory.semantic_score or float("-inf"),
                    memory.updated_at,
                ),
                reverse=True,
            )[: query.limit]

        scored = []
        for memory in memories:
            score = self._score_memory(memory, tokens, query.query)
            if score > 0:
                scored.append((score, memory))

        scored.sort(
            key=lambda item: (
                item[0],
                item[1].importance,
                item[1].semantic_score or float("-inf"),
                item[1].updated_at,
            ),
            reverse=True,
        )
        return [memory for _, memory in scored[: query.limit]]

    def search_by_text(
        self,
        text: str,
        *,
        limit: int = 5,
        memory_types: list[MemoryType] | None = None,
    ) -> list[Memory]:
        return self.search(
            MemorySearchQuery(
                query=text,
                limit=limit,
                memory_types=memory_types or [],
            )
        )

    def _score_memory(self, memory: Memory, tokens: set[str], raw_query: str) -> float:
        haystack = " ".join([memory.title, memory.content, " ".join(memory.tags)])
        normalized_text = self._normalize(haystack)
        text_tokens = self._tokenize(haystack)
        overlap = tokens.intersection(text_tokens)
        score = float(len(overlap))
        if normalized_text and self._normalize(raw_query) in normalized_text:
            score += 3.0
        if self._matches_identity_intent(tokens, text_tokens):
            score += 2.0
        return score

    def _matches_identity_intent(self, query_tokens: set[str], text_tokens: set[str]) -> bool:
        if "name" in query_tokens and {"name", "user"}.intersection(text_tokens):
            return True
        if {"role", "developer", "job"}.intersection(query_tokens) and {"role", "developer"}.intersection(
            text_tokens
        ):
            return True
        if "skill" in query_tokens and {"skill", "skills"}.intersection(text_tokens):
            return True
        return False

    def _tokenize(self, value: str) -> set[str]:
        normalized = self._normalize(value)
        return {token for token in normalized.split() if token}

    def _normalize(self, value: str) -> str:
        return re.sub(r"[^a-z0-9+#.\s]", " ", value.lower()).strip()
