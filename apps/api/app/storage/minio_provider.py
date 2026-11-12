"""MinIO backend for Local Docker Mode, built on the official minio SDK.

Used only when ``STORAGE_PROVIDER=minio`` (Local Docker Mode, Phase 10),
so this module is imported lazily inside the factory and the hosted demo
never pays for or imports it. SDK surface confirmed against installed
minio 7.2.20:

- ``Minio(endpoint, access_key=..., secret_key=...)`` — plain host:port,
  no scheme; ``secure=False`` because the local Compose network is plain
  HTTP inside the loopback, which the flag documents here.
- ``presigned_put_object(bucket, object)`` — returns an absolute
  presigned PUT URL; expiry defaults to 7 days and is surfaced as-is.
- ``stat_object`` — object metadata; a missing object raises ``S3Error``
  with ``code == "NoSuchKey"`` (the 404 mapping in minio's api.py).
- ``get_object`` — response whose ``.read()`` yields bytes, then
  ``.release_conn()`` and ``.close()`` return the connection to the pool.
- ``remove_object`` — idempotent delete for our purposes.
"""

import structlog
from minio import Minio
from minio.error import S3Error

from app.config import get_settings
from app.storage.base import SignedUpload, StorageObjectMeta, StorageProvider

logger = structlog.get_logger(__name__)


class MinIOStorageProvider(StorageProvider):
    """StorageProvider backed by a private MinIO bucket (Local Docker Mode)."""

    def __init__(self) -> None:
        """Build the Minio client from MINIO_* settings.

        ``secure=False`` is deliberate: the Compose network serves plain
        HTTP on localhost; TLS is a Phase 11 hosting concern, not a
        local-docker one.
        """
        settings = get_settings()
        self._bucket = settings.MINIO_BUCKET
        self._client = Minio(
            endpoint=settings.MINIO_ENDPOINT,
            access_key=settings.MINIO_ACCESS_KEY,
            secret_key=settings.MINIO_SECRET_KEY,
            secure=False,
        )

    def create_upload_url(self, storage_path: str, content_type: str) -> SignedUpload:
        """Presign a PUT URL; the client uploads with the declared type.

        The presigned URL embeds the bucket, object, and expiry in its
        signature; ``Content-Type`` rides as a request header the client
        must send, exactly as with the Supabase backend.
        """
        url = self._client.presigned_put_object(self._bucket, storage_path)
        return SignedUpload(
            url=url,
            method="PUT",
            headers={"Content-Type": content_type},
            # presigned_put_object default expiry: 7 days, per the SDK
            # signature default timedelta(days=7); surfaced, not configured.
            expires_in_seconds=7 * 24 * 60 * 60,
            storage_path=storage_path,
        )

    def verify_file(self, storage_path: str) -> StorageObjectMeta | None:
        """Return object metadata, or None when the object is absent.

        ``stat_object`` raising ``S3Error`` with code ``NoSuchKey`` is the
        documented 404 mapping for a missing object; any other S3Error
        propagates as a real storage failure.
        """
        try:
            stat = self._client.stat_object(self._bucket, storage_path)
        except S3Error as exc:
            if exc.code == "NoSuchKey":
                return None
            raise
        content_type = stat.content_type or "application/octet-stream"
        return StorageObjectMeta(
            storage_path=storage_path,
            size_bytes=int(stat.size or 0),
            content_type=content_type,
        )

    def download_file(self, storage_path: str) -> bytes:
        """Return the object's full bytes, releasing the connection after.

        ``read`` then ``release_conn`` then ``close`` is the documented
        urllib3-style lifecycle for the minio response: without
        ``release_conn`` the pooled connection stays checked out until
        garbage collection and long runs starve the pool.
        """
        response = self._client.get_object(self._bucket, storage_path)
        try:
            return response.read()
        finally:
            response.release_conn()
            response.close()

    def delete_file(self, storage_path: str) -> None:
        """Remove the object; S3 delete of an absent object is not an error."""
        self._client.remove_object(self._bucket, storage_path)
        logger.info("storage_object_deleted", storage_path=storage_path)
