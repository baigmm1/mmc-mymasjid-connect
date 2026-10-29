"""
Build version models for API versioning and deployment tracking.

This module defines the schema for build version information including
build number, timestamp, and version string formatting.
"""

from datetime import datetime
from pydantic import BaseModel, Field


class BuildInfo(BaseModel):
    """
    Build information response model.
    
    Attributes:
        build_number: Sequential build number (auto-incremented)
        build_date: ISO 8601 formatted date when build was created
        build_timestamp: Unix timestamp when build was created
        version: Semantic version string (YYYY.MM.BUILD_NUMBER)
        full_version: Complete version string with date and build number
    """
    
    build_number: int = Field(..., description="Sequential build number", ge=1)
    build_date: str = Field(..., description="Build creation date (YYYY-MM-DD)")
    build_timestamp: int = Field(..., description="Unix timestamp of build creation")
    version: str = Field(..., description="Semantic version (YYYY.MM.BUILD)", pattern=r"^\d{4}\.\d{2}\.\d+$")
    full_version: str = Field(..., description="Full version string with date and build")
    
    class Config:
        """Pydantic model configuration."""
        json_schema_extra = {
            "example": {
                "build_number": 42,
                "build_date": "2025-12-17",
                "build_timestamp": 1734451200,
                "version": "2025.12.42",
                "full_version": "2025.12.42-20251217"
            }
        }
