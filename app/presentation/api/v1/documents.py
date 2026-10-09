"""Document endpoints – /api/v1/documents/* (presigned upload flow)."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.application.documents.use_cases import (
    confirm_upload,
    delete_document,
    get_document,
    initiate_upload,
    list_documents,
)
from app.core.dependencies import (
    CurrentUser,
    RequestContext,
    get_request_context,
    get_uow,
    require_permission,
)
from app.core.permissions import P
from app.core.responses import created_response, success_response
from app.infrastructure.database.uow import SqlAlchemyUnitOfWork
from app.presentation.schemas.documents import UploadDocumentRequest

router = APIRouter(prefix="/documents", tags=["Documents"])


@router.post("/upload", summary="Initiate presigned upload")
async def upload_document_endpoint(
    body: UploadDocumentRequest,
    user: Annotated[CurrentUser, Depends(require_permission(P.DOCUMENT_UPLOAD))],
    uow: Annotated[SqlAlchemyUnitOfWork, Depends(get_uow)],
    ctx: Annotated[RequestContext, Depends(get_request_context)],
):
    result = await initiate_upload(
        filename=body.filename,
        size_bytes=body.size_bytes,
        content_type=body.content_type,
        employee_id=body.employee_id,
        actor=user,
        uow=uow,
        ctx=ctx,
    )
    return created_response(
        data={
            "document_id": result.document_id,
            "upload_url": result.upload_url,
            "upload_headers": result.upload_headers,
        },
        message="Upload initiated. PUT the file to the upload_url.",
    )


@router.post("/{document_id}/confirm", summary="Confirm upload completed")
async def confirm_document_endpoint(
    document_id: str,
    user: Annotated[CurrentUser, Depends(require_permission(P.DOCUMENT_UPLOAD))],
    uow: Annotated[SqlAlchemyUnitOfWork, Depends(get_uow)],
    ctx: Annotated[RequestContext, Depends(get_request_context)],
):
    doc = await confirm_upload(document_id, actor=user, uow=uow, ctx=ctx)
    return success_response(
        data={"id": doc.id, "status": doc.status, "size_bytes": doc.size_bytes},
        message="Document confirmed.",
    )


@router.get("", summary="List documents")
async def list_documents_endpoint(
    user: Annotated[CurrentUser, Depends(require_permission(P.DOCUMENT_READ))],
    uow: Annotated[SqlAlchemyUnitOfWork, Depends(get_uow)],
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    employee_id: str | None = Query(None),
):
    result = await list_documents(uow, offset=offset, limit=limit, employee_id=employee_id)
    return success_response(
        data={
            "items": result.items,
            "total": result.total,
            "offset": result.offset,
            "limit": result.limit,
        }
    )


@router.get("/{document_id}", summary="Get document metadata + download URL")
async def get_document_endpoint(
    document_id: str,
    user: Annotated[CurrentUser, Depends(require_permission(P.DOCUMENT_READ))],
    uow: Annotated[SqlAlchemyUnitOfWork, Depends(get_uow)],
):
    data = await get_document(document_id, uow)
    return success_response(data=data)


@router.delete("/{document_id}", summary="Soft-delete a document")
async def delete_document_endpoint(
    document_id: str,
    user: Annotated[CurrentUser, Depends(require_permission(P.DOCUMENT_DELETE))],
    uow: Annotated[SqlAlchemyUnitOfWork, Depends(get_uow)],
    ctx: Annotated[RequestContext, Depends(get_request_context)],
):
    await delete_document(document_id, actor=user, uow=uow, ctx=ctx)
    return success_response(message="Document deleted.")
