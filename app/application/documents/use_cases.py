"""Document use cases – presigned upload flow."""

from __future__ import annotations

from dataclasses import dataclass

import structlog

from app.application.common.audit import write_audit
from app.core.dependencies import CurrentUser, RequestContext
from app.core.exceptions import NotFoundError, ValidationAppError
from app.domain.documents.enums import DocumentStatus
from app.infrastructure.database.models.document import Document
from app.infrastructure.database.uow import SqlAlchemyUnitOfWork
from app.infrastructure.storage.s3 import (
    generate_presigned_get,
    generate_presigned_put,
    generate_storage_key,
    head_object,
)
from app.presentation.schemas.documents import (
    ALLOWED_EXTENSIONS,
    MAX_SIZE_BYTES,
)

logger = structlog.stdlib.get_logger(__name__)


def validate_document_input(filename: str, size_bytes: int) -> str:
    """Validate filename extension and size. Returns the extension."""
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if ext not in ALLOWED_EXTENSIONS:
        raise ValidationAppError(
            f"File extension '{ext}' not allowed. "
            f"Allowed: {', '.join(sorted(ALLOWED_EXTENSIONS))}"
        )
    if size_bytes > MAX_SIZE_BYTES:
        raise ValidationAppError(
            f"File size {size_bytes} exceeds maximum of {MAX_SIZE_BYTES} bytes."
        )
    return ext


@dataclass(frozen=True, slots=True)
class UploadResult:
    document_id: str
    upload_url: str
    upload_headers: dict[str, str]


async def initiate_upload(
    *,
    filename: str,
    size_bytes: int,
    content_type: str,
    employee_id: str | None,
    actor: CurrentUser,
    uow: SqlAlchemyUnitOfWork,
    ctx: RequestContext | None = None,
) -> UploadResult:
    """Create a PENDING document and return a presigned PUT URL."""
    validate_document_input(filename, size_bytes)

    storage_key = generate_storage_key(filename)
    presigned = generate_presigned_put(storage_key, content_type, size_bytes)

    doc = Document(
        storage_key=presigned.storage_key,
        filename=filename,
        content_type=content_type,
        size_bytes=size_bytes,
        employee_id=employee_id,
        uploaded_by=actor.id,
        status=DocumentStatus.PENDING,
    )
    uow.session.add(doc)
    await uow.session.flush()

    await write_audit(
        uow,
        actor_id=actor.id,
        action="document.upload_initiated",
        entity_type="document",
        entity_id=doc.id,
        new={"filename": filename, "size_bytes": size_bytes},
        request_context=ctx,
    )
    await uow.commit()

    return UploadResult(
        document_id=doc.id,
        upload_url=presigned.url,
        upload_headers=presigned.headers,
    )


async def confirm_upload(
    document_id: str,
    *,
    actor: CurrentUser,
    uow: SqlAlchemyUnitOfWork,
    ctx: RequestContext | None = None,
) -> Document:
    """HEAD the object in S3, verify it exists, mark document AVAILABLE."""
    from sqlalchemy import select

    stmt = select(Document).where(Document.id == document_id)
    result = await uow.session.execute(stmt)
    doc = result.scalars().first()
    if doc is None:
        raise NotFoundError("Document not found.")
    if doc.status != DocumentStatus.PENDING:
        raise ValidationAppError("Document is not in PENDING status.")

    # Ownership / permission check
    if doc.uploaded_by != actor.id and "document.upload" not in actor.permissions:
        from app.core.exceptions import ForbiddenError

        raise ForbiddenError("You do not own this document.")

    try:
        obj_info = head_object(doc.storage_key)
        actual_size = obj_info.get("ContentLength", 0)
        if actual_size and abs(actual_size - doc.size_bytes) > 1024:
            await logger.awarning(
                "document_size_mismatch",
                expected=doc.size_bytes,
                actual=actual_size,
            )
    except Exception as exc:
        raise ValidationAppError(
            "Object not found in storage. Upload may have failed."
        ) from exc

    doc.status = DocumentStatus.AVAILABLE
    if actual_size:
        doc.size_bytes = actual_size

    await write_audit(
        uow,
        actor_id=actor.id,
        action="document.confirmed",
        entity_type="document",
        entity_id=doc.id,
        request_context=ctx,
    )
    await uow.commit()
    return doc


