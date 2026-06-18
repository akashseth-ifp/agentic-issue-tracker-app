from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.database import get_db
from app.schemas.assistant import AssistantRequest, AssistantResponse
from app.agent.assistant_service import run_agent

router = APIRouter(prefix="/api/assistant", tags=["assistant"])


@router.post("/run", response_model=AssistantResponse)
async def run_assistant(body: AssistantRequest, db: AsyncSession = Depends(get_db)):
    try:
        result = await run_agent(body.instruction, db, cursor=body.cursor)
        return AssistantResponse(**result)
    except Exception:
        raise HTTPException(status_code=502, detail="Assistant service unavailable. Please try again.")
