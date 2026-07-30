"""Object storage (MinIO/S3) helper for attachments and document imports."""

import io

from minio import Minio

from app.core.config import get_settings

settings = get_settings()


def _client() -> Minio:
    return Minio(
        settings.minio_endpoint,
        access_key=settings.minio_root_user,
        secret_key=settings.minio_root_password,
        secure=False,
    )


def ensure_bucket() -> None:
    client = _client()
    if not client.bucket_exists(settings.minio_bucket):
        client.make_bucket(settings.minio_bucket)


def put_object(key: str, data: bytes, content_type: str = "application/octet-stream") -> str:
    ensure_bucket()
    client = _client()
    client.put_object(
        settings.minio_bucket,
        key,
        io.BytesIO(data),
        length=len(data),
        content_type=content_type,
    )
    return key


def get_object(key: str) -> bytes:
    client = _client()
    resp = client.get_object(settings.minio_bucket, key)
    try:
        return resp.read()
    finally:
        resp.close()
        resp.release_conn()