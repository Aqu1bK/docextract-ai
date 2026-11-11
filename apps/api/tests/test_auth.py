"""Auth and RBAC tests: the full validation stack without a real Supabase project.

Every token is minted locally, signed with the same HS256 secret the
validator checks and carrying the same claims Supabase issues (``iss``
derived from ``SUPABASE_URL``, ``exp`` offset from now), so a green suite
means the real validation path accepts what Supabase actually sends — and
rejects the forgeries it must reject.
"""

from collections.abc import Callable, Iterator

import pytest
from fastapi import APIRouter, Depends, FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.auth.dependencies import require_roles
from app.db.models import User
from app.db.session import get_db
from app.domain.enums import RoleName
from app.errors import AppException, app_exception_handler

# ----------------------------------------------------------------------
# RBAC test routes. Production scope for Phase 4 is exactly one endpoint
# (GET /auth/me); role enforcement still needs protected routes to be
# testable, so they are declared here on a throwaway app and never shipped.
# ----------------------------------------------------------------------

rbac_router = APIRouter()


@rbac_router.get("/admin-only")
# B008 (call in default) is the documented FastAPI idiom for declaring
# dependencies; there is no cleaner form this lint rule accepts.
def admin_only(
    user: User = Depends(require_roles([RoleName.ADMIN])),  # noqa: B008
) -> dict[str, str]:
    """Route guarded by require_roles([ADMIN]) for the RBAC tests."""
    return {"email": user.email}


@rbac_router.get("/reviewer-or-admin")
def reviewer_or_admin(
    user: User = Depends(require_roles([RoleName.REVIEWER, RoleName.ADMIN])),  # noqa: B008
) -> dict[str, str]:
    """Route allowing REVIEWER or ADMIN for the multi-role intersection test."""
    return {"email": user.email}


@pytest.fixture
def rbac_client(db_session: Session) -> Iterator[TestClient]:
    """TestClient on a throwaway app mounting the RBAC test routes.

    Same override pattern as ``client_with_db``: the ``get_db`` dependency
    resolves to the test session, so rows seeded by ``seed_test_user`` are
    visible to requests and everything rolls back at teardown.
    """
    rbac_app = FastAPI()
    # Same stub-signature mismatch as app/main.py; see the comment there.
    rbac_app.add_exception_handler(AppException, app_exception_handler)  # type: ignore[arg-type]
    rbac_app.include_router(rbac_router)

    def _override_get_db() -> Iterator[Session]:
        yield db_session

    rbac_app.dependency_overrides[get_db] = _override_get_db
    with TestClient(rbac_app) as test_client:
        yield test_client


def auth_header(token: str) -> dict[str, str]:
    """Build the Authorization header dict for a token."""
    return {"Authorization": f"Bearer {token}"}


# ----------------------------------------------------------------------
# Authentication: GET /auth/me through the real application
# ----------------------------------------------------------------------


def test_valid_token_returns_user(
    client_with_db: TestClient,
    create_test_token: Callable[..., str],
    seed_test_user: Callable[..., User],
) -> None:
    """A valid JWT for a seeded active user returns 200 with identity and roles."""
    seed_test_user("valid@auth.test", roles=["admin"])
    token = create_test_token("valid@auth.test")

    response = client_with_db.get("/api/v1/auth/me", headers=auth_header(token))

    assert response.status_code == 200
    body = response.json()
    assert body["email"] == "valid@auth.test"
    assert body["full_name"] == "Test Valid"
    assert body["roles"] == ["admin"]
    assert body["user_id"]


def test_missing_token_returns_401(client_with_db: TestClient) -> None:
    """No Authorization header produces a 401 in the standard envelope."""
    response = client_with_db.get("/api/v1/auth/me")

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "NOT_AUTHENTICATED"


def test_invalid_signature_returns_401(
    client_with_db: TestClient,
    create_test_token: Callable[..., str],
    seed_test_user: Callable[..., User],
) -> None:
    """A token signed with the wrong secret is rejected with 401 UNAUTHORIZED."""
    seed_test_user("tampered@auth.test", roles=["viewer"])
    # Long on purpose: PyJWT warns when an HMAC key is under 32 bytes, and
    # the suite must add zero new warnings. The key just has to be WRONG,
    # not short.
    token = create_test_token(
        "tampered@auth.test", secret="wrong-secret-0123456789abcdef0123456789"
    )

    response = client_with_db.get("/api/v1/auth/me", headers=auth_header(token))

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "UNAUTHORIZED"
    assert response.json()["error"]["details"]["reason"] == "InvalidSignatureError"


