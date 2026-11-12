"""Services: business logic the endpoints compose.

Services exist so business rules stay callable and testable without HTTP:
``file_validation`` is pure (bytes in, verdict out), while ``usage`` and
``documents`` take a session and own their database discipline (row locks,
row creation). Endpoints stay thin wiring: dependencies, schemas, calls.
"""
