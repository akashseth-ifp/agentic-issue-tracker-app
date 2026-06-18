import base64
import json
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, update as sa_update
from app.models.issue import Issue, IssueStatus
from app.schemas.issue import IssueCreate, IssueUpdate


def encode_cursor(created_at: datetime, id: int) -> str:
    payload = json.dumps({"ts": created_at.isoformat(), "id": id})
    return base64.urlsafe_b64encode(payload.encode()).decode()


def decode_cursor(cursor: str) -> tuple[datetime, int]:
    payload = json.loads(base64.urlsafe_b64decode(cursor))
    return datetime.fromisoformat(payload["ts"]), payload["id"]

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

    async def get_cursor_page(
        self,
        page_size: int = 20,
        cursor: str | None = None,
        issue_id: int | None = None,
        status: IssueStatus | None = None,
        created_after: datetime | None = None,
        created_before: datetime | None = None,
    ) -> tuple[list[Issue], bool, str | None]:
        query = select(Issue)
        if cursor:
            ts, cid = decode_cursor(cursor)
            query = query.where(
                (Issue.created_at < ts) |
                ((Issue.created_at == ts) & (Issue.id < cid))
            )
        if issue_id is not None:
            query = query.where(Issue.id == issue_id)
        if status:
            query = query.where(Issue.status == status)
        if created_after:
            query = query.where(Issue.created_at >= created_after)
        if created_before:
            query = query.where(Issue.created_at <= created_before)

        rows = list((await self.db.execute(
            query.order_by(Issue.created_at.desc(), Issue.id.desc()).limit(page_size + 1)
        )).scalars().all())

        has_more = len(rows) > page_size
        items = rows[:page_size]
        next_cursor = encode_cursor(items[-1].created_at, items[-1].id) if has_more and items else None
        return items, has_more, next_cursor

    async def count(
        self,
        status: IssueStatus | None = None,
        created_after: datetime | None = None,
        created_before: datetime | None = None,
    ) -> int:
        query = select(func.count()).select_from(Issue)
        if status:
            query = query.where(Issue.status == status)
        if created_after:
            query = query.where(Issue.created_at >= created_after)
        if created_before:
            query = query.where(Issue.created_at <= created_before)
        return await self.db.scalar(query) or 0

    async def bulk_update_status(self, from_status: IssueStatus, to_status: IssueStatus) -> int:
        result = await self.db.execute(
            sa_update(Issue)
            .where(Issue.status == from_status)
            .values(status=to_status)
        )
        await self.db.commit()
        return result.rowcount