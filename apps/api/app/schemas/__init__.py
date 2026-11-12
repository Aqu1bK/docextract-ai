"""Pydantic request/response schemas for the two-step upload contract.

Schemas live in their own package so the wire contract is importable by
the frontend (Phase 9 mirrors these shapes) without importing a single
ORM model. Fields carry constraints, not just types: a 300-character
file name or a zero size is a validation error before any service runs.
"""
