from contextvars import ContextVar

# Holds the authenticated user's UUID for the duration of a request / stdio process.
# Set by the HTTP auth middleware or by mcp/__main__.py at startup.
# MCP tool handlers and FastAPI service deps read it via get_current_user_id().
current_user_id_var: ContextVar[str | None] = ContextVar("current_user_id", default=None)
