"""The storage provider contract: four operations, nothing more.

Why an interface instead of calling a specific SDK: the same API must run
against Supabase Storage on the hosted demo and MinIO in Local Docker Mode,
and the test suite must run against neither (a fake). A narrow abstract base
class pinned to exactly these four operations keeps every backend
interchangeable: call sites depend on ``StorageProvider``, the factory picks
the implementation from ``STORAGE_PROVIDER``, and no business code imports an
SDK. Adding a fifth method to the interface means implementing it in every
provider — which is the point: the surface stays small on purpose.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True)
class SignedUpload:
    """Everything a client needs to upload one object without our help.

    The URL and method are replayed verbatim by any HTTP client (the Phase 9
    frontend uses ``fetch``), so the API server never carries file bytes.
    """

    url: str
    method: str
    headers: dict[str, str]
    expires_in_seconds: int
    storage_path: str


@dataclass(frozen=True)
class StorageObjectMeta:
    """What the backend reports about one stored object.

    Used to confirm the client really uploaded what it claimed: size comes
    from the backend, never from the request, so a lying client cannot
    mislead the confirm step.
    """

    storage_path: str
    size_bytes: int
    content_type: str


class StorageProvider(ABC):
    """Four-operation contract every storage backend must implement."""

    @abstractmethod
    def create_upload_url(self, storage_path: str, content_type: str) -> SignedUpload:
        """Return a time-limited signed upload URL for one new object."""

    @abstractmethod
    def verify_file(self, storage_path: str) -> StorageObjectMeta | None:
        """Return stored-object metadata, or None when the object is absent."""

    @abstractmethod
    def download_file(self, storage_path: str) -> bytes:
        """Return the object's full bytes (acceptable at <= 10 MB demo scale)."""

    @abstractmethod
    def delete_file(self, storage_path: str) -> None:
        """Remove the object; absence is not an error."""
