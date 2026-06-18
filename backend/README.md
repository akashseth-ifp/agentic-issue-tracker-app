# Backend — FastAPI Issue Tracker

REST API for the Issue Tracking System. Built with FastAPI, SQLAlchemy 2.0 (async), and SQLite.

## Setup

```bash
cd backend

# Create and activate virtual environment
uv venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate

# Install dependencies
uv sync

# Create .env file
cp .env.example .env        # or create manually (see Configuration below)

# Run the development server
uvicorn app.main:app --reload --port 8000
```

- Swagger UI: `http://localhost:8000/docs`
- OpenAPI JSON: `http://localhost:8000/openapi.json`

## Configuration

Create a `.env` file in the `backend/` directory:

```
DATABASE_URL=sqlite+aiosqlite:///./issues.db
CORS_ORIGINS=["http://localhost:4200"]
OPENAI_API_KEY=sk-...
```

Note the `sqlite+aiosqlite:///` prefix — this activates the async SQLite driver. `OPENAI_API_KEY` is required for the AI Assistant endpoint; the rest of the app works without it.

## Project Structure

```
backend/
├── app/
│   ├── main.py              — App entry point: middleware, routers, lifespan
│   ├── core/
│   │   ├── config.py        — Typed settings loaded from .env (incl. OPENAI_API_KEY)
│   │   └── exceptions.py    — Custom exception hierarchy + FastAPI handlers
│   ├── db/
│   │   └── database.py      — Async engine, session factory, get_db dependency
│   ├── models/
│   │   └── issue.py         — SQLAlchemy ORM model (Issue table)
│   ├── schemas/
│   │   ├── issue.py         — Pydantic schemas: IssueCreate, IssueUpdate, IssueResponse, IssuePage
│   │   └── assistant.py     — AssistantRequest, AssistantResponse schemas
│   ├── repositories/
│   │   └── issue_repository.py  — All SQL queries; includes cursor-based pagination,
│   │                              count(), and bulk_update_status() for agent use
│   ├── services/
│   │   └── issue_service.py     — Business rules (status transitions, raises semantic errors)
│   ├── agent/
│   │   ├── tools.py             — 5 OpenAI tool schemas + execute_tool() dispatcher
│   │   └── assistant_service.py — run_agent(): agentic loop (MAX_ITERATIONS=10)
│   └── routers/
│       ├── issue_router.py      — HTTP routes for issues (calls service, returns schemas)
│       └── assistant_router.py  — POST /api/assistant/run
├── alembic/                 — Migration scripts (incl. ix_issues_created_at index)
├── alembic.ini
├── pyproject.toml
└── .env
```

## API Reference

### Issues

| Method | Path | Query params | Request body | Response |
|---|---|---|---|---|
| GET | `/api/issues` | `page=1`, `page_size=20` | — | `IssuePage` |
| GET | `/api/issues/{id}` | — | — | `IssueResponse` |
| POST | `/api/issues` | — | `IssueCreate` | `IssueResponse` (201) |
| PUT | `/api/issues/{id}` | — | `IssueUpdate` | `IssueResponse` |
| DELETE | `/api/issues/{id}` | — | — | 204 No Content |

### AI Assistant

| Method | Path | Request body | Response |
|---|---|---|---|
| POST | `/api/assistant/run` | `AssistantRequest` | `AssistantResponse` |

**`AssistantRequest`:**
```json
{ "instruction": "Close all in-progress issues", "cursor": null }
```

**`AssistantResponse`:**
```json
{
  "response": "Done! Moved 3 in-progress issues to Closed.",
  "mutations_made": true,
  "next_cursor": null
}
```

- `mutations_made: true` tells the frontend to refresh the issue list.
- `next_cursor` is a base64 pagination cursor; send it back in the next request to fetch the next page of a previous `list_issues` result.
- Returns `502` if the OpenAI API is unreachable.

All error responses: `{"error": "<message>", "status_code": <code>}`

## Status Transitions

```
Open → In Progress → Closed
         ↑
         └── (can revert back to Open)
```

`Closed` is a terminal state — no further transitions allowed.

## Database Migrations

```bash
# After changing a model
alembic revision --autogenerate -m "describe the change"
alembic upgrade head

# Roll back one step
alembic downgrade -1
```

## Dependencies

| Package | Purpose |
|---|---|
| `fastapi` | Web framework |
| `uvicorn[standard]` | ASGI server |
| `sqlalchemy` | ORM + async session |
| `aiosqlite` | Async SQLite driver |
| `alembic` | Database migrations |
| `pydantic-settings` | Typed settings from `.env` |
| `openai>=1.0` | OpenAI SDK — native function calling for the AI Assistant |
