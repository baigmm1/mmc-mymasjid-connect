"""
Build version endpoint for retrieving application build information.

Provides build number, version strings, and timestamp information
for deployment tracking and versioning.

Endpoint: GET /api/v1/build
Returns: BuildInfo with build number, date, timestamp, and version strings
"""

from fastapi import APIRouter, status as http_status

from src.core.build_manager import get_build_manager
from src.models.build import BuildInfo

router = APIRouter(tags=["build"])


@router.get(
    "/build",
    response_model=BuildInfo,
    status_code=http_status.HTTP_200_OK,
    summary="Get build version information",
    description="""
    Retrieve current build version information including:
    - Sequential build number (auto-incremented)
    - Build creation date and timestamp
    - Semantic version string (YYYY.MM.BUILD)
    - Full version string with date
    
    This endpoint is useful for:
    - Deployment verification
    - Version tracking
    - Build identification
    - CI/CD pipeline integration
    """,
    responses={
        200: {
            "description": "Build information retrieved successfully",
            "model": BuildInfo,
        }
    },
)
async def get_build_info() -> BuildInfo:
    """
    Get current build information.
    
    Returns build number, date, timestamp, and version strings.
    The build number auto-increments with each deployment.
    
    Returns:
        BuildInfo: Current build information
        
    Example:
        GET /api/v1/build
        Response 200:
        {
            "build_number": 42,
            "build_date": "2025-12-17",
            "build_timestamp": 1734451200,
            "version": "2025.12.42",
            "full_version": "2025.12.42-20251217"
        }
    """
    build_manager = get_build_manager()
    build_info = build_manager.get_current_build()
    
    return BuildInfo(**build_info)


@router.post(
    "/build/increment",
    response_model=BuildInfo,
    status_code=http_status.HTTP_200_OK,
    summary="Increment build number",
    description="""
    Manually increment the build number and update version information.
    
    This endpoint is typically called by:
    - CI/CD pipelines during deployment
    - Automated build scripts
    - Manual deployment processes
    
    Note: This should be restricted in production environments.
    """,
    responses={
        200: {
            "description": "Build number incremented successfully",
            "model": BuildInfo,
        }
    },
)
async def increment_build() -> BuildInfo:
    """
    Increment build number.
    
    Increases the build number by 1 and updates all version strings
    with current timestamp. This persists to the build info file.
    
    Returns:
        BuildInfo: Updated build information
        
    Example:
        POST /api/v1/build/increment
        Response 200:
        {
            "build_number": 43,
            "build_date": "2025-12-17",
            "build_timestamp": 1734451260,
            "version": "2025.12.43",
            "full_version": "2025.12.43-20251217"
        }
    """
    build_manager = get_build_manager()
    build_info = build_manager.increment_build()
    
    return BuildInfo(**build_info)
