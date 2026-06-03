from fastapi import FastAPI

from personal_context_mcp.api.routes import api_router
from personal_context_mcp.config.settings import get_settings


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        docs_url="/docs" if settings.app_env != "production" else None,
        redoc_url="/redoc" if settings.app_env != "production" else None,
    )
    app.include_router(api_router)
    return app


app = create_app()
