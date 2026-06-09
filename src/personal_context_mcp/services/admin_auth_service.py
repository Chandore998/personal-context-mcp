import base64
import hashlib
import hmac
import json
import secrets
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from personal_context_mcp.models.admin import Admin
from personal_context_mcp.repositories.admin_repository import AdminRepository

_SCRYPT_N = 2**14
_SCRYPT_R = 8
_SCRYPT_P = 1
_SALT_BYTES = 16
_KEY_BYTES = 64


class AdminAlreadyExistsError(ValueError):
    pass


class InvalidAdminCredentialsError(ValueError):
    pass


class InvalidAdminTokenError(ValueError):
    pass


def _encode_base64url(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


def _decode_base64url(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(_SALT_BYTES)
    derived_key = hashlib.scrypt(
        password.encode("utf-8"),
        salt=salt,
        n=_SCRYPT_N,
        r=_SCRYPT_R,
        p=_SCRYPT_P,
        dklen=_KEY_BYTES,
    )
    encoded_salt = base64.urlsafe_b64encode(salt).decode("ascii")
    encoded_key = base64.urlsafe_b64encode(derived_key).decode("ascii")
    return f"scrypt${_SCRYPT_N}${_SCRYPT_R}${_SCRYPT_P}${encoded_salt}${encoded_key}"


def verify_password(password: str, password_hash: str) -> bool:
    try:
        algorithm, n, r, p, encoded_salt, encoded_key = password_hash.split("$", 5)
        if algorithm != "scrypt":
            return False
        salt = base64.urlsafe_b64decode(encoded_salt.encode("ascii"))
        expected_key = base64.urlsafe_b64decode(encoded_key.encode("ascii"))
        actual_key = hashlib.scrypt(
            password.encode("utf-8"),
            salt=salt,
            n=int(n),
            r=int(r),
            p=int(p),
            dklen=len(expected_key),
        )
    except (TypeError, ValueError):
        return False
    return hmac.compare_digest(actual_key, expected_key)


class AdminAuthService:
    def __init__(
        self,
        repository: AdminRepository,
        *,
        token_secret: str,
        token_expire_minutes: int,
    ) -> None:
        self.repository = repository
        self.token_secret = token_secret
        self.token_expire_minutes = token_expire_minutes

    def signup(self, email: str, password: str) -> Admin:
        normalized_email = email.strip().lower()
        if self.repository.get_by_email(normalized_email) is not None:
            raise AdminAlreadyExistsError("An admin with this email already exists.")

        is_first_admin = self.repository.count() == 0
        return self.repository.create(
            Admin(
                id=str(uuid4()),
                email=normalized_email,
                password_hash=hash_password(password),
                status="active",
                is_super_admin=is_first_admin,
            )
        )

    def login(self, email: str, password: str) -> Admin:
        admin = self.repository.get_by_email(email.strip().lower())
        if (
            admin is None
            or admin.status != "active"
            or admin.deleted_at is not None
            or not verify_password(password, admin.password_hash)
        ):
            raise InvalidAdminCredentialsError("Invalid email or password.")
        return admin

    def create_access_token(self, admin: Admin) -> tuple[str, datetime]:
        now = datetime.now(UTC)
        expires_at = now + timedelta(minutes=self.token_expire_minutes)
        header = {"alg": "HS256", "typ": "JWT"}
        payload = {
            "sub": admin.id,
            "iat": int(now.timestamp()),
            "exp": int(expires_at.timestamp()),
        }
        encoded_header = _encode_base64url(
            json.dumps(header, separators=(",", ":"), sort_keys=True).encode()
        )
        encoded_payload = _encode_base64url(
            json.dumps(payload, separators=(",", ":"), sort_keys=True).encode()
        )
        signing_input = f"{encoded_header}.{encoded_payload}"
        signature = hmac.new(
            self.token_secret.encode(),
            signing_input.encode(),
            hashlib.sha256,
        ).digest()
        return f"{signing_input}.{_encode_base64url(signature)}", expires_at

    def authenticate_token(self, token: str) -> Admin:
        try:
            encoded_header, encoded_payload, encoded_signature = token.split(".", 2)
            signing_input = f"{encoded_header}.{encoded_payload}"
            expected_signature = hmac.new(
                self.token_secret.encode(),
                signing_input.encode(),
                hashlib.sha256,
            ).digest()
            supplied_signature = _decode_base64url(encoded_signature)
            if not hmac.compare_digest(expected_signature, supplied_signature):
                raise InvalidAdminTokenError("Invalid admin token.")

            header = json.loads(_decode_base64url(encoded_header))
            payload = json.loads(_decode_base64url(encoded_payload))
            if header.get("alg") != "HS256":
                raise InvalidAdminTokenError("Invalid admin token.")
            if int(payload["exp"]) <= int(datetime.now(UTC).timestamp()):
                raise InvalidAdminTokenError("Admin token has expired.")
            admin_id = str(payload["sub"])
        except InvalidAdminTokenError:
            raise
        except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
            raise InvalidAdminTokenError("Invalid admin token.") from exc

        admin = self.repository.get_by_id(admin_id)
        if admin is None or admin.status != "active" or admin.deleted_at is not None:
            raise InvalidAdminTokenError("Invalid admin token.")
        return admin
