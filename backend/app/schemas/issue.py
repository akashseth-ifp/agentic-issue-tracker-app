from pydantic import BaseModel, Field, field_validator
from datetime import datetime
from app.models.issue import IssueStatus

class IssueBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    description: str | None = Field(None, max_length=2000)
    status: IssueStatus = IssueStatus.OPEN

class IssueCreate(IssueBase):
    @field_validator("title")
    @classmethod
    def title_not_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("title cannot be blank or whitespace only")
        return v.strip()

class IssueUpdate(BaseModel):
    title: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = None
    status: IssueStatus | None = None

class IssueResponse(IssueBase):
    id: int
    created_at: datetime
    model_config = {"from_attributes": True}

class IssuePage(BaseModel):
    items: list[IssueResponse]
    total: int
    page: int
    page_size: int
    total_pages: int