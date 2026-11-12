"""Storage provider selection: one function, driven by one env var.

The factory is a FastAPI dependency so every call site declares
``Depends(get_storage)`` the same way it declares ``Depends(get_db)`` —
backend choice then stays a wiring concern, and tests swap the provider
with ``app.dependency_overrides`` exactly as they swap the session.

Imports of the concrete providers are inside the function on purpose: the
hosted demo never imports ``minio`` (it is not installed there) and Local
Docker never imports ``storage3`` beyond what the demo needs. A bad
``STORAGE_PROVIDER`` value fails fast with a clear 500 envelope naming
the offending value instead of surfacing as a confusing ImportError later.
"""

from app.config import get_settings
from app.errors import InternalErrorException
from app.storage.base import StorageProvider


def get_storage() -> StorageProvider:
    """Return the storage provider selected by ``STORAGE_PROVIDER``.

    Raises:
        InternalErrorException: If ``STORAGE_PROVIDER`` is not one of the
            supported values; the envelope's ``details`` names the value
            so an operator sees the misconfiguration immediately.
    """
    provider = get_settings().STORAGE_PROVIDER
    if provider == "supabase":
        from app.storage.supabase_provider import SupabaseStorageProvider

        return SupabaseStorageProvider()
    if provider == "minio":
        from app.storage.minio_provider import MinIOStorageProvider

        return MinIOStorageProvider()
    raise InternalErrorException(details={"storage_provider": provider})