def test_expired_token_returns_401(
    client_with_db: TestClient,
    create_test_token: Callable[..., str],
    seed_test_user: Callable[..., User],
) -> None:
    """An expired token (exp in the past) is rejected with 401 UNAUTHORIZED."""
    seed_test_user("expired@auth.test", roles=["viewer"])
    token = create_test_token("expired@auth.test", exp_offset_seconds=-60)

    response = client_with_db.get("/api/v1/auth/me", headers=auth_header(token))

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "UNAUTHORIZED"
    assert response.json()["error"]["details"]["reason"] == "ExpiredSignatureError"


def test_unknown_email_returns_401(
    client_with_db: TestClient,
    create_test_token: Callable[..., str],
) -> None:
    """A valid JWT whose email has no users row is rejected with 401."""
    token = create_test_token("ghost@auth.test")

    response = client_with_db.get("/api/v1/auth/me", headers=auth_header(token))

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "UNAUTHORIZED"
    assert response.json()["error"]["details"]["reason"] == "unknown_or_inactive_user"


def test_inactive_user_returns_401(
    client_with_db: TestClient,
    create_test_token: Callable[..., str],
    seed_test_user: Callable[..., User],
) -> None:
    """A valid JWT for an is_active=false user is rejected with 401."""
    seed_test_user("disabled@auth.test", roles=["viewer"], is_active=False)
    token = create_test_token("disabled@auth.test")

    response = client_with_db.get("/api/v1/auth/me", headers=auth_header(token))

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "UNAUTHORIZED"
    assert response.json()["error"]["details"]["reason"] == "unknown_or_inactive_user"


# ----------------------------------------------------------------------
# Authorization: require_roles through the throwaway RBAC app
# ----------------------------------------------------------------------


def test_admin_can_access_admin_endpoint(
    rbac_client: TestClient,
    create_test_token: Callable[..., str],
    seed_test_user: Callable[..., User],
) -> None:
    """An admin-role user passes require_roles([ADMIN])."""
    seed_test_user("root@auth.test", roles=["admin"])
    token = create_test_token("root@auth.test")

    response = rbac_client.get("/admin-only", headers=auth_header(token))

    assert response.status_code == 200
    assert response.json()["email"] == "root@auth.test"


def test_viewer_cannot_access_admin_endpoint(
    rbac_client: TestClient,
    create_test_token: Callable[..., str],
    seed_test_user: Callable[..., User],
) -> None:
    """A viewer-role user hitting require_roles([ADMIN]) gets a 403 envelope."""
    seed_test_user("looker@auth.test", roles=["viewer"])
    token = create_test_token("looker@auth.test")

    response = rbac_client.get("/admin-only", headers=auth_header(token))

    assert response.status_code == 403
    body = response.json()["error"]
    assert body["code"] == "FORBIDDEN"
    assert body["details"]["required_roles"] == ["admin"]


def test_multiple_roles_allowed(
    rbac_client: TestClient,
    create_test_token: Callable[..., str],
    seed_test_user: Callable[..., User],
) -> None:
    """A user holding [REVIEWER, UPLOADER] passes require_roles([REVIEWER, ADMIN]).

    Only the intersection matters: the user holds none of the ADMIN role but
    does hold REVIEWER, which is enough for an any-of policy.
    """
    seed_test_user("dual@auth.test", roles=["reviewer", "uploader"])
    token = create_test_token("dual@auth.test")

    response = rbac_client.get("/reviewer-or-admin", headers=auth_header(token))

    assert response.status_code == 200
    assert response.json()["email"] == "dual@auth.test"


def test_require_roles_with_no_roles_returns_403(
    rbac_client: TestClient,
    create_test_token: Callable[..., str],
    seed_test_user: Callable[..., User],
) -> None:
    """A user with no role links at all is forbidden on a role-guarded route."""
    seed_test_user("norole@auth.test", roles=[])
    token = create_test_token("norole@auth.test")

    response = rbac_client.get("/admin-only", headers=auth_header(token))

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "FORBIDDEN"
