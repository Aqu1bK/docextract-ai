# docsxtract-ai/apps/api/tests/fakes.py

"""Test doubles: in-memory implementations of real interfaces.

A fake that honors the same contract as production is the cheapest way
to run the real flow in CI without credentials, network, or buckets.
Only the storage provider is faked so far; each fake stays in this
module (never imported by app code) and matches the interface exactly,
so tests exercise every branch of the real logic against a provider
whose behavior we control line by line.
"""

from app.storage.base import SignedUpload, StorageObjectMeta, StorageProvider


class FakeStorageProvider(StorageProvider):
    """In-memory StorageProvider: two dicts standing in for a bucket.

    ``objects`` maps storage_path to bytes and ``metas`` maps
    storage_path to metadata, which is exactly the state a real bucket
    keeps. ``put_object`` is the test hook that plays the role of the
    client's PUT to the signed URL — the fake cannot enforce a signature,
    so the hook is the moment "the client uploaded" happens.
    """

    def __init__(self) -> None:
        """Start with an empty bucket."""
        self.objects: dict[str, bytes] = {}
        self.metas: dict[str, StorageObjectMeta] = {}

    def put_object(self, storage_path: str, data: bytes, content_type: str) -> None:
        """Simulate the client uploading bytes to the signed URL."""
        self.objects[storage_path] = data
        self.metas[storage_path] = StorageObjectMeta(
            storage_path=storage_path,
            size_bytes=len(data),
            content_type=content_type,
        )

    def create_upload_url(self, storage_path: str, content_type: str) -> SignedUpload:
        """Mint a fake signed URL mirroring the real contract's shape."""
        return SignedUpload(
            url=f"fake://upload/{storage_path}",
            method="PUT",
            headers={"Content-Type": content_type},
            expires_in_seconds=120,
            storage_path=storage_path,
        )

    def verify_file(self, storage_path: str) -> StorageObjectMeta | None:
        """Return metadata when the fake bucket holds the object."""
        return self.metas.get(storage_path)

    def download_file(self, storage_path: str) -> bytes:
        """Return the object's bytes (KeyError mirrors a real absence)."""
        return self.objects[storage_path]

    def delete_file(self, storage_path: str) -> None:
        """Remove the object; absence is a no-op, like the real bucket."""
        self.objects.pop(storage_path, None)
        self.metas.pop(storage_path, None)