@dataclass(frozen=True, slots=True)
class PaginatedDocuments:
    items: list[dict]
    total: int
    offset: int
    limit: int


async def list_documents(
    uow: SqlAlchemyUnitOfWork,
    *,
    offset: int = 0,
    limit: int = 50,
    employee_id: str | None = None,
) -> PaginatedDocuments:
    """List documents with pagination."""
    from sqlalchemy import func, select

    base = select(Document).where(Document.status != DocumentStatus.DELETED)
    count_base = select(func.count(Document.id)).where(
        Document.status != DocumentStatus.DELETED
    )

    if employee_id:
        base = base.where(Document.employee_id == employee_id)
        count_base = count_base.where(Document.employee_id == employee_id)

    total = (await uow.session.execute(count_base)).scalar_one()
    rows = (
        await uow.session.execute(
            base.order_by(Document.created_at.desc()).offset(offset).limit(limit)
        )
    ).scalars().all()

    items = [
        {
            "id": r.id,
            "filename": r.filename,
            "content_type": r.content_type,
            "size_bytes": r.size_bytes,
            "status": r.status,
            "employee_id": r.employee_id,
            "uploaded_by": r.uploaded_by,
            "storage_key": r.storage_key,
            "created_at": r.created_at.isoformat() if r.created_at else None,
            "updated_at": r.updated_at.isoformat() if r.updated_at else None,
        }
        for r in rows
    ]
    return PaginatedDocuments(items=items, total=total, offset=offset, limit=limit)


async def get_document(
    document_id: str,
    uow: SqlAlchemyUnitOfWork,
) -> dict:
    """Get document metadata + short-lived signed GET URL."""
    from sqlalchemy import select

    stmt = select(Document).where(
        Document.id == document_id,
        Document.status != DocumentStatus.DELETED,
    )
    result = await uow.session.execute(stmt)
    doc = result.scalars().first()
    if doc is None:
        raise NotFoundError("Document not found.")

    download_url = None
    if doc.status == DocumentStatus.AVAILABLE:
        try:
            download_url = generate_presigned_get(doc.storage_key)
        except Exception:
            await logger.awarning("presigned_get_failed", doc_id=doc.id)

    return {
        "id": doc.id,
        "filename": doc.filename,
        "content_type": doc.content_type,
        "size_bytes": doc.size_bytes,
        "status": doc.status,
        "employee_id": doc.employee_id,
        "uploaded_by": doc.uploaded_by,
        "storage_key": doc.storage_key,
        "download_url": download_url,
        "created_at": doc.created_at.isoformat() if doc.created_at else None,
        "updated_at": doc.updated_at.isoformat() if doc.updated_at else None,
    }


async def delete_document(
    document_id: str,
    *,
    actor: CurrentUser,
    uow: SqlAlchemyUnitOfWork,
    ctx: RequestContext | None = None,
) -> None:
    """Soft-delete a document (mark DELETED)."""
    from sqlalchemy import select

    stmt = select(Document).where(
        Document.id == document_id,
        Document.status != DocumentStatus.DELETED,
    )
    result = await uow.session.execute(stmt)
    doc = result.scalars().first()
    if doc is None:
        raise NotFoundError("Document not found.")

    # Ownership check: owner or document.delete permission
    if doc.uploaded_by != actor.id and "document.delete" not in actor.permissions:
        from app.core.exceptions import ForbiddenError

        raise ForbiddenError("You do not have permission to delete this document.")

    doc.status = DocumentStatus.DELETED

    await write_audit(
        uow,
        actor_id=actor.id,
        action="document.deleted",
        entity_type="document",
        entity_id=doc.id,
        request_context=ctx,
    )
    await uow.commit()
