from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.core.exceptions import AppException, app_exception_handler
from app.db.database import engine, Base
from app.routers.issue_router import router as issue_router
from app.routers.assistant_router import router as assistant_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Dev convenience — Alembic handles this in production
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    await engine.dispose()

app = FastAPI(title="Issue Tracker API", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_exception_handler(AppException, app_exception_handler)
app.include_router(issue_router)
app.include_router(assistant_router)