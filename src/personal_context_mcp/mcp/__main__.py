import os

from personal_context_mcp.auth.api_key import current_user_id_var
from personal_context_mcp.config.settings import get_settings
from personal_context_mcp.services.dependencies import get_auth_service

from .server import build_personal_context_mcp_server


def main() -> None:
    settings = get_settings()
    auth_service = get_auth_service()

    try:
        if auth_service.has_any_users():
            raw_key = os.environ.get("MCP_API_KEY", "").strip()
            if not raw_key:
                raise SystemExit("Error: MCP_API_KEY environment variable is required")

            user = auth_service.validate_key(raw_key)
            if user is None:
                raise SystemExit(
                    "Error: MCP_API_KEY is invalid or the account is inactive/expired"
                )

            auth_service.record_session(user.id)
            current_user_id_var.set(user.id)
        else:
            # No users in DB - auth disabled, use default partition.
            current_user_id_var.set("default")
    finally:
        auth_service.close()

    server = build_personal_context_mcp_server()
    mcp_server = server.create_fastmcp_server()
    mcp_server.run(transport=settings.mcp_transport)


if __name__ == "__main__":
    main()
