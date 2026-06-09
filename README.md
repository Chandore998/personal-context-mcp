# personal-context-mcp

`personal-context-mcp` is a personal memory backend for AI agents. It stores user profile data, work style, reusable memories, and task outcomes, then exposes that context through both FastAPI endpoints and MCP tools.

The goal is simple: give agents a lightweight, structured memory layer they can read before a task and update after a task.

## What this repo includes

- FastAPI service for managing profile, work style, memories, task outcomes, and relevant context
- MCP server built with FastMCP for agent-side context access
- PostgreSQL + `pgvector` storage layer using SQLAlchemy and Alembic
- NiceGUI dashboard for local inspection and manual management
- Retrieval service that returns compressed context instead of raw history

## Current scope

This is an early V1 scaffold focused on the memory backend itself.

What is implemented:

- persistent profile, work style, memory, and task-outcome models
- keyword and metadata-based retrieval
- MCP tool registration
- local HTTP management endpoints
- database migrations and test coverage for the core service flow

What is not implemented yet:

- production-grade authentication or multi-user isolation
- external embedding provider integration
- background jobs, Redis, or async pipelines
- browser or IDE telemetry ingestion

## Architecture

```text
src/personal_context_mcp/
|-- api/           FastAPI routes and app setup
|-- config/        Environment-based settings
|-- db/            SQLAlchemy base and session management
|-- mcp/           FastMCP server and CLI entrypoint
|-- models/        SQLAlchemy entities
|-- repositories/  Persistence layer
|-- schemas/       Pydantic request and response models
|-- services/      Business logic and retrieval
`-- dashboard/     NiceGUI UI
```

## MCP tools

The MCP server exposes these tools:

- `get_user_profile`
- `get_work_style`
- `search_memory`
- `get_relevant_context`
- `save_memory`
- `save_task_outcome`

## Retrieval flow

When a client asks for relevant context, the service:

1. Loads the active user profile.
2. Loads the active work style.
3. Searches matching memories.
4. Searches related task outcomes.
5. Returns a compact `context_summary` plus the structured source records.

This keeps downstream prompts smaller and more deterministic than dumping full chat history.

## Quick start

### Prerequisites

- Python 3.11+
- PostgreSQL 15+
- `pgvector` enabled in the target database

### Install

```powershell
python -m venv venv
venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
```

If you prefer editable installs with dev dependencies:

```powershell
pip install -e .[dev]
```

### Configure

Set at least the database connection in `.env`:

```env
DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5432/personal_context_mcp
PGVECTOR_DIMENSION=1536
MCP_TRANSPORT=stdio
```

### Initialize the database

Create the database, then run migrations:

```powershell
createdb personal_context_mcp
alembic upgrade head
```

The initial migration creates the `vector` extension if needed. If your database user cannot create extensions, install `pgvector` as an administrator first.

## Run locally

### FastAPI

```powershell
uvicorn personal_context_mcp.main:app --reload
```

API docs are available at `http://127.0.0.1:8000/docs` in non-production environments.

### NiceGUI dashboard

```powershell
python -m personal_context_mcp.dashboard
```

### Railway deployment

Deploy the API and NiceGUI dashboard as two Railway services from the same
repository.

API service:

```text
Pre-deploy command: alembic upgrade head
Start command: uvicorn --app-dir src personal_context_mcp.main:app --host 0.0.0.0 --port $PORT
Healthcheck path: /health
```

Dashboard service:

```text
Start command: python -m personal_context_mcp.dashboard
Healthcheck path: /
```

Set `DASHBOARD_HOST=0.0.0.0` and set `DASHBOARD_API_BASE_URL` to the API
service's Railway URL, such as `https://your-api.up.railway.app`. Railway's
injected `PORT` variable is used automatically. Both services should receive
the same application variables, including `DATABASE_URL`.

### FastAPI and NiceGUI together

```powershell
.\start-dev.cmd
```

This starts:

- FastAPI on `http://127.0.0.1:8000`
- NiceGUI on `http://127.0.0.1:8501`

### MCP server

```powershell
python -m personal_context_mcp.mcp
```

## HTTP API

Main endpoints:

- `GET /health`
- `GET /profile`
- `PUT /profile`
- `GET /work-style`
- `PUT /work-style`
- `POST /memories`
- `GET /memories`
- `GET /memories/recent`
- `POST /task-outcomes`
- `GET /task-outcomes`
- `POST /context`

## Configuration

The main environment variables are:

- `APP_NAME`
- `APP_ENV`
- `LOG_LEVEL`
- `DATABASE_URL`
- `DB_POOL_SIZE`
- `DB_MAX_OVERFLOW`
- `DB_POOL_TIMEOUT_SECONDS`
- `DB_POOL_RECYCLE_SECONDS`
- `EMBEDDING_DIMENSIONS`
- `PGVECTOR_DIMENSION`
- `CONTEXT_MEMORY_LIMIT`
- `CONTEXT_TASK_LIMIT`
- `MCP_SERVER_NAME`
- `MCP_TRANSPORT`
- `ADMIN_TOKEN_SECRET`
- `ADMIN_TOKEN_EXPIRE_MINUTES`
- `DASHBOARD_HOST`
- `DASHBOARD_PORT`
- `DASHBOARD_API_BASE_URL`
- `SQL_ECHO`

Set `ADMIN_TOKEN_SECRET` to a long random value in production. Admin login
returns a bearer token that is required by `GET /admin/users` and
`POST /admin/users`. The create-user response includes the generated API key
once; only its hash and prefix are stored afterward.

## Development

Run tests:

```powershell
pytest
```

Run lint checks:

```powershell
ruff check .
ruff format --check .
```

## Design notes

- The storage layer is separated from retrieval logic so ranking can evolve without rewriting the API or MCP surface.
- `pgvector` support is already part of the schema boundary, but V1 retrieval still relies on keyword relevance, importance, and recency.
- The dashboard is meant for local operations and inspection, not as a polished end-user product.

## Limitations

- No embedding provider is wired into the retrieval pipeline yet.
- Ranking is not semantic in practice until embeddings are generated and queried.
- The project is currently geared toward local and single-user usage.

## Roadmap ideas

- Add embedding generation and semantic search
- Support multi-user or workspace-scoped memory
- Add auth for API and MCP access
- Add import/export and backup tooling
- Add agent wrapper examples once the adapter layer is finalized
