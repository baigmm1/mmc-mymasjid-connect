"""
Core Dependencies

FastAPI dependencies for authentication, authorization, and shared resources.

Optimized to minimize Auth0 API calls:
- JWT claims are extracted first (no network call)
- Auth0 /userinfo is only called on cache miss
- Results are cached in-memory with a 5-minute TTL
"""

from typing import Optional
from fastapi import Depends, HTTPException, Header, status
from pydantic import BaseModel
import logging

from src.config import settings
from src.security.jwt_handler import get_jwt_handler
from src.providers.auth0_provider import get_auth0_provider
from src.models.user import User

logger = logging.getLogger(__name__)


def _build_user_from_jwt(payload: dict) -> User:
    """
    Build a User from JWT claims only (no network call).

    Auth0 JWTs always contain 'sub'. Depending on your Auth0 Action / Rule
    configuration they may also contain email, name, picture, etc.

    Roles are read from the custom namespace claim configured via
    ``AUTH0_ROLES_NAMESPACE`` (set by an Auth0 Action / Rule).  The claim
    value is expected to be a list of strings, e.g.::

        "https://masjidconnect.auth0.com/roles": ["admin", "vendor"]
    """
    logger.info(f"paylod {payload}")
    roles_claim = f"{settings.AUTH0_AUDIENCE}/roles"
    raw_roles = payload.get(roles_claim, [])
    roles: list[str] = raw_roles if isinstance(raw_roles, list) else []

    return User(
        id=payload.get("sub"),  # type: ignore
        email=payload.get("email"),
        name=payload.get("name"),
        first_name=payload.get("given_name"),
        last_name=payload.get("family_name"),
        nick_name=payload.get("nickname"),
        picture=payload.get("picture"),
        email_verified=payload.get("email_verified", False),
        roles=roles,
    )


def _user_needs_enrichment(user: User) -> bool:
    """Return True if the user is missing fields that /userinfo can provide."""
    return not user.email or not user.name


async def _fetch_roles_if_missing(user: User) -> User:
    """
    Fetch Auth0 roles from the Management API when none were found in the JWT.

    This is called after JWT extraction (and optional /userinfo enrichment) when
    the ``roles`` list is still empty — i.e. either no Auth0 Action is configured
    to embed roles in the token, or the token was issued before the Action was
    added.

    Results are cached in-memory inside the Auth0Provider (same 5-minute TTL as
    the userinfo cache) so repeat requests within a session do not incur extra
    Management API calls.
    """
    if user.roles:
        return user
    try:
        provider = get_auth0_provider()
        roles = await provider.get_user_roles(user.id)
        user.roles = roles
        logger.info(
            f"Roles populated from Management API for user: {user.id} — roles: {roles}"
        )
    except ValueError as e:
        # Configuration problem (missing/wrong credentials) — log clearly, do not retry
        logger.error(
            f"Management API configuration error for user '{user.id}': {e}"
        )
    except Exception as e:
        logger.warning(
            f"Could not fetch roles from Management API for user '{user.id}': {e}. "
            "Continuing with empty roles list."
        )
    return user


async def _enrich_user_from_auth0(user: User, token: str) -> User:
    """
    Fill in missing fields by calling Auth0 /userinfo (cached).

    This only makes a real HTTP call on the first invocation per token;
    subsequent calls within the TTL window are served from the in-memory cache.

    Roles present in the /userinfo response under the configured namespace claim
    are merged with any roles already extracted from the JWT.
    """
    try:
        auth0_provider = get_auth0_provider()
        user_info = await auth0_provider.get_user_info(token)
        user.name = user_info.get("name") or user.name
        user.first_name = user_info.get("given_name") or user.first_name
        user.last_name = user_info.get("family_name") or user.last_name
        user.nick_name = user_info.get("nickname") or user.nick_name
        user.picture = user_info.get("picture") or user.picture
        user.email = user_info.get("email") or user.email
        user.email_verified = user_info.get("email_verified", user.email_verified)

        # Merge roles from /userinfo namespace claim (may supplement JWT roles)
        roles_claim = settings.AUTH0_ROLES_NAMESPACE
        userinfo_roles = user_info.get(roles_claim, [])
        if isinstance(userinfo_roles, list) and userinfo_roles:
            merged = list({*user.roles, *userinfo_roles})
            user.roles = merged

        logger.info(f"Enriched user info from Auth0 for user: {user.id}, roles: {user.roles}")
    except Exception as e:
        logger.warning(f"Failed to enrich user from Auth0: {e}")
        # Partial data from JWT is acceptable — do not block the request
    return user



