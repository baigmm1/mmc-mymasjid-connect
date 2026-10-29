"""
Auth endpoints for identity and role information.

Provides the /auth/me endpoint that returns the authenticated user's identity
and the Auth0 roles assigned to them.  Roles are extracted from the JWT
custom-namespace claim and can be used by clients to adapt UI behaviour and
restrict feature access.

Endpoints:
    GET /api/v1/auth/me - Return current user identity and roles
"""

from fastapi import APIRouter, Depends
import fastapi

from src.config import settings
from src.core.dependencies import User, get_current_user_required
from src.core.logging import get_logger
from src.models.user import UserMeResponse

router = APIRouter(prefix="/auth", tags=["auth"])
logger = get_logger(__name__, level=settings.LOG_LEVEL)


@router.get(
    "/me",
    response_model=UserMeResponse,
    status_code=200,
    summary="Get current user identity and roles",
    description=(
        "Returns the authenticated user's identity and the Auth0 roles assigned "
        "to their account. Roles are read from the JWT custom-namespace claim "
        "(set by an Auth0 Action or Rule) and can be used by clients to provide "
        "different capabilities based on the user's assigned roles.\n\n"
        "**Requires**: `Authorization: Bearer <token>` header."
    ),
    responses={
        200: {"description": "Authenticated user identity and roles"},
        401: {"description": "Missing or invalid access token"},
    },
)
async def get_me(
    current_user: User = Depends(get_current_user_required),        
) -> UserMeResponse:
    """
    Return the current authenticated user's identity and assigned roles.

    Roles are populated from the Auth0 JWT custom-namespace claim.  If an
    Auth0 Action/Rule has not yet been configured to include roles in the
    token, the ``roles`` list will be empty.

    Args:
        current_user: Injected authenticated user (from JWT + optional /userinfo enrichment).

    Returns:
        UserMeResponse: User identity including id, email, name, picture, and roles.

    Example::

        GET /api/v1/auth/me
        Authorization: Bearer eyJhbGci...

        Response 200:
        {
            "id": "auth0|abc123",
            "email": "user@example.com",
            "email_verified": true,
            "name": "Jane Smith",
            "first_name": "Jane",
            "last_name": "Smith",
            "nick_name": null,
            "picture": "https://cdn.auth0.com/avatars/js.png",
            "roles": ["admin", "staff"]
        }
    """
    logger.info(
        "User identity requested",
        extra={"user_id": current_user.id, "roles": current_user.roles},
    )
    # logger.info(f"Authorization header: {fastapi_request.headers.get('Authorization', '')}")
    # user = await get_current_user_required(fastapi_request.headers.get("Authorization", ""))
    # logger.info(f"user {user} requested identity info")
    return UserMeResponse(
        id=current_user.id,
        email=current_user.email,
        email_verified=current_user.email_verified,
        name=current_user.name,
        first_name=current_user.first_name,
        last_name=current_user.last_name,
        nick_name=current_user.nick_name,
        picture=current_user.picture,
        roles=current_user.roles,
    )
