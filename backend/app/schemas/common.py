from __future__ import annotations

from typing import Generic, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class PaginatedResponse(BaseModel, Generic[T]):
    items: list[T]
    total: int
    page: int
    page_size: int
    pages: int


class ErrorResponse(BaseModel):
    detail: str


class MessageResponse(BaseModel):
    message: str


class FilterOptions(BaseModel):
    stores: list[dict[str, str]]
    categories: list[dict[str, str]]
    horizons: list[int] = Field(default_factory=lambda: [7, 14])