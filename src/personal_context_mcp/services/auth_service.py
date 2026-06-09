import hashlib
import secrets
from datetime import UTC, datetime
from uuid import uuid4

from personal_context_mcp.models.user_auth import UserAuth
from personal_context_mcp.repositories.user_auth_repository import UserAuthRepository
from personal_context_mcp.repositories.user_session_repository import UserSessionRepository


class UserAlreadyExistsError(ValueError):
    pass


class UserNotFoundError(ValueError):
    pass


def generate_secret_key() -> str:
    return "sk_" + secrets.token_hex(24)


def hash_key(raw_key: str) -> str:
    return hashlib.sha256(raw_key.encode()).hexdigest()


class AuthService:
    def __init__(
        self,
        user_repo: UserAuthRepository,
        session_repo: UserSessionRepository,
    ) -> None:
        self.user_repo = user_repo
        self.session_repo = session_repo

    def close(self) -> None:
        self.user_repo.session.close()

    def has_any_users(self) -> bool:
        return self.user_repo.count() > 0

    def create_user(
        self,
        email: str,
        expires_at: datetime | None = None,
    ) -> tuple[UserAuth, str]:
        """Create a user and return (user, raw_secret_key). The raw key is shown once — store it."""
        normalized_email = email.strip().lower()
        if self.user_repo.get_by_email(normalized_email) is not None:
            raise UserAlreadyExistsError("A user with this email already exists.")

        raw_key = generate_secret_key()
        user = UserAuth(
            id=str(uuid4()),
            email=normalized_email,
            key_hash=hash_key(raw_key),
            key_prefix=raw_key[:12],
            is_active=True,
            expires_at=expires_at,
        )
        self.user_repo.create(user)
        return user, raw_key

    def validate_key(self, raw_key: str) -> UserAuth | None:
        """Return the user if key is valid, active, and not expired — else None."""
        user = self.user_repo.get_by_key_hash(hash_key(raw_key))
        if user is None or not user.is_active:
            return None
        if user.expires_at and user.expires_at < datetime.now(UTC):
            return None
        return user

    def record_session(self, user_id: str, ip_address: str | None = None) -> None:
        self.session_repo.upsert(user_id, ip_address=ip_address)

    def regenerate_key(self, user: UserAuth) -> tuple[UserAuth, str]:
        """Replace the user's key. Old key is immediately invalid. Returns (user, new_raw_key)."""
        raw_key = generate_secret_key()
        user.key_hash = hash_key(raw_key)
        user.key_prefix = raw_key[:12]
        self.user_repo.save(user)
        return user, raw_key

    def regenerate_user_key(self, user_id: str) -> tuple[UserAuth, str]:
        return self.regenerate_key(self.get_user(user_id))

    def set_active(self, user: UserAuth, *, active: bool) -> UserAuth:
        user.is_active = active
        return self.user_repo.save(user)

    def deactivate_user(self, user_id: str) -> UserAuth:
        return self.set_active(self.get_user(user_id), active=False)

    def delete_user(self, user: UserAuth) -> None:
        self.user_repo.delete(user)

    def delete_user_by_id(self, user_id: str) -> None:
        self.delete_user(self.get_user(user_id))

    def get_user(self, user_id: str) -> UserAuth:
        user = self.user_repo.get_by_id(user_id)
        if user is None:
            raise UserNotFoundError("User not found.")
        return user

    def list_users_with_sessions(self) -> list[dict]:
        users = self.user_repo.list_all()
        sessions = {s.user_id: s for s in self.session_repo.list_all()}
        return [
            {
                "id": u.id,
                "email": u.email,
                "key_prefix": u.key_prefix,
                "is_active": u.is_active,
                "expires_at": u.expires_at,
                "created_at": u.created_at,
                "last_seen_at": sessions[u.id].last_seen_at if u.id in sessions else None,
                "ip_address": sessions[u.id].ip_address if u.id in sessions else None,
            }
            for u in users
        ]
