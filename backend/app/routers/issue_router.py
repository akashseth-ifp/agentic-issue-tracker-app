from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.database import get_db
from app.services.issue_service import IssueService
from app.schemas.issue import IssueCreate, IssueUpdate, IssueResponse, IssuePage

router = APIRouter(prefix="/api/issues", tags=["issues"])

def get_service(db: AsyncSession = Depends(get_db)) -> IssueService:
    return IssueService(db)

@router.get("/", response_model=IssuePage)
async def list_issues(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    service: IssueService = Depends(get_service),
):
    issues, total = await service.get_all_issues(page=page, page_size=page_size)
    return IssuePage(
        items=issues,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=(total + page_size - 1) // page_size,
    )

@router.get("/{issue_id}", response_model=IssueResponse)
async def get_issue(issue_id: int, service: IssueService = Depends(get_service)):
    return await service.get_issue_or_raise(issue_id)

@router.post("/", response_model=IssueResponse, status_code=status.HTTP_201_CREATED)
async def create_issue(data: IssueCreate, service: IssueService = Depends(get_service)):
    return await service.create_issue(data)

@router.put("/{issue_id}", response_model=IssueResponse)
async def update_issue(
    issue_id: int, data: IssueUpdate, service: IssueService = Depends(get_service)
):
    return await service.update_issue(issue_id, data)

@router.delete("/{issue_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_issue(issue_id: int, service: IssueService = Depends(get_service)):
    await service.delete_issue(issue_id)