"""Auth endpoints.

``GET /auth/me`` exists to prove the full auth stack end-to-end: JWT
validation, users-table lookup, and role loading — one request, all three
layers. Production endpoints declare ``require_roles`` for authorization;
this one only asks for identity.
"""

from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user, load_role_names
from app.db.models import User
from app.db.session import get_db

router = APIRouter()


@router.get("/me")
def get_current_user_info(
    current_user: User = Depends(get_current_user),  # noqa: B008
    db: Session = Depends(get_db),  # noqa: B008
) -> dict[str, Any]:
    """Return the authenticated user's identity and roles.

    This endpoint exists to verify the authentication stack works end-to-end.
    Production endpoints use require_roles for authorization.
    """
    return {
        "user_id": str(current_user.id),
        "email": current_user.email,
        "full_name": current_user.full_name,
        "roles": load_role_names(db, current_user),
    }