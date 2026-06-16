from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.models.issue import Issue
from app.schemas.issue import IssueCreate, IssueUpdate

class IssueRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_all(self, page: int = 1, page_size: int = 20) -> tuple[list[Issue], int]:
        offset = (page - 1) * page_size

        total = await self.db.scalar(
            select(func.count()).select_from(Issue)
        ) or 0

        result = await self.db.execute(
            select(Issue)
            .order_by(Issue.created_at.desc())
            .offset(offset)
            .limit(page_size)
        )
        return list(result.scalars().all()), total

    async def get_by_id(self, issue_id: int) -> Issue | None:
        result = await self.db.execute(
            select(Issue).where(Issue.id == issue_id)
        )
        return result.scalar_one_or_none()

    async def create(self, data: IssueCreate) -> Issue:
        issue = Issue(**data.model_dump())
        self.db.add(issue)
        await self.db.commit()
        await self.db.refresh(issue)
        return issue

    async def update(self, issue: Issue, data: IssueUpdate) -> Issue:
        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(issue, field, value)
        await self.db.commit()
        await self.db.refresh(issue)
        return issue

    async def delete(self, issue: Issue) -> None:
        await self.db.delete(issue)
        await self.db.commit()