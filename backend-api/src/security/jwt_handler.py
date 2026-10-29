"""
JWT Authentication Handler

Validates Auth0 JWT tokens and extracts user information
Uses JSON Web Key Set (JWKS) for token verification
"""

import jwt
from jwt import PyJWKClient
from typing import Dict, Optional
from functools import lru_cache
import logging

logger = logging.getLogger(__name__)


class JWTHandler:
    """
    Handles JWT token validation for Auth0 tokens
    """

    def __init__(self, domain: str, audience: str, algorithms: list[str] = None):
        """
        Initialize JWT Handler

        Args:
            domain: Auth0 tenant domain (e.g., "masjidconnect.prod-us-1.auth0.com")
            audience: API identifier configured in Auth0
            algorithms: Allowed signing algorithms (default: ["RS256"])
        """
        self.domain = domain
        self.audience = audience
        self.algorithms = algorithms or ["RS256"]
        self.jwks_url = f"https://{domain}/.well-known/jwks.json"
        self.issuer = f"https://{domain}/"

        # Initialize JWKS client (caches keys)
        self.jwks_client = PyJWKClient(self.jwks_url)

    def verify_token(self, token: str) -> Dict:
        """
        Verify and decode JWT token

        Args:
            token: JWT token string

        Returns:
            Dict containing token payload/claims

        Raises:
            jwt.ExpiredSignatureError: Token has expired
            jwt.InvalidTokenError: Token is invalid
            jwt.InvalidAudienceError: Token audience doesn't match
            jwt.InvalidIssuerError: Token issuer doesn't match
        """
        try:
            # Get signing key from JWKS
            signing_key = self.jwks_client.get_signing_key_from_jwt(token)

            # Decode and verify token
            payload = jwt.decode(
                token,
                signing_key.key,
                algorithms=self.algorithms,
                audience=self.audience,
                issuer=self.issuer,
            )

            logger.debug(f"Token verified successfully for user: {payload.get('sub')}")
            return payload

        except jwt.ExpiredSignatureError as e:
            logger.warning(f"Token expired: {str(e)}")
            raise

        except jwt.InvalidTokenError as e:
            logger.warning(f"Invalid token: {str(e)}")
            raise

        except Exception as e:
            logger.error(f"Error verifying token: {str(e)}")
            raise jwt.InvalidTokenError(f"Token verification failed: {str(e)}")

    def get_user_id(self, token: str) -> Optional[str]:
        """
        Extract user ID from token

        Args:
            token: JWT token string

        Returns:
            User ID (sub claim) or None if invalid
        """
        try:
            payload = self.verify_token(token)
            return payload.get("sub")
        except Exception as e:
            logger.error(f"Failed to extract user ID: {str(e)}")
            return None

    def get_user_email(self, token: str) -> Optional[str]:
        """
        Extract user email from token

        Args:
            token: JWT token string

        Returns:
            User email or None if not present/invalid
        """
        try:
            payload = self.verify_token(token)
            return payload.get("email")
        except Exception as e:
            logger.error(f"Failed to extract user email: {str(e)}")
            return None

    def decode_token_without_verification(self, token: str) -> Dict:
        """
        Decode token without verification (for debugging only)

        Args:
            token: JWT token string

        Returns:
            Dict containing token payload

        Warning:
            DO NOT use this in production for authentication decisions
        """
        return jwt.decode(token, options={"verify_signature": False})


@lru_cache()
def get_jwt_handler(domain: str, audience: str) -> JWTHandler:
    """
    Get cached JWT handler instance

    Args:
        domain: Auth0 domain
        audience: API audience

    Returns:
        JWTHandler instance
    """
    return JWTHandler(domain=domain, audience=audience)
