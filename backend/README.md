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
```

Note the `sqlite+aiosqlite:///` prefix — this activates the async SQLite driver.

## Project Structure

```
backend/
├── app/
│   ├── main.py              — App entry point: middleware, routers, lifespan
│   ├── core/
│   │   ├── config.py        — Typed settings loaded from .env
│   │   └── exceptions.py    — Custom exception hierarchy + FastAPI handlers
│   ├── db/
│   │   └── database.py      — Async engine, session factory, get_db dependency
│   ├── models/
│   │   └── issue.py         — SQLAlchemy ORM model (Issue table)
│   ├── schemas/
│   │   └── issue.py         — Pydantic schemas: IssueCreate, IssueUpdate, IssueResponse, IssuePage
│   ├── repositories/
│   │   └── issue_repository.py  — All SQL queries (no business logic)
│   ├── services/
│   │   └── issue_service.py     — Business rules (status transitions, raises semantic errors)
│   └── routers/
│       └── issue_router.py      — HTTP routes (calls service, returns schemas)
├── alembic/                 — Migration scripts
├── alembic.ini
├── pyproject.toml
└── .env
```

## API Reference

| Method | Path | Query params | Request body | Response |
|---|---|---|---|---|
| GET | `/api/issues` | `page=1`, `page_size=20` | — | `IssuePage` |
| GET | `/api/issues/{id}` | — | — | `IssueResponse` |
| POST | `/api/issues` | — | `IssueCreate` | `IssueResponse` (201) |
| PUT | `/api/issues/{id}` | — | `IssueUpdate` | `IssueResponse` |
| DELETE | `/api/issues/{id}` | — | — | 204 No Content |

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
