"""FastAPI dependencies for authentication and authorization.

FastAPI dependencies are the right shape for auth because they compose:
``get_current_user`` is declared on the endpoint, and ``require_roles``
declares ``get_current_user`` on itself — the framework resolves the whole
chain once per request, and every endpoint gets identical semantics instead
of hand-rolled ``if not user ...`` branches drifting apart file by file.

The security model is split on purpose: the token proves identity (signed
by Supabase, verified here), the database proves authorization (roles and
``is_active`` are rows this API controls). That split is also why the User
row is loaded on EVERY request rather than cached in the token: a role
revoked or a user deactivated in the database must take effect on the next
request, not on the next token — JWTs are already un-revocable signed
documents, so caching permissions inside them would extend that window
indefinitely.
"""

from collections.abc import Awaitable, Callable

from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.jwt_validator import validate_supabase_jwt
from app.db.models import Role, User, UserRole
from app.db.session import get_db
from app.domain.enums import RoleName
from app.errors import ForbiddenException, UnauthorizedException

# tokenUrl feeds only the OpenAPI "Authorize" button: Supabase issues the
# tokens, this API never serves a password flow, so the URL exists for
# documentation, not routing.
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth")


async def get_current_user(
    token: str = Depends(oauth2_scheme),  # noqa: B008
    db: Session = Depends(get_db),  # noqa: B008
) -> User:
    """Validate JWT and load the active User row.

    Reads the Bearer token, verifies it is signed by this project's
    Supabase (``validate_supabase_jwt``), then loads the matching row from
    ``users``. Loading the row per request — instead of trusting token
    claims for anything beyond identity — is what makes ``is_active``
    revocation and role changes effective immediately.

    Returns:
        The active ``User`` row for the token's email.

    Raises:
        UnauthorizedException: Missing/invalid token, unknown email, inactive user.
    """
    payload = validate_supabase_jwt(token)

    email = payload.get("email")
    if not isinstance(email, str) or not email:
        raise UnauthorizedException(details={"reason": "missing_email_claim"}) from None

    user = db.execute(
        select(User).where(User.email == email, User.is_active.is_(True))
    ).scalar_one_or_none()
    if user is None:
        # Unknown email and deactivated user share one response on purpose:
        # distinguishing them would let an unauthenticated caller enumerate
        # which emails have accounts.
        raise UnauthorizedException(details={"reason": "unknown_or_inactive_user"}) from None
    return user


def load_role_names(db: Session, user: User) -> list[str]:
    """Return the role names one user holds (``user_roles`` joined to ``roles``)."""
    stmt = (
        select(Role.name)
        .join(UserRole, UserRole.role_id == Role.id)
        .where(UserRole.user_id == user.id)
        .order_by(Role.name)
    )
    return list(db.execute(stmt).scalars())


def require_roles(allowed_roles: list[RoleName]) -> Callable[..., Awaitable[User]]:
    """Dependency factory: enforce that the caller holds at least one of allowed_roles.

    Usage:

        @router.get("/admin-only")
        def admin_endpoint(user: User = Depends(require_roles([RoleName.ADMIN]))):
            ...

    Why a factory and not a decorator: the allowed-roles list is fixed at
    route-declaration time but varies per route, so each route needs its own
    dependency function; a plain decorator cannot carry that per-route state
    into FastAPI's dependency resolution. The factory closes over the list
    and returns a checker FastAPI resolves per request: identity first
    (``get_current_user``, so 401 always precedes 403 — a caller without
    valid identity never learns which roles exist), then roles from the
    database, then the intersection test.
    """

    async def role_checker(
        current_user: User = Depends(get_current_user),  # noqa: B008
        db: Session = Depends(get_db),  # noqa: B008
    ) -> User:
        allowed = {role.value for role in allowed_roles}
        held = load_role_names(db, current_user)
        if not set(held) & allowed:
            raise ForbiddenException(details={"required_roles": sorted(allowed)}) from None
        return current_user

    return role_checker
