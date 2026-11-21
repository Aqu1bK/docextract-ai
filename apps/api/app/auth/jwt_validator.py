# docextract-ai/apps/api/app/auth/jwt_validator.py

"""Server-side validation of Supabase-issued JWTs.

Supabase Auth is the hosted JWT issuer: it authenticates a person (password
login, magic link, OAuth) and signs an access token. This API is the relying
party — it receives that token as a Bearer credential on every request and
must decide, on its own, whether to believe it.

Why validate server-side: a token arriving over the network is a *claim*,
not a proof. Only the signature check proves the token was issued by this
project's Supabase and has not been edited since. Skipping that check — or
trusting identity fields sent in a request body — means anyone with curl is
every user at once.

Supabase has *two* signing regimes, and the validator must accept both:

- **Legacy (before October 1, 2025):** HS256 with the project's shared
  secret (``SUPABASE_JWT_SECRET``, symmetric — both sides know it).
- **Modern (default for new projects since October 1, 2025):** ES256 or
  RS256 with an asymmetric keypair. The private key never leaves Supabase;
  the public keys are published at the JWKS endpoint
  (``{SUPABASE_URL}/auth/v1/.well-known/jwks.json``). Verification fetches
  the public key once and caches it — no Auth-server round-trip per request.

Claims verified here, in order of severity:

- **Signature** (HS256 with ``SUPABASE_JWT_SECRET``, or ES256/RS256 with
  the JWKS public key): editing any payload byte breaks it.
- **Issuer** (``iss`` must equal ``settings.jwt_issuer``): a valid token
  from *another* Supabase project must not grant access to this one.
- **Expiration** (``exp``): PyJWT checks it during decode; an expired token
  is rejected without a database round-trip.

Key rotation: Supabase can rotate its signing keys; the new public key
appears in the JWKS with a new ``kid``. ``PyJWKClient``'s built-in two-tier
cache handles this on its own — an unknown ``kid`` triggers exactly one
cache refresh (note: PyJWT's default behavior can refresh on each
unknown-``kid`` miss; pinning ``pyjwt>=2.14`` is what keeps the
cache-refresh path safe from the redirect-trust issue recorded as
CVE-2026-102267). No manual TTL management anywhere in this module.

What we extract: the ``email`` claim, used by the caller for the
users-table lookup. The token proves identity; the database row proves
authorization.
"""

from typing import Any, cast

import jwt
import structlog
from jwt import (
    InvalidAlgorithmError,
    PyJWKClient,
    PyJWKClientConnectionError,
    PyJWKClientError,
)

from app.config import Settings, get_settings
from app.errors import UnauthorizedException
from app.middleware import get_request_id

logger = structlog.get_logger(__name__)

# The algorithms this validator accepts, mapped to their verification path.
# Anything outside the tuple is rejected — see the dispatch in
# validate_supabase_jwt.
HS256_ALGORITHM = "HS256"
ASYMMETRIC_ALGORITHMS = ("ES256", "RS256")
SUPPORTED_ALGORITHMS = (HS256_ALGORITHM, *ASYMMETRIC_ALGORITHMS)

# Supabase stamps "aud": "authenticated" on user tokens, but audience is
# not a trust boundary for this API: authorization comes from the roles
# table after the users-table lookup, and the security-relevant claims
# are signature + issuer + expiry. PyJWT's audience check requires an
# explicit expected audience; disabling it keeps verification focused on
# the claims that matter here (and keeps locally-minted test tokens,
# which carry no aud claim, valid).
DECODE_OPTIONS: dict[str, Any] = {"verify_aud": False}

# Module-level cache for the JWKS client: one client (and therefore one
# fetched-and-cached key set) per process. Rebuilt only if the JWKS URL
# changes, which tests rely on when they point SUPABASE_URL elsewhere.
_jwk_client: PyJWKClient | None = None
_jwk_client_url: str | None = None


def _get_jwk_client(settings: Settings) -> PyJWKClient:
    """Return the process-wide ``PyJWKClient`` for the JWKS endpoint.

    One instance holds the two-tier cache (a time-based default cache plus
    a per-``kid`` lru cache), so the public keys are fetched from Supabase
    once per process — not once per request. A new settings URL (tests do
    this) builds a fresh client instead of reusing one pointed at the old
    endpoint.

    Tests replace this function wholesale (monkeypatch) with a fake client
    that serves a local public key — that is the provider seam.
    """
    global _jwk_client, _jwk_client_url
    if _jwk_client is None or _jwk_client_url != settings.jwt_jwks_url:
        _jwk_client = PyJWKClient(settings.jwt_jwks_url)
        _jwk_client_url = settings.jwt_jwks_url
    return _jwk_client


