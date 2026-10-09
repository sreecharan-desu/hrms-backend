"""S3-compatible object storage client (MinIO / AWS S3).

Generates presigned PUT/GET URLs for the document presigned-upload flow.
No binary data ever passes through the API server.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass

import boto3
from botocore.config import Config as BotoConfig

from app.core.config import Settings, get_settings

_client = None


def _get_s3_client(settings: Settings | None = None):
    global _client
    if _client is not None:
        return _client
    settings = settings or get_settings()
    kwargs: dict = {
        "aws_access_key_id": settings.STORAGE_ACCESS_KEY,
        "aws_secret_access_key": settings.STORAGE_SECRET_KEY,
        "region_name": settings.STORAGE_REGION,
        "config": BotoConfig(signature_version="s3v4"),
    }
    if settings.STORAGE_ENDPOINT:
        kwargs["endpoint_url"] = settings.STORAGE_ENDPOINT
    _client = boto3.client("s3", **kwargs)
    return _client


def generate_storage_key(filename: str) -> str:
    """Create a unique object key: ``documents/<uuid>/<filename>``."""
    return f"documents/{uuid.uuid4().hex}/{filename}"


@dataclass(frozen=True, slots=True)
class PresignedUpload:
    url: str
    headers: dict[str, str]
    storage_key: str


def generate_presigned_put(
    storage_key: str,
    content_type: str,
    size_bytes: int,
    *,
    expires_in: int = 3600,
    settings: Settings | None = None,
) -> PresignedUpload:
    """Return a presigned PUT URL the client uses to upload directly to S3."""
    settings = settings or get_settings()
    client = _get_s3_client(settings)
    url = client.generate_presigned_url(
        "put_object",
        Params={
            "Bucket": settings.STORAGE_BUCKET,
            "Key": storage_key,
            "ContentType": content_type,
            "ContentLength": size_bytes,
        },
        ExpiresIn=expires_in,
    )
    return PresignedUpload(
        url=url,
        headers={"Content-Type": content_type, "Content-Length": str(size_bytes)},
        storage_key=storage_key,
    )


def generate_presigned_get(
    storage_key: str,
    *,
    expires_in: int = 900,
    settings: Settings | None = None,
) -> str:
    """Return a short-lived presigned GET URL for downloading a document."""
    settings = settings or get_settings()
    client = _get_s3_client(settings)
    return client.generate_presigned_url(
        "get_object",
        Params={
            "Bucket": settings.STORAGE_BUCKET,
            "Key": storage_key,
        },
        ExpiresIn=expires_in,
    )


def head_object(
    storage_key: str,
    *,
    settings: Settings | None = None,
) -> dict:
    """HEAD the object in S3 to verify it was uploaded."""
    settings = settings or get_settings()
    client = _get_s3_client(settings)
    return client.head_object(
        Bucket=settings.STORAGE_BUCKET,
        Key=storage_key,
    )
