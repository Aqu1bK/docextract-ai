# docextract-ai/apps/api/app/api/v1/router.py

"""API v1 router aggregating all endpoint routers under the version prefix."""

from fastapi import APIRouter

from app.api.v1.endpoints import audit, auth, documents, export, extraction, health, review
from app.config import get_settings

api_v1_router = APIRouter(prefix=get_settings().API_V1_STR)
api_v1_router.include_router(health.router)
api_v1_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_v1_router.include_router(documents.router, prefix="/documents", tags=["documents"])
api_v1_router.include_router(extraction.router, prefix="/extraction", tags=["extraction"])
api_v1_router.include_router(review.router, prefix="/review", tags=["review"])
api_v1_router.include_router(export.router, prefix="/exports", tags=["exports"])
api_v1_router.include_router(audit.router, prefix="/audit", tags=["audit"])