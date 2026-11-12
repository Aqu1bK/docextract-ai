"""Storage abstraction: the interface every object-storage backend implements.

One interface, three implementations (Supabase Storage, MinIO, and a fake for
tests) is the strategy pattern in its plainest form: the upload service codes
against ``StorageProvider`` and never learns which backend answered. That is
what makes the two operating modes a configuration change (``STORAGE_PROVIDER``
env var) rather than a code change, and what lets the CI suite run the exact
production flow with ``FakeStorageProvider`` instead of a real bucket.
"""
