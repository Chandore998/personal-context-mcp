from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from personal_context_mcp.api.routes import api_router
from personal_context_mcp.auth.api_key import current_user_id_var
from personal_context_mcp.config.settings import get_settings
from personal_context_mcp.mcp.server import build_personal_context_mcp_server
from personal_context_mcp.services.dependencies import get_auth_service

# Paths that never require authentication.
_PUBLIC_PATHS = {"/health"}


def create_app() -> FastAPI:
    settings = get_settings()

    mcp_server = build_personal_context_mcp_server()
    fastmcp = mcp_server.create_fastmcp_server(streamable_http_path="/")
    mcp_app = fastmcp.streamable_http_app()

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        async with fastmcp.session_manager.run():
            yield

    app = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        docs_url="/docs" if settings.app_env != "production" else None,
        redoc_url="/redoc" if settings.app_env != "production" else None,
        lifespan=lifespan,
    )

    # Overridable in tests via app.state.auth_service_factory = lambda: MockAuthService(...)
    app.state.auth_service_factory = get_auth_service

    @app.middleware("http")
    async def auth_middleware(request: Request, call_next):
        if request.url.path in _PUBLIC_PATHS:
            return await call_next(request)

        auth_service = request.app.state.auth_service_factory()

        # Auth is disabled when no users exist in the DB.
        if not auth_service.has_any_users():
            current_user_id_var.set("default")
            return await call_next(request)

        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return JSONResponse(
                {"detail": "Missing or invalid Authorization header"},
                status_code=401,
            )

        raw_key = auth_header[7:]
        user = auth_service.validate_key(raw_key)
        if user is None:
            return JSONResponse({"detail": "Invalid or expired API key"}, status_code=401)

        ip = request.client.host if request.client else None
        auth_service.record_session(user.id, ip_address=ip)

        current_user_id_var.set(user.id)
        return await call_next(request)

    app.include_router(api_router)

    # Mount a hosted MCP endpoint for remote agent connections.
    app.mount("/mcp", mcp_app)

    return app


app = create_app()
