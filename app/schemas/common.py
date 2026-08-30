from typing import Generic, Sequence, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class Pagination(BaseModel):
    limit: int = Field(50, ge=1, le=500)
    offset: int = Field(0, ge=0)


class Page(BaseModel, Generic[T]):
    items: Sequence[T]
    total: int
    limit: int
    offset: int

    @property
    def has_more(self) -> bool:
        return self.offset + len(self.items) < self.total

    @classmethod
    def build(cls, items: Sequence[T], total: int, limit: int, offset: int) -> "Page[T]":
        return cls(items=items, total=total, limit=limit, offset=offset)


class ErrorResponse(BaseModel):
    detail: str
    code: str | None = None


class MessageResponse(BaseModel):
    message: str
