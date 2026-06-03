from contextlib import asynccontextmanager

from fastapi import FastAPI

from personal_context_mcp.api.routes import api_router
from personal_context_mcp.config.settings import get_settings
from personal_context_mcp.mcp.server import build_personal_context_mcp_server


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
    app.include_router(api_router)

    # Mount a hosted MCP endpoint for remote agent connections.
    app.mount("/mcp", mcp_app)

    return app


app = create_app()
