from personal_context_mcp.config.settings import get_settings

from .server import build_personal_context_mcp_server


def main() -> None:
    settings = get_settings()
    server = build_personal_context_mcp_server()
    mcp_server = server.create_fastmcp_server()
    mcp_server.run(transport=settings.mcp_transport)


if __name__ == "__main__":
    main()
