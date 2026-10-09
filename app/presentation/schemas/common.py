"""Common Pydantic response envelopes."""

from __future__ import annotations

from typing import Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class SuccessEnvelope(BaseModel, Generic[T]):
    success: bool = True
    data: T | None = None
    message: str = "OK"


class ErrorDetail(BaseModel):
    field: str
    message: str


class ErrorBody(BaseModel):
    code: str
    message: str
    details: list[ErrorDetail] | None = None


class ErrorEnvelope(BaseModel):
    success: bool = False
    error: ErrorBody


class PaginatedData(BaseModel, Generic[T]):
    items: list[T]
    total: int
    offset: int
    limit: int


class PaginatedResponse(BaseModel, Generic[T]):
    success: bool = True
    data: PaginatedData[T]
    message: str = "OK"
