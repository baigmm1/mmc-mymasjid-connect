"""
Main FastAPI application factory.

Creates and configures the FastAPI application with all middleware,
exception handlers, and route registration. This is the entry point
for the ASGI server (Uvicorn).

Usage:
    uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload
"""

import sys
import traceback
from contextlib import asynccontextmanager

try:
    from fastapi import FastAPI
    from fastapi.middleware.cors import CORSMiddleware

    from src.api.v1.endpoints import auth, build, cache, company, community, donationtype, health, masterdata, donationtypekiosk, servicetypekiosk,  transaction, provider_configuration, donors_review, donors, dashboard, prayer_times, documents, webhooks, bank_deposit_batch, pledges
    from src.config import settings
    from src.core.cache_manager import (
        initialize_caches,
        warm_all_caches,
        clear_all_caches,
        start_background_cache_refresh,
        stop_background_cache_refresh,
    )
    from src.core.exceptions import MasjidConnectException
    from src.core.logging import get_logger
    from src.core.middleware import (
        CorrelationIdMiddleware,
        ErrorHandlerMiddleware,
        SecurityHeadersMiddleware,
    )
    from src.providers.auth0_provider import shutdown_auth0_provider
    from src.database import get_session
    from src.models.error import ErrorResponse
    
    print("All imports successful!", file=sys.stderr)
    
except Exception as e:
    print(f"CRITICAL ERROR: Failed to import required modules: {e}", file=sys.stderr)
    traceback.print_exc(file=sys.stderr)
    sys.exit(1)