async def get_current_user_optional(
    authorization: Optional[str] = Header(None)
) -> Optional[User]:
    """
    Get current authenticated user from JWT token (optional).

    Returns None if no valid token provided.
    Use this for endpoints that work with or without authentication.

    Optimized flow:
      1. Validate JWT (local crypto — no network call)
      2. Build User from JWT claims
      3. Only call Auth0 /userinfo when essential fields are missing **and** the
         result is not already in the in-memory cache
    """
    if not settings.AUTH0_ENABLED or not authorization:
        return None

    try:
        if not authorization.startswith("Bearer "):
            return None

        token = authorization.replace("Bearer ", "")

        # Step 1: Validate JWT locally
        jwt_handler = get_jwt_handler(
            domain=settings.AUTH0_DOMAIN, audience=settings.AUTH0_AUDIENCE
        )
        payload = jwt_handler.verify_token(token)
        logger.debug(f"JWT payload keys: {list(payload.keys())}")

        # Step 2: Build user from JWT claims (free — no network)
        user = _build_user_from_jwt(payload)

        # Step 3: Enrich from Auth0 /userinfo only if needed (cached)
        if _user_needs_enrichment(user):
            user = await _enrich_user_from_auth0(user, token)

        # Step 4: Fetch roles from Management API if none found in JWT / userinfo
        #user = await _fetch_roles_if_missing(user)

        logger.debug(
            f"Authenticated user: {user.id}, email: {user.email}, "
            f"name: {user.name}, roles: {user.roles}"
        )
        return user

    except Exception as e:
        logger.warning(f"Token validation failed: {str(e)}")
        return None


async def get_current_user_required(
    authorization: Optional[str] = Header(None)
) -> User:
    """
    Get current authenticated user from JWT token (required).

    Raises 401 if no valid token provided.
    Use this for endpoints that require authentication.

    Optimized flow:
      1. Validate JWT (local crypto — no network call)
      2. Build User from JWT claims
      3. Only call Auth0 /userinfo when essential fields are missing **and** the
         result is not already in the in-memory cache
    """
    if not settings.AUTH0_ENABLED:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Authentication is not enabled",
        )

    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authorization header",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        logger.info("Authenticating request with JWT token")
        if not authorization.startswith("Bearer "):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authorization header format. Expected: Bearer <token>",
                headers={"WWW-Authenticate": "Bearer"},
            )

        token = authorization.replace("Bearer ", "")

        # Step 1: Validate JWT locally
        jwt_handler = get_jwt_handler(
            domain=settings.AUTH0_DOMAIN, audience=settings.AUTH0_AUDIENCE
        )
        payload = jwt_handler.verify_token(token)
        logger.info(f"JWT payload keys: {list(payload.keys())}")

        # Step 2: Build user from JWT claims (free — no network)
        user = _build_user_from_jwt(payload)

        # Step 3: Enrich from Auth0 /userinfo only if needed (cached)
        if _user_needs_enrichment(user):
            logger.info(f"User {user.id} needs enrichment from Auth0 /userinfo")
            user = await _enrich_user_from_auth0(user, token)

        # Step 4: Fetch roles from Management API if none found in JWT / userinfo
        #if not user.roles:
            # logger.info(f"User {user.id} has no roles from JWT or /userinfo; checking Management API")
            # user = await _fetch_roles_if_missing(user)

        logger.info(f"Authenticated user: {user.id}, email: {user.email}, name: {user.name}")
        return user

    except HTTPException:
        raise

    except Exception as e:
        logger.error(f"Token validation failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )


# ---------------------------------------------------------------------------
# Role-based authorization dependency factories
# ---------------------------------------------------------------------------

def require_role(role: str):
    """
    Dependency factory that enforces a single required role.

    Usage::

        @router.post("/admin/approve")
        async def approve(
            current_user: User = Depends(require_role("admin")),
        ): ...

    Raises 401 when no valid token is present, 403 when the role is missing.

    Args:
        role: The Auth0 role name the caller must have.

    Returns:
        A FastAPI dependency coroutine.
    """
    async def _dependency(
        authorization: Optional[str] = Header(None)
    ) -> User:
        user = await get_current_user_required(authorization)
        if not user.has_role(role):
            logger.warning(
                f"Access denied: user '{user.id}' missing required role '{role}'. "
                f"User roles: {user.roles}"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Required role '{role}' not assigned to this account.",
            )
        return user

    return _dependency


def require_any_role(*roles: str):
    """
    Dependency factory that requires the caller to have **at least one** of the
    listed roles.

    Usage::

        @router.get("/reports")
        async def reports(
            current_user: User = Depends(require_any_role("admin", "staff")),
        ): ...

    Raises 401 when no valid token is present, 403 when none of the roles match.

    Args:
        *roles: One or more role names; the user must possess at least one.

    Returns:
        A FastAPI dependency coroutine.
    """
    async def _dependency(
        authorization: Optional[str] = Header(None)
    ) -> User:
        user = await get_current_user_required(authorization)
        if not user.has_any_role(*roles):
            logger.warning(
                f"Access denied: user '{user.id}' has none of required roles {list(roles)}. "
                f"User roles: {user.roles}"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"One of the following roles is required: {', '.join(roles)}.",
            )
        return user

    return _dependency


# Convenience dependency aliases
OptionalUser = Depends(get_current_user_optional)
RequiredUser = Depends(get_current_user_required)
