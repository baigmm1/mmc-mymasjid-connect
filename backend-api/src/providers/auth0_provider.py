"""
Auth0 Provider for User Information Retrieval

Provides functionality to fetch user profile information from Auth0's userinfo endpoint.
Uses access tokens to retrieve authenticated user data.

Includes in-memory TTL caching to minimize Auth0 API calls and avoid 429 rate limits.
"""

from typing import Optional, Dict, Any, List
import asyncio
import hashlib
import time
import httpx
from src.core.logging import get_logger
from src.config import settings

logger = get_logger(__name__, level=settings.LOG_LEVEL)

# Default cache TTL: 5 minutes — user info rarely changes mid-session
_DEFAULT_CACHE_TTL = 300


class _UserInfoCache:
    """
    Simple in-memory TTL cache for Auth0 /userinfo responses.

    Keyed by a SHA-256 hash of the access token so raw tokens are never stored.
    Thread-safe via an asyncio Lock.
    """

    def __init__(self, ttl: int = _DEFAULT_CACHE_TTL, max_size: int = 500):
        self._ttl = ttl
        self._max_size = max_size
        self._store: Dict[str, tuple[float, Dict[str, Any]]] = {}
        self._lock = asyncio.Lock()

    @staticmethod
    def _hash_token(token: str) -> str:
        return hashlib.sha256(token.encode()).hexdigest()

    async def get(self, token: str) -> Optional[Dict[str, Any]]:
        key = self._hash_token(token)
        async with self._lock:
            entry = self._store.get(key)
            if entry is None:
                return None
            ts, data = entry
            if time.monotonic() - ts > self._ttl:
                del self._store[key]
                return None
            return data

    async def put(self, token: str, data: Dict[str, Any]) -> None:
        key = self._hash_token(token)
        async with self._lock:
            # Evict oldest entries if cache is full
            if len(self._store) >= self._max_size:
                oldest_key = min(self._store, key=lambda k: self._store[k][0])
                del self._store[oldest_key]
            self._store[key] = (time.monotonic(), data)

    async def invalidate(self, token: str) -> None:
        key = self._hash_token(token)
        async with self._lock:
            self._store.pop(key, None)

    async def clear(self) -> None:
        async with self._lock:
            self._store.clear()

    @property
    def size(self) -> int:
        return len(self._store)


class _RolesCache:
    """
    Simple in-memory TTL cache for Auth0 user roles.

    Keyed by the Auth0 user ID (``sub`` claim).  Roles change infrequently so
    we reuse the same TTL as the userinfo cache.
    Thread-safe via an asyncio Lock.
    """

    def __init__(self, ttl: int = _DEFAULT_CACHE_TTL, max_size: int = 500):
        self._ttl = ttl
        self._max_size = max_size
        self._store: Dict[str, tuple[float, List[str]]] = {}
        self._lock = asyncio.Lock()

    async def get(self, user_id: str) -> Optional[List[str]]:
        async with self._lock:
            entry = self._store.get(user_id)
            if entry is None:
                return None
            ts, roles = entry
            if time.monotonic() - ts > self._ttl:
                del self._store[user_id]
                return None
            return roles

    async def put(self, user_id: str, roles: List[str]) -> None:
        async with self._lock:
            if len(self._store) >= self._max_size:
                oldest_key = min(self._store, key=lambda k: self._store[k][0])
                del self._store[oldest_key]
            self._store[user_id] = (time.monotonic(), roles)

    async def invalidate(self, user_id: str) -> None:
        async with self._lock:
            self._store.pop(user_id, None)

    async def clear(self) -> None:
        async with self._lock:
            self._store.clear()

    @property
    def size(self) -> int:
        return len(self._store)