def create_app() -> FastAPI:
    """
    Create and configure FastAPI application.

    Configures:
    - Middleware for correlation IDs, error handling, and security headers
    - Exception handlers for standardized error responses
    - CORS for cross-origin requests
    - OpenAPI documentation

    Returns:
        Configured FastAPI application
    """
    app = FastAPI(
        title=settings.API_TITLE,
        description=settings.API_DESCRIPTION,
        version=settings.API_VERSION,
        debug=settings.DEBUG,
    )

    # Add middleware in reverse order (first added is last executed)
    # CORS must be added first so it's executed last (wraps all other middleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=settings.CORS_ALLOW_CREDENTIALS,
        allow_methods=settings.CORS_ALLOW_METHODS,
        allow_headers=settings.CORS_ALLOW_HEADERS,
        expose_headers=settings.CORS_EXPOSE_HEADERS,
    )
    
    # Add other middleware after CORS
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(ErrorHandlerMiddleware)
    app.add_middleware(CorrelationIdMiddleware)

    # Register API routes
    app.include_router(auth.router, prefix="/api/v1")
    app.include_router(health.router, prefix="/api/v1")
    app.include_router(build.router, prefix="/api/v1")
    app.include_router(cache.router, prefix="/api/v1")
    app.include_router(masterdata.router, prefix="/api/v1")
    app.include_router(company.router, prefix="/api/v1")
    app.include_router(donationtype.router, prefix="/api/v1")
    app.include_router(donationtypekiosk.router, prefix="/api/v1")
    app.include_router(servicetypekiosk.router, prefix="/api/v1")
    app.include_router(transaction.router, prefix="/api/v1")
    app.include_router(provider_configuration.router, prefix="/api/v1")
    app.include_router(donors_review.router, prefix="/api/v1")
    app.include_router(donors.router, prefix="/api/v1")
    app.include_router(dashboard.router, prefix="/api/v1")
    app.include_router(prayer_times.router, prefix="/api/v1")
    app.include_router(documents.router, prefix="/api/v1")
    app.include_router(webhooks.router, prefix="/api/v1")
    app.include_router(bank_deposit_batch.router, prefix="/api/v1")
    app.include_router(community.router, prefix="/api/v1")
    app.include_router(pledges.router, prefix="/api/v1")

    # Get logger
    logger = get_logger(__name__, level=settings.LOG_LEVEL)

    # Exception handler for MasjidConnectException
    @app.exception_handler(MasjidConnectException)
    async def masjidconnect_exception_handler(request, exc: MasjidConnectException):
        """Handle Masjid Connect exceptions and return standardized error response."""
        from datetime import datetime

        from fastapi.responses import JSONResponse

        from src.core.logging import CorrelationIdFilter

        correlation_id = CorrelationIdFilter.get_correlation_id() or "unknown"

        error_response = ErrorResponse(
            detail=exc.detail,
            error_code=exc.error_code,
            timestamp=datetime.utcnow(),
            correlation_id=correlation_id,
            errors=exc.errors,
        )
        logger.error(
            f"MasjidConnectException: {exc.error_code}",
            extra={"error_code": exc.error_code, "status_code": exc.status_code},
        )
        return JSONResponse(
            status_code=exc.status_code, content=error_response.model_dump()
        )

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        """Lifespan context manager for startup and shutdown events."""
        # Startup
        logger = get_logger(__name__, level=settings.LOG_LEVEL)
        
        try:
            logger.info("=" * 60)
            logger.info(f"Starting Masjid Connect API v{settings.API_VERSION}")
            logger.info(f"Environment: {settings.ENVIRONMENT}")
            logger.info(f"Debug mode: {settings.DEBUG}")
            logger.info(f"Listening on {settings.HOST}:{settings.PORT}")
            logger.info(f"Database server: {settings.DB_SERVER}")
            logger.info(f"Database name: {settings.DB_NAME}")
            logger.info("=" * 60)

            # Initialize caches
            logger.info("Initializing caches...")
            initialize_caches(
                company_ttl=86400,  # 24 hours
                donation_type_ttl=86400,  # 24 hours
                kiosk_donation_type_ttl=86400,  # 24 hours
                kiosk_service_type_ttl=86400,  # 24 hours
            )
            logger.info("Caches initialized successfully")

            # Warm caches with database data
            try:
                logger.info("Warming caches from database...")
                async for session in get_session():
                    cache_stats = await warm_all_caches(session)
                    logger.info(f"Cache warming completed: {cache_stats}")
                    break  # Only need one session
                
                # Start background cache refresh task (refresh every 6 hours, well before 24-hour TTL)
                logger.info(f"Starting background cache refresh task (interval: {settings.CACHE_REFRESH_INTERVAL}s)...")
                await start_background_cache_refresh(refresh_interval=settings.CACHE_REFRESH_INTERVAL)
                logger.info("Background cache refresh task started successfully")
                
                logger.info("Application startup completed successfully!")
            except Exception as e:
                logger.error(f"Failed to warm caches on startup: {e}", exc_info=True)
                logger.warning("Continuing without cache warming - caches will be populated on first request")

            yield

        except Exception as e:
            logger.error(f"CRITICAL: Application startup failed: {e}", exc_info=True)
            raise
        finally:
            # Shutdown
            logger.info("Shutting down Masjid Connect API")
            try:
                # Stop background cache refresh task
                logger.info("Stopping background cache refresh task...")
                await stop_background_cache_refresh()
                
                cache_stats = await clear_all_caches()
                logger.info(f"Caches cleared on shutdown: {cache_stats}")

                # Close Auth0 provider HTTP client
                await shutdown_auth0_provider()
                logger.info("Auth0 provider shut down")
            except Exception as e:
                logger.error(f"Error during shutdown: {e}", exc_info=True)

    app.router.lifespan_context = lifespan

    # Root endpoint
    @app.get("/")
    async def root():
        """Root endpoint with basic information."""
        return {
            "service": settings.API_TITLE,
            "version": settings.API_VERSION,
            "environment": settings.ENVIRONMENT,
            "status": "running",
            "docs": "/docs",
            "redoc": "/redoc",
            "openapi": "/openapi.json",
        }

    logger.info(f"FastAPI app created with version {settings.API_VERSION}")

    return app


# Create app instance
app = create_app()
