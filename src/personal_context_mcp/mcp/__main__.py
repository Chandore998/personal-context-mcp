from personal_context_mcp.services.dependencies import (
    get_memory_service,
    get_profile_service,
    get_retrieval_service,
    get_task_outcome_service,
    get_work_style_service,
)

from .server import PersonalContextMCPServer


def main() -> None:
    server = PersonalContextMCPServer(
        profile_service=get_profile_service(),
        work_style_service=get_work_style_service(),
        memory_service=get_memory_service(),
        retrieval_service=get_retrieval_service(),
        task_outcome_service=get_task_outcome_service(),
    )
    mcp_server = server.create_fastmcp_server()
    mcp_server.run(transport="stdio")


if __name__ == "__main__":
    main()