def _reject(exc: BaseException) -> UnauthorizedException:
    """Log a validation failure and build its 401 envelope.

    One shared shape for every failure path — HS256 decode errors, JWKS
    lookup errors, unsupported algorithms — so an operator grepping
    ``jwt_validation_failed`` in the logs sees the same fields regardless
    of which path rejected the token.

    The error CLASS NAME goes into details and the log, not str(exc): it is
    stable, machine-readable, and reveals nothing about the secret or the
    token's contents.
    """
    logger.warning(
        "jwt_validation_failed",
        request_id=get_request_id(),
        reason=type(exc).__name__,
    )
    return UnauthorizedException(details={"reason": type(exc).__name__})


def _verify_hs256(token: str, settings: Settings) -> dict[str, Any]:
    """Verify a legacy HS256 token with the shared secret.

    The algorithm list is passed explicitly: ``jwt.decode`` without it is
    the deprecated pattern that enabled algorithm-confusion attacks, and
    PyJWT refuses an unset algorithm for exactly that reason.
    """
    try:
        return jwt.decode(
            token,
            key=settings.SUPABASE_JWT_SECRET,
            algorithms=[HS256_ALGORITHM],
            issuer=settings.jwt_issuer,
            options=cast(Any, DECODE_OPTIONS),
        )
    except jwt.InvalidTokenError as exc:
        raise _reject(exc) from exc


def _verify_asymmetric(token: str, algorithm: str, kid: str, settings: Settings) -> dict[str, Any]:
    """Verify an ES256/RS256 token with the public key from the JWKS.

    Two steps, two failure classes: ``get_signing_key`` can fail while
    fetching the key set (network) or because ``kid`` is unknown (the token
    was signed by a key this JWKS does not publish — possibly one rotated
    out, possibly a forgery); ``jwt.decode`` then fails like the HS256 path
    on signature, issuer, or expiration. Both map to the same 401 envelope
    so clients see one error shape.
    """
    jwk_client = _get_jwk_client(settings)
    try:
        signing_key = jwk_client.get_signing_key(kid)
    except PyJWKClientConnectionError as exc:
        # Network-unreachable JWKS: log it separately from decode failures
        # so on-call can tell "Supabase is down / unreachable" from "bad
        # token" without opening the traceback.
        raise _reject(exc) from exc
    except PyJWKClientError as exc:
        raise _reject(exc) from exc

    try:
        return jwt.decode(
            token,
            key=signing_key.key,
            algorithms=[algorithm],
            issuer=settings.jwt_issuer,
            options=cast(Any, DECODE_OPTIONS),
        )
    except jwt.InvalidTokenError as exc:
        raise _reject(exc) from exc


def validate_supabase_jwt(token: str) -> dict[str, Any]:
    """Validate a Supabase JWT (HS256 or ES256/RS256) and return its payload.

    The token's *unverified* header says which algorithm signed it; that
    choice is data, not an instruction. Reading it is safe — it only picks
    the verification path — while the actual trust decision still happens
    inside ``jwt.decode`` with an explicit algorithm list and the expected
    issuer, never with values the token itself supplies.

    Returns:
        The decoded payload dict, including the ``email`` claim the caller
        uses for user lookup.

    Raises:
        UnauthorizedException: If the algorithm is unsupported, the key
            cannot be found, or the token is invalid, expired, or fails
            signature or issuer checks.
    """
    settings = get_settings()

    # jwt.get_unverified_header validates the token's structure before
    # returning the header, so a malformed token raises here.
    try:
        unverified_header: dict[str, Any] = jwt.get_unverified_header(token)
    except jwt.InvalidTokenError as exc:
        raise _reject(exc) from exc

    algorithm = unverified_header.get("alg")
    kid = unverified_header.get("kid")

    if algorithm == HS256_ALGORITHM:
        return _verify_hs256(token, settings)
    if algorithm in ASYMMETRIC_ALGORITHMS:
        return _verify_asymmetric(token, algorithm, kid or "", settings)

    # Do not trust the token's self-declared alg — only the algorithms we
    # support. Algorithm confusion is the attack vector this rejection
    # prevents: a token claiming "none"/"RS256" against an HS256 secret
    # (CVE-2015-9235 class of bugs) must fail closed. PyJWT's own exception
    # (InvalidAlgorithmError) keeps the 401 envelope's reason stable
    # without this module inventing a new error class.
    raise _reject(InvalidAlgorithmError(algorithm))