class Auth0Provider:
    """
    Auth0 provider for fetching user profile information.

    Features:
    - In-memory TTL cache for /userinfo responses (avoids 429 rate limits)
    - Shared httpx.AsyncClient for connection pooling
    - Automatic retry with back-off on 429 responses
    """

    def __init__(self, domain: str, cache_ttl: int = _DEFAULT_CACHE_TTL):
        """
        Initialize Auth0 Provider with the tenant domain.

        Args:
            domain: Auth0 tenant domain (e.g., masjidconnect.auth0.com)
            cache_ttl: How long (seconds) to cache /userinfo results (default 300s)
        """
        self.domain = domain
        self.userinfo_url = f"https://{domain}/userinfo"
        self._mgmt_api_base = f"https://{domain}/api/v2"
        self._cache = _UserInfoCache(ttl=cache_ttl)
        self._roles_cache = _RolesCache(ttl=cache_ttl)
        self._client: Optional[httpx.AsyncClient] = None
        self._rate_limited_until: float = 0  # monotonic timestamp

        # Management API token state (client-credentials grant, cached until near-expiry)
        self._mgmt_token: Optional[str] = None
        self._mgmt_token_expires_at: float = 0.0
        self._mgmt_token_lock = asyncio.Lock()

        logger.debug(f"Auth0Provider initialized with domain: {self.domain}, cache_ttl: {cache_ttl}s")

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create the shared httpx client (connection pooling)."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                timeout=10.0,
                limits=httpx.Limits(max_connections=10, max_keepalive_connections=5),
            )
        return self._client

    async def close(self) -> None:
        """Close the shared HTTP client. Call on application shutdown."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None

    async def get_user_info(self, access_token: str) -> Dict[str, Any]:
        """
        Fetch user information from Auth0 userinfo endpoint **with caching**.

        On the first call for a given token the result is fetched from Auth0
        and then cached for subsequent calls (default 5 min TTL).  If Auth0
        responds with 429 the provider waits using the Retry-After header and
        returns cached data when available.

        Args:
            access_token: Auth0 access token (Bearer token)

        Returns:
            Dictionary with user profile claims (sub, email, name, picture…)

        Raises:
            httpx.HTTPStatusError: If the API request fails (non-429)
            httpx.RequestError: Network error
            ValueError: Missing access token
        """
        if not access_token:
            raise ValueError("Access token is required")

        # ---- 1. Check cache first ----
        cached = await self._cache.get(access_token)
        if cached is not None:
            logger.debug(f"Auth0 userinfo cache HIT for user: {cached.get('sub', 'unknown')}")
            return cached

        # ---- 2. Rate-limit guard ----
        now = time.monotonic()
        if now < self._rate_limited_until:
            wait = self._rate_limited_until - now
            logger.warning(
                f"Auth0 rate-limited — backing off {wait:.1f}s. No cached data available."
            )
            raise httpx.HTTPStatusError(
                "Rate limited by Auth0 (429)",
                request=httpx.Request("GET", self.userinfo_url),
                response=httpx.Response(429),
            )

        # ---- 3. Fetch from Auth0 with retry ----
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }

        max_retries = 2
        client = await self._get_client()

        for attempt in range(max_retries + 1):
            try:
                logger.debug(f"Fetching user info from Auth0 (attempt {attempt + 1})")
                response = await client.get(self.userinfo_url, headers=headers)

                if response.status_code == 429:
                    retry_after = int(response.headers.get("Retry-After", "5"))
                    self._rate_limited_until = time.monotonic() + retry_after
                    logger.warning(
                        f"Auth0 returned 429 — will back off for {retry_after}s "
                        f"(attempt {attempt + 1}/{max_retries + 1})"
                    )
                    if attempt < max_retries:
                        await asyncio.sleep(min(retry_after, 3))
                        continue
                    # Final attempt failed — raise
                    response.raise_for_status()

                response.raise_for_status()

                user_info = response.json()
                # get the claims from token
                #logger.info(f"cached data {cached.get('https://api.mymasjidconnect.org/roles', []) if cached else '[]'}")
                #logger.info(f"user info {user_info} fetched from url {self.userinfo_url}")
                # Store in cache
                await self._cache.put(access_token, user_info)

                logger.info(
                    f"Auth0 userinfo fetched & cached for user: {user_info.get('sub', 'unknown')}"
                )
                logger.debug(f"User info keys: {list(user_info.keys())}")
                return user_info

            except httpx.HTTPStatusError:
                raise
            except httpx.RequestError as e:
                logger.error(f"Network error fetching user info: {str(e)}")
                raise
            except Exception as e:
                logger.error(f"Unexpected error fetching user info: {str(e)}")
                raise

        # Should not reach here, but satisfy type checker
        raise RuntimeError("Exhausted retries fetching Auth0 user info")

    async def _get_management_token(self) -> str:
        """
        Obtain a cached Management API access token via client-credentials grant.

        The token is re-fetched automatically when it is missing or within
        60 seconds of expiry.

        Requires:
            - ``AUTH0_MGMT_CLIENT_ID``  — client ID of a Machine-to-Machine app
            - ``AUTH0_MGMT_CLIENT_SECRET`` — its secret

        The M2M app must be authorised for the Management API with at least
        the ``read:users`` and ``read:role_members`` scopes in the Auth0 dashboard.
        Do **not** use the SPA application credentials — those do not support the
        client_credentials grant and will receive a 403 Forbidden response.

        Returns:
            A valid Management API Bearer token.

        Raises:
            ValueError: If M2M credentials are not configured.
            httpx.HTTPStatusError: If Auth0 returns a non-2xx response.
        """
        async with self._mgmt_token_lock:
            now = time.monotonic()
            if self._mgmt_token and now < self._mgmt_token_expires_at:
                logger.debug("Auth0 Management API token cache HIT")
                return self._mgmt_token

            client_id = settings.AUTH0_MGMT_CLIENT_ID
            client_secret = settings.AUTH0_MGMT_CLIENT_SECRET
            if not client_id or not client_secret:
                raise ValueError(
                    "AUTH0_MGMT_CLIENT_ID and AUTH0_MGMT_CLIENT_SECRET must be set to fetch "
                    "user roles from the Management API. Create a Machine-to-Machine application "
                    "in the Auth0 dashboard, authorise it for the Management API with "
                    "read:users and read:role_members scopes, then set these two env vars. "
                    "Do NOT use the SPA application's AUTH0_CLIENT_ID/SECRET — those do not "
                    "support the client_credentials grant."
                )

            token_url = f"https://{self.domain}/oauth/token"
            payload = {
                "grant_type": "client_credentials",
                "client_id": client_id,
                "client_secret": client_secret,
                "audience": f"https://{self.domain}/api/v2/",
            }

            client = await self._get_client()
            try:
                response = await client.post(token_url, json=payload)
                if response.status_code == 403:
                    body = response.text
                    raise ValueError(
                        f"Auth0 Management API token request returned 403 Forbidden. "
                        f"This means the M2M application is not authorised for the Management API. "
                        f"In the Auth0 dashboard go to Applications → APIs → Auth0 Management API "
                        f"and add the Machine-to-Machine application with read:users and "
                        f"read:role_members scopes. Response body: {body}"
                    )
                response.raise_for_status()
            except httpx.HTTPStatusError as e:
                logger.error(
                    f"Failed to obtain Management API token (HTTP {e.response.status_code}). "
                    f"Ensure AUTH0_MGMT_CLIENT_ID/SECRET are from a Machine-to-Machine app "
                    f"authorised for the Management API: {e}"
                )
                raise

            data = response.json()
            self._mgmt_token = data["access_token"]
            # Cache until 60 s before the actual expiry (default Auth0 TTL is 86 400 s)
            self._mgmt_token_expires_at = now + data.get("expires_in", 86400) - 60

            logger.debug(
                f"Auth0 Management API token obtained; "
                f"expires in ~{data.get('expires_in', 86400)}s"
            )
            return self._mgmt_token  # type: ignore[return-value]

    async def get_user_roles(self, user_id: str) -> List[str]:
        """
        Fetch the roles assigned to a user via the Management API **with caching**.

        Calls ``GET /api/v2/users/{user_id}/roles``.  A Management API token is
        obtained automatically via the client-credentials grant and is itself
        cached until near-expiry.

        Args:
            user_id: Auth0 user identifier (the ``sub`` JWT claim, e.g.
                     ``"auth0|abc123"`` or ``"google-oauth2|xyz"``).  The value
                     is URL-encoded before being used in the path.

        Returns:
            List of role name strings assigned to the user.
            Returns an empty list (and logs a warning) if the call fails.

        Raises:
            httpx.HTTPStatusError: If the Management API returns a non-2xx status.
            ValueError: If Management API credentials are not configured.
        """
        # ---- 1. Roles cache ----
        cached_roles = await self._roles_cache.get(user_id)
        if cached_roles is not None:
            logger.debug(
                f"Auth0 roles cache HIT for user: {user_id} — roles: {cached_roles}"
            )
            return cached_roles

        # ---- 2. Fetch via Management API ----
        from urllib.parse import quote
        encoded_user_id = quote(user_id, safe="")
        roles_url = f"{self._mgmt_api_base}/users/{encoded_user_id}/roles"

        mgmt_token = await self._get_management_token()
        logger.info(f"Fetching Auth0 roles for user: {user_id} via Management API {mgmt_token[:10]}...")
        headers = {"Authorization": f"Bearer {mgmt_token}"}

        client = await self._get_client()
        response = await client.get(roles_url, headers=headers)
        response.raise_for_status()

        roles_data = response.json()
        roles: List[str] = [
            r["name"] for r in roles_data if isinstance(r, dict) and "name" in r
        ]

        await self._roles_cache.put(user_id, roles)
        logger.info(
            f"Auth0 roles fetched & cached for user: {user_id} — roles: {roles}"
        )
        return roles

    async def invalidate_roles_cache(self, user_id: str) -> None:
        """Invalidate cached roles for a specific user (e.g. after role assignment)."""
        await self._roles_cache.invalidate(user_id)

    async def get_user_email(self, access_token: str) -> Optional[str]:
        """
        Convenience method to fetch only the user's email address.

        Args:
            access_token: Auth0 access token

        Returns:
            User's email address or None if not available
        """
        try:
            user_info = await self.get_user_info(access_token)
            return user_info.get("email")
        except Exception as e:
            logger.error(f"Failed to get user email: {str(e)}")
            return None

    async def get_user_profile(self, access_token: str) -> Dict[str, Optional[str]]:
        """
        Fetch basic user profile information (id, email, name).

        Args:
            access_token: Auth0 access token

        Returns:
            Dictionary with user_id, email, name, email_verified, picture, updated_at, and roles fields
        """
        try:
            user_info = await self.get_user_info(access_token)
            return {
                "user_id": user_info.get("sub"),
                "email": user_info.get("email"),
                "name": user_info.get("name"),
                "email_verified": user_info.get("email_verified", False),
                "picture": user_info.get("picture"),
                "updated_at": user_info.get("updated_at"),                
            }
        except Exception as e:
            logger.error(f"Failed to get user profile: {str(e)}")
            raise

    async def invalidate_cache(self, access_token: str) -> None:
        """Invalidate cached user info for a specific token."""
        await self._cache.invalidate(access_token)

    async def clear_cache(self) -> None:
        """Clear the entire user info cache and the roles cache."""
        await self._cache.clear()
        await self._roles_cache.clear()

    @property
    def cache_size(self) -> int:
        """Current number of cached user info entries."""
        return self._cache.size

    @property
    def roles_cache_size(self) -> int:
        """Current number of cached user roles entries."""
        return self._roles_cache.size


# ---------------------------------------------------------------------------
# Singleton instance
# ---------------------------------------------------------------------------
_auth0_provider_instance: Optional[Auth0Provider] = None


def get_auth0_provider() -> Auth0Provider:
    """
    Get the singleton Auth0Provider instance.

    Uses the domain from application settings. Creates the instance on first
    call and reuses it thereafter (connection pooling + cache preserved).

    Returns:
        Configured Auth0Provider singleton

    Raises:
        ValueError: If AUTH0_DOMAIN is not configured
    """
    global _auth0_provider_instance

    if _auth0_provider_instance is None:
        if not settings.AUTH0_DOMAIN:
            raise ValueError("AUTH0_DOMAIN must be configured in settings")
        _auth0_provider_instance = Auth0Provider(domain=settings.AUTH0_DOMAIN)

    return _auth0_provider_instance


async def shutdown_auth0_provider() -> None:
    """Close the Auth0 provider's HTTP client. Call on app shutdown."""
    global _auth0_provider_instance
    if _auth0_provider_instance is not None:
        await _auth0_provider_instance.close()
        _auth0_provider_instance = None
