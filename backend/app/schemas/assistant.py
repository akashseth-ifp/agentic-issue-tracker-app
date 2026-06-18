from pydantic import BaseModel, field_validator


class AssistantRequest(BaseModel):
    instruction: str
    cursor: str | None = None

    @field_validator("instruction")
    @classmethod
    def not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Instruction cannot be empty")
        return v.strip()


class AssistantResponse(BaseModel):
    response: str
    mutations_made: bool
    next_cursor: str | None = None
