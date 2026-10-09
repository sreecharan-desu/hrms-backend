"""Document Pydantic schemas."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

ALLOWED_EXTENSIONS = frozenset({"pdf", "png", "jpg", "jpeg", "docx"})
MAX_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB

EXTENSION_CONTENT_TYPES: dict[str, str] = {
    "pdf": "application/pdf",
    "png": "image/png",
    "jpg": "image/jpeg",
    "jpeg": "image/jpeg",
    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}


class UploadDocumentRequest(BaseModel):
    filename: str = Field(..., min_length=1, max_length=255)
    size_bytes: int = Field(..., gt=0)
    employee_id: str | None = None
    content_type: str = Field(..., min_length=1, max_length=100)


class ConfirmDocumentResponse(BaseModel):
    id: str
    status: str
    size_bytes: int


class DocumentOut(BaseModel):
    id: str
    filename: str
    content_type: str
    size_bytes: int
    status: str
    employee_id: str | None = None
    uploaded_by: str | None = None
    storage_key: str
    created_at: datetime | None = None
    updated_at: datetime | None = None


class DocumentWithUrlOut(DocumentOut):
    download_url: str | None = None


class UploadDocumentResponse(BaseModel):
    document_id: str
    upload_url: str
    upload_headers: dict[str, str]
