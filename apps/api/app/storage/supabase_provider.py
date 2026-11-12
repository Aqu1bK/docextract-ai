# docextract-ai/apps/api/app/storage/supabase_provider.py

"""Supabase Storage backend built on the official storage3 SDK.

storage3 is the storage client ``supabase-py`` wraps; we use it directly so
the dependency stays one package instead of the full supabase bundle. The
SDK surface used here was confirmed against installed storage3 2.34.1:

- ``SyncStorageClient(url, headers)`` — constructor takes the storage
  endpoint and an Authorization header dict.
- ``.from_(bucket_id)`` — returns the bucket-scoped ``SyncBucketProxy``.
- ``create_signed_upload_url(path)`` — POST to ``/object/upload/sign/{bucket}``,
  returns ``signed_url`` already ABSOLUTE (the SDK joins its base URL) plus
  the one-time ``token``.
- ``upload_to_signed_url`` — the SDK's own upload uses verb PUT with the
  file as a multipart part carrying ``Content-Type``; we mirror exactly
  that verb and header into ``SignedUpload`` so any HTTP client can replay
  the upload verbatim.
- ``info(path)`` — object metadata (size, mimetype); 404 means absent.
- ``download(path)`` — full object bytes; ``remove(paths)`` — delete.

The bucket is PRIVATE: signed URLs are the only door, and every SDK call
carries the service role key server-side. The service role key must NEVER
reach the frontend — it bypasses all row-level security on the project.
"""

import structlog
from storage3 import SyncStorageClient
from storage3.exceptions import StorageApiError

from app.config import get_settings
from app.storage.base import SignedUpload, StorageObjectMeta, StorageProvider

logger = structlog.get_logger(__name__)


class SupabaseStorageProvider(StorageProvider):
    """StorageProvider backed by a private Supabase Storage bucket."""

    def __init__(self) -> None:
        """Build the storage3 client with the service-role authorization.

        The URL gets ``/storage/v1`` appended because Supabase serves the
        Storage API under that path, and a trailing slash because storage3's
        bucket API warns when joining URLs without one.
        """
        settings = get_settings()
        self._bucket_id = settings.STORAGE_BUCKET
        self._client = SyncStorageClient(
            url=f"{settings.SUPABASE_URL}/storage/v1/",
            headers={"Authorization": f"Bearer {settings.SUPABASE_SERVICE_ROLE_KEY}"},
        )

    def create_upload_url(self, storage_path: str, content_type: str) -> SignedUpload:
        """Create a one-time signed upload URL for a new object.

        The SDK's own ``upload_to_signed_url`` PUTs the file with this
        Content-Type, so those two facts are what we hand the client;
        the signed URL itself already carries the one-time token as a
        query parameter. Expiry is the Supabase default for signed upload
        URLs (120 seconds server-side); it is not configurable through
        the SDK, so the value is surfaced as-is.
        """
        signed = self._client.from_(self._bucket_id).create_signed_upload_url(storage_path)
        url: str = str(signed["signed_url"])
        return SignedUpload(
            url=url,
            method="PUT",
            headers={"Content-Type": content_type},
            expires_in_seconds=120,
            storage_path=storage_path,
        )

    def verify_file(self, storage_path: str) -> StorageObjectMeta | None:
        """Return object metadata from the backend, or None if absent.

        The size and content type reported here are the backend's own view
        of the stored object — never values echoed from the request — so
        the confirm step cannot be lied to about what was uploaded.
        Absence (404) is a normal outcome, not an error; anything else
        (bad credentials, missing bucket) propagates as a storage failure.
        """
        try:
            info = self._client.from_(self._bucket_id).info(storage_path)
        except StorageApiError as exc:
            if str(exc.status) == "404":
                return None
            raise

        # The storage3 SDK has returned both raw dicts (older/2.34.x versions)
        # and Pydantic FileObject models (newer versions) from this endpoint.
        # The exact location of the MIME type also varies (top-level vs nested
        # inside a 'metadata' dict). We normalize the access pattern so a SDK
        # upgrade never breaks the confirm flow.
        def _get(obj: object, key: str, default: object = None) -> object:
            if isinstance(obj, dict):
                return obj.get(key, default)
            return getattr(obj, key, default)

        metadata_obj = _get(info, "metadata", {}) or {}

        content_type = (
            _get(info, "mimetype")
            or _get(info, "content_type")
            or _get(info, "contentType")
            or _get(metadata_obj, "mimetype")
            or _get(metadata_obj, "mimeType")
            or _get(metadata_obj, "contentType")
            or "application/octet-stream"
        )

        raw_size = _get(info, "size", 0)
        # isinstance() validates at runtime AND narrows the type for mypy:
        # _get returns `object`, and int() has no overload accepting object.
        size_bytes = int(raw_size) if isinstance(raw_size, int | float | str) else 0

        return StorageObjectMeta(
            storage_path=storage_path,
            size_bytes=size_bytes,
            content_type=str(content_type),
        )

    def download_file(self, storage_path: str) -> bytes:
        """Return the object's full bytes via the authenticated read path.

        Acceptable at demo scale: documents are capped at 10 MB and 20
        pages, so the confirm step downloads the whole object to hash and
        parse it. A streaming or ranged design is only needed when the cap
        stops being small.
        """
        content: bytes = self._client.from_(self._bucket_id).download(storage_path)
        return content

    def delete_file(self, storage_path: str) -> None:
        """Remove the object; deleting an absent object is not an error."""
        self._client.from_(self._bucket_id).remove([storage_path])
        logger.info("storage_object_deleted", storage_path=storage_path)
