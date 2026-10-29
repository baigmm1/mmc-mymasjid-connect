
"""Configuration management for Masjid Connect application.

Loads settings from environment variables with sensible defaults.
Supports different configurations for development, testing, and production environments.

Environment Variables:
    ENVIRONMENT: deployment environment (development, testing, production)
    DEBUG: enable debug mode (true/false)
    API_VERSION: API version for versioned endpoints (v1, v2, etc.)
    LOG_LEVEL: logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    HOST: server host address (default: 0.0.0.0)
    PORT: server port (default: 8000)
"""

import json
import os
from typing import Literal, Optional, Union

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.

    All settings have sensible defaults for development but can be overridden
    via environment variables for different deployment environments.
    """

    # Application Settings
    APP_NAME: str = Field(default="Masjid Connect API", description="Application name")
    
    ENVIRONMENT: Literal["development", "testing", "production"] = Field(
        default="development", description="Deployment environment"
    )
    DEBUG: bool = Field(default=True, description="Enable debug mode")
    API_VERSION: str = Field(default="v1", description="API version")

    # Logging Settings
    LOG_LEVEL: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field(
        default="INFO", description="Logging level"
    )

    SEND_EMAILS: bool = Field(
        default=False, description="Enable sending emails via email provider"
    )
    EMAIL_TEMPLATE_PATH: str = Field(
        default="src/data/templates/", description="Path to email templates"
    )

    # Server Settings
    HOST: str = Field(default="0.0.0.0", description="Server host")
    PORT: int = Field(default=8000, description="Server port")

    # API Settings    
    API_TITLE: str = Field(default="Masjid Connect API Service", description="My Masjid Connect API Service")
    API_DESCRIPTION: str = Field(
        default="Application API Service", description="API description"
    )

    # Security Settings
    CORS_ORIGINS: Union[str, list] = Field(
        default=["http://localhost:3000", "http://localhost:8000", "http://localhost:5173"],
        description="CORS allowed origins (JSON string or list)",
    )
    CORS_ALLOW_CREDENTIALS: bool = Field(
        default=True, description="Allow cookies in CORS requests"
    )
    CORS_ALLOW_METHODS: Union[str, list] = Field(
        default=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
        description="CORS allowed methods (JSON string or list)",
    )
    CORS_ALLOW_HEADERS: Union[str, list] = Field(
        default=["Content-Type", "Authorization", "X-Requested-With", "Accept", "Origin", "X-Correlation-ID"],
        description="CORS allowed headers (JSON string or list)"
    )
    CORS_EXPOSE_HEADERS: Union[str, list] = Field(
        default=["X-Correlation-ID"],
        description="CORS exposed headers (JSON string or list)"
    )

    @field_validator("CORS_ORIGINS", "CORS_ALLOW_METHODS", "CORS_ALLOW_HEADERS", "CORS_EXPOSE_HEADERS", mode="before")
    @classmethod
    def parse_json_list(cls, v, info):
        """Parse JSON string to list for Azure environment variables.
        
        Azure App Service environment variables are strings, so list values
        need to be provided as JSON strings like: ["item1", "item2"]
        This prevents pydantic-settings from auto-parsing and failing.
        
        Special handling for CORS_ALLOW_HEADERS:
        - If value is ["*"], convert to list ["*"] for FastAPI CORSMiddleware
        - FastAPI expects ["*"] not just "*" for wildcard headers
        
        Args:
            v: Value from environment variable (string or list)
            info: Field validation info containing field name
            
        Returns:
            Parsed list
            
        Examples:
            '["http://localhost:3000"]' -> ["http://localhost:3000"]
            '[]' -> []
            "" -> []  (empty string becomes empty list)
            '["*"]' -> ["*"]  (wildcard as list)
            ["already", "a", "list"] -> ["already", "a", "list"]
        """
        if isinstance(v, str):
            # Handle empty string
            v = v.strip()
            if not v:
                return []
            
            try:
                parsed = json.loads(v)
                if isinstance(parsed, list):
                    # Ensure wildcard is properly handled for CORS headers
                    if info.field_name == "CORS_ALLOW_HEADERS" and parsed == ["*"]:
                        return ["*"]
                    return parsed
                # If it's not a list after parsing, return as single-item list
                return [parsed]
            except json.JSONDecodeError as e:
                # If JSON parsing fails, treat as comma-separated string
                if "," in v:
                    return [item.strip() for item in v.split(",") if item.strip()]
                # Single value, not JSON - special case for wildcard
                if v == "*":
                    return ["*"]
                return [v] if v else []
        
        # Already a list - validate wildcard for CORS headers
        if isinstance(v, list):
            if info.field_name == "CORS_ALLOW_HEADERS" and v == ["*"]:
                return ["*"]
            return v
        
        return []

    # Auth0 Settings
    AUTH0_DOMAIN: Optional[str] = Field(
        default=None,
        description="Auth0 tenant domain (e.g., masjidconnect.prod-us-1.auth0.com)"
    )
    AUTH0_AUDIENCE: Optional[str] = Field(
        default=None,
        description="Auth0 API identifier/audience for JWT validation"
    )
    AUTH0_CLIENT_ID: Optional[str] = Field(
        default=None,
        description="Auth0 application client ID"
    )
    AUTH0_CLIENT_SECRET: Optional[str] = Field(
        default=None,
        description="Auth0 application client secret (for backend operations)"
    )
    AUTH0_MGMT_CLIENT_ID: Optional[str] = Field(
        default=None,
        description=(
            "Client ID of the Auth0 Machine-to-Machine application authorised for the "
            "Management API (read:users, read:role_members scopes). "
            "This is DIFFERENT from AUTH0_CLIENT_ID which is the SPA app."
        )
    )
    AUTH0_MGMT_CLIENT_SECRET: Optional[str] = Field(
        default=None,
        description=(
            "Client secret of the Auth0 Machine-to-Machine application authorised for the "
            "Management API. This is DIFFERENT from AUTH0_CLIENT_SECRET which is the SPA app."
        )
    )
    AUTH0_ENABLED: bool = Field(
        default=False,
        description="Enable Auth0 authentication"
    )
    AUTH0_ROLES_NAMESPACE: str = Field(
        default="https://masjidconnect.auth0.com/roles",
        description="Namespace claim key used in the JWT for Auth0 roles (set via Auth0 Action/Rule)"
    )

    # Database Settings
    DB_CONNECTION_STRING: Optional[str] = Field(
        default=None,
        description="Direct SQL Server connection string (development only)"
    )
    DB_SERVER: str = Field(
        default="localhost",
        description="SQL Database server name (e.g., server.database.windows.net)"
    )
    DB_NAME: str = Field(
        default="masjiddb",
        description="Database name"
    )
    DB_IDENTITY_CLIENT_ID: Optional[str] = Field(
        default=None,
        description="User-assigned managed identity client ID (optional)"
    )
    
    DB_IDENTITY_OBJECT_ID: Optional[str] = Field(
        default=None,
        description="User-assigned managed identity client ID (optional)"
    )

    # Database Connection Pool Settings
    DB_POOL_SIZE: int = Field(
        default=10,
        description="Connection pool minimum size"
    )
    DB_MAX_OVERFLOW: int = Field(
        default=10,
        description="Maximum additional connections beyond pool_size"
    )
    DB_POOL_RECYCLE: int = Field(
        default=300,
        description="Recycle connections after N seconds"
    )
    DB_CONNECT_TIMEOUT: int = Field(
        default=30,
        description="Connection timeout in seconds"
    )
    DB_ECHO_SQL: bool = Field(
        default=False,
        description="Log all SQL statements (for debugging)"
    )

    # Cache Settings
    CACHE_REFRESH_INTERVAL: int = Field(
        default=21600,  # 6 hours
        description="Interval in seconds between automatic cache refreshes (default: 6 hours)"
    )

    AZURE_TENANT_ID: Optional[str] = Field(
        default=None,
        description="Azure Tenant ID for managed identity authentication (optional)"
    )

    # SendGrid Email Settings    
    SENDGRID_FROM_EMAIL: Optional[str] = Field(
        default=None,
        description="Default sender email address for SendGrid emails"
    )
    SENDGRID_FROM_NAME: Optional[str] = Field(
        default="Masjid Connect",
        description="Default sender name for SendGrid emails"
    )
    
    # Stripe Settings
    STRIPE_SECRET_KEY: Optional[str] = Field(
        default=None,
        description="Stripe secret key for API authentication"
    )
    STRIPE_PUBLISHABLE_KEY: Optional[str] = Field(
        default=None,
        description="Stripe publishable key for frontend integration"
    )
    STRIPE_WEBHOOK_SECRET: Optional[str] = Field(
        default=None,
        description="Stripe webhook endpoint secret for signature verification"
    )
    STRIPE_API_VERSION: str = Field(
        default="2023-10-16",
        description="Stripe API version to use"
    )
    STRIPE_API_BASE_URL: str = Field(
        default="https://api.stripe.com/v1",
        description="Base URL for Stripe API (for HTTP provider)"
    )

    # ---------------------------------------------------------------------------
    # Wix Events Settings
    # ---------------------------------------------------------------------------
    # WIX_API_KEY: Optional[str] = Field(
    #     default=None,
    #     description="Wix API key for authenticating with the Wix Events API"
    # )
    # WIX_SITE_ID: Optional[str] = Field(
    #     default=None,
    #     description="Wix site ID (account-level site identifier)"
    # )
    WIX_API_BASE_URL: str = Field(
        default="https://www.wixapis.com/wix-events/v1",
        description="Base URL for the Wix Events v1 REST API"
    )

    class Config:
        """Pydantic configuration."""
        
        # Only load .env file in non-production environments
        # In production (Azure), environment variables take precedence
        env_file = ".env" if os.getenv("ENVIRONMENT", "development") != "production" else None
        case_sensitive = True
        # Ensure environment variables override .env file values
        env_file_encoding = "utf-8"


def get_settings() -> Settings:
    """
    Get application settings instance.

    Reads from .env file in development/testing and environment variables in production.
    Environment variables always take precedence over .env file values.

    Returns:
        Settings instance with all configuration
    """
    return Settings()


# Create global settings instance
settings = get_settings()
