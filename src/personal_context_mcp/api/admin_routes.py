from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status

from personal_context_mcp.models.admin import Admin
from personal_context_mcp.schemas.admin import AdminAuthResponse, AdminLogin, AdminSignup
from personal_context_mcp.schemas.user_auth import UserCreate, UserKeyResponse, UserRead
from personal_context_mcp.services.admin_auth_service import (
    AdminAlreadyExistsError,
    AdminAuthService,
    InvalidAdminCredentialsError,
)
from personal_context_mcp.services.auth_service import (
    AuthService,
    UserAlreadyExistsError,
    UserNotFoundError,
)
from personal_context_mcp.services.dependencies import (
    get_admin_auth_service,
    get_current_admin,
    get_user_auth_service,
)

admin_router = APIRouter(prefix="/admin", tags=["admin"])


@admin_router.post(
    "/signup",
    response_model=AdminAuthResponse,
    status_code=status.HTTP_201_CREATED,
)
def admin_signup(
    payload: AdminSignup,
    service: Annotated[AdminAuthService, Depends(get_admin_auth_service)],
) -> AdminAuthResponse:
    try:
        admin = service.signup(payload.email, payload.password)
    except AdminAlreadyExistsError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    return AdminAuthResponse(message="Admin created successfully.", admin=admin)


@admin_router.post("/login", response_model=AdminAuthResponse)
def admin_login(
    payload: AdminLogin,
    service: Annotated[AdminAuthService, Depends(get_admin_auth_service)],
) -> AdminAuthResponse:
    try:
        admin = service.login(payload.email, payload.password)
    except InvalidAdminCredentialsError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc
    access_token, expires_at = service.create_access_token(admin)
    return AdminAuthResponse(
        message="Login successful.",
        admin=admin,
        access_token=access_token,
        token_type="bearer",
        expires_at=expires_at,
    )


@admin_router.get("/users", response_model=list[UserRead])
def list_users(
    _: Annotated[Admin, Depends(get_current_admin)],
    service: Annotated[AuthService, Depends(get_user_auth_service)],
) -> list[dict]:
    return service.list_users_with_sessions()


@admin_router.post(
    "/users",
    response_model=UserKeyResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_user(
    payload: UserCreate,
    _: Annotated[Admin, Depends(get_current_admin)],
    service: Annotated[AuthService, Depends(get_user_auth_service)],
) -> UserKeyResponse:
    try:
        user, raw_key = service.create_user(payload.email, expires_at=payload.expires_at)
    except UserAlreadyExistsError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    return UserKeyResponse(
        message="User created. Store the API key now; it will not be shown again.",
        user=UserRead.model_validate(user, from_attributes=True),
        api_key=raw_key,
    )


@admin_router.post("/users/{user_id}/key", response_model=UserKeyResponse)
def regenerate_user_key(
    user_id: str,
    _: Annotated[Admin, Depends(get_current_admin)],
    service: Annotated[AuthService, Depends(get_user_auth_service)],
) -> UserKeyResponse:
    try:
        user, raw_key = service.regenerate_user_key(user_id)
    except UserNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return UserKeyResponse(
        message="API key regenerated. The previous key is no longer valid.",
        user=UserRead.model_validate(user, from_attributes=True),
        api_key=raw_key,
    )


@admin_router.patch("/users/{user_id}/deactivate", response_model=UserRead)
def deactivate_user(
    user_id: str,
    _: Annotated[Admin, Depends(get_current_admin)],
    service: Annotated[AuthService, Depends(get_user_auth_service)],
) -> UserRead:
    try:
        user = service.deactivate_user(user_id)
    except UserNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return UserRead.model_validate(user, from_attributes=True)


@admin_router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(
    user_id: str,
    _: Annotated[Admin, Depends(get_current_admin)],
    service: Annotated[AuthService, Depends(get_user_auth_service)],
) -> Response:
    try:
        service.delete_user_by_id(user_id)
    except UserNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)
