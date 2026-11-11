"""Server-side validation of Supabase-issued JWTs.

Supabase Auth is the hosted JWT issuer: it authenticates a person (password
login, magic link, OAuth) and signs an access token with the project's
HS256 secret. This API is the relying party — it receives that token as a
Bearer credential on every request and must decide, on its own, whether to
believe it.

Why validate server-side: a token arriving over the network is a *claim*,
not a proof. Only the signature check (against ``SUPABASE_JWT_SECRET``,
which no client ever sees) proves the token was issued by this project's
Supabase and has not been edited since. Skipping that check — or trusting
identity fields sent in a request body — means anyone with curl is every
user at once.

Claims verified here, in order of severity:

- **Signature** (HS256 with ``SUPABASE_JWT_SECRET``): editing any payload
  byte breaks it.
- **Issuer** (``iss`` must equal ``settings.jwt_issuer``): a valid token
  from *another* Supabase project must not grant access to this one.
- **Expiration** (``exp``): PyJWT checks it during decode; an expired token
  is rejected without a database round-trip.

What we extract: the ``email`` claim, used by the caller for the
users-table lookup. The token proves identity; the database row proves
authorization.
"""

from typing import Any

import jwt
import structlog

from app.config import get_settings
from app.errors import UnauthorizedException
from app.middleware import get_request_id

logger = structlog.get_logger(__name__)


def validate_supabase_jwt(token: str) -> dict[str, Any]:
    """Validate a Supabase JWT and return the decoded payload.

    The algorithm list is passed explicitly (``algorithms=["HS256"]``):
    ``jwt.decode`` without it is the deprecated pattern that enabled
    algorithm-confusion attacks, and PyJWT refuses an unset algorithm for
    exactly that reason.

    Returns:
        The decoded payload dict, including the ``email`` claim the caller
        uses for user lookup.

    Raises:
        UnauthorizedException: If token is invalid, expired, or signature fails.
    """
    settings = get_settings()
    try:
        payload: dict[str, Any] = jwt.decode(
            token,
            key=settings.SUPABASE_JWT_SECRET,
            algorithms=["HS256"],
            issuer=settings.jwt_issuer,
        )
    except jwt.InvalidTokenError as exc:
        # The error CLASS NAME goes into details and the log, not str(exc):
        # it is stable, machine-readable, and reveals nothing about the
        # secret or the token's contents.
        logger.warning(
            "jwt_validation_failed",
            request_id=get_request_id(),
            reason=type(exc).__name__,
        )
        raise UnauthorizedException(details={"reason": type(exc).__name__}) from exc
    return payload
