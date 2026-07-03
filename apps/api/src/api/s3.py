import io
import os
import uuid
from pathlib import Path

from minio import Minio
from minio.error import S3Error

from api.config import settings
from api.logging import logger

_LOCAL_STORAGE_DIR = Path("/tmp/dataproof-uploads")


def get_minio_client() -> Minio | None:
    """Return a MinIO client, or None if MinIO is unreachable."""
    try:
        client = Minio(
            settings.minio_endpoint,
            access_key=settings.minio_access_key,
            secret_key=settings.minio_secret_key,
            secure=settings.minio_secure,
        )
        # Test the connection
        client.bucket_exists(settings.minio_bucket)
        return client
    except Exception as exc:
        logger.warning("minio_unavailable", error=str(exc))
        return None


def _local_path(s3_key: str) -> Path:
    return _LOCAL_STORAGE_DIR / s3_key


def ensure_bucket(client: Minio | None, bucket_name: str) -> None:
    if client is None:
        _LOCAL_STORAGE_DIR.mkdir(parents=True, exist_ok=True)
        return
    try:
        if not client.bucket_exists(bucket_name):
            client.make_bucket(bucket_name)
    except S3Error as exc:
        logger.warning("minio_bucket_error", error=str(exc))


def upload_file_to_minio(
    user_id: int, dataset_id: int, filename: str, data: bytes
) -> str:
    client = get_minio_client()
    s3_key = f"user_{user_id}/dataset_{dataset_id}/{uuid.uuid4()}_{filename}"

    if client is None:
        # Fall back to local storage
        path = _local_path(s3_key)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        logger.info("file_stored_locally", path=str(path), key=s3_key)
        return s3_key

    ensure_bucket(client, settings.minio_bucket)
    client.put_object(
        settings.minio_bucket,
        s3_key,
        io.BytesIO(data),
        len(data),
    )
    return s3_key


def download_file_from_minio(s3_key: str) -> bytes:
    client = get_minio_client()
    if client is None:
        path = _local_path(s3_key)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {s3_key}")
        return path.read_bytes()

    response = client.get_object(settings.minio_bucket, s3_key)
    return response.read()
