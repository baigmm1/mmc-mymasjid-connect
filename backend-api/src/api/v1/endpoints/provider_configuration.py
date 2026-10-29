"""
ProviderConfiguration endpoints for managing provider configuration data.

Provides GET endpoints for retrieving provider configurations with optional filtering.

Endpoints:
    GET /api/v1/provider-configuration - Get all or filtered provider configurations
    GET /api/v1/provider-configuration/{company_id}/{provider} - Get single configuration by composite key
    GET /api/v1/provider-configuration/by-company/{company_id} - Get all configurations for a company
"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import settings
from src.core.cache_manager import get_provider_configurations_from_cache, get_provider_configuration_from_cache
from src.core.logging import get_logger
from src.database import get_session
from src.database.models.provider_configuration import ProviderConfiguration
from src.models.provider_configuration import (
    ProviderConfigurationListResponse,
    ProviderConfigurationModel,
    ProviderConfigurationResponse,
)

router = APIRouter(prefix="/provider-configuration", tags=["provider-configuration"])
logger = get_logger(__name__, level=settings.LOG_LEVEL)


@router.get(
    "",
    response_model=ProviderConfigurationListResponse,
    status_code=200,
    summary="Get provider configurations",
    description="Retrieve all provider configurations or filter by various criteria",
)
async def get_provider_configurations(
    company_id: Optional[int] = Query(None, description="Filter by company ID"),
    provider: Optional[str] = Query(None, description="Filter by provider name"),
    environment: Optional[str] = Query(None, description="Filter by environment"),
    session: AsyncSession = Depends(get_session),
) -> ProviderConfigurationListResponse:
    """
    Get list of provider configurations with optional filtering.

    Args:
        company_id: Optional company ID filter
        provider: Optional provider name filter
        environment: Optional environment filter
        session: Database session (injected)

    Returns:
        ProviderConfigurationListResponse with count and list of configurations

    Example:
        GET /api/v1/provider-configuration
        GET /api/v1/provider-configuration?company_id=1
        GET /api/v1/provider-configuration?provider=Stripe
        GET /api/v1/provider-configuration?company_id=1&provider=Stripe
    """
    logger.info(
        "Retrieving provider configurations",
        extra={
            "company_id_filter": company_id,
            "provider_filter": provider,
            "environment_filter": environment,
        },
    )

    try:
        # Try to get from cache first (filters will be applied to cached data)
        if not any([company_id, provider, environment]):
            # No filters, can use cached data directly
            configurations = await get_provider_configurations_from_cache()
            logger.info(f"Retrieved {len(configurations)} provider configurations from cache")
        else:
            # Has filters, need to query database or filter cache
            query = select(ProviderConfiguration)

            if company_id is not None:
                query = query.where(ProviderConfiguration.CompanyId == company_id)
                logger.debug(f"Applied company_id filter: {company_id}")
            if provider:
                query = query.where(ProviderConfiguration.Provider == provider)
                logger.debug(f"Applied provider filter: {provider}")
            if environment:
                query = query.where(ProviderConfiguration.Environment == environment)
                logger.debug(f"Applied environment filter: {environment}")

            result = await session.execute(query)
            configurations = result.scalars().all()
            logger.info(f"Retrieved {len(configurations)} provider configurations from database")

        # Convert to response models
        config_models = [ProviderConfigurationModel.model_validate(config) for config in configurations]

        return ProviderConfigurationListResponse(
            count=len(config_models),
            items=config_models,
            status="success",
        )

    except Exception as e:
        logger.error(f"Error retrieving provider configurations: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving provider configurations: {str(e)}",
        )


@router.get(
    "/{company_id}/{provider}",
    response_model=ProviderConfigurationResponse,
    status_code=200,
    summary="Get provider configuration by composite key",
    description="Retrieve a single provider configuration by company ID and provider name",
)
async def get_provider_configuration(
    company_id: int,
    provider: str,
    session: AsyncSession = Depends(get_session),
) -> ProviderConfigurationResponse:
    """
    Get a single provider configuration by composite key.

    Args:
        company_id: Company identifier
        provider: Provider name
        session: Database session (injected)

    Returns:
        ProviderConfigurationResponse with the configuration

    Raises:
        HTTPException: 404 if configuration not found

    Example:
        GET /api/v1/provider-configuration/1/Stripe
    """
    logger.info(f"Retrieving provider configuration for company_id={company_id}, provider={provider}")

    try:
        # Try to get from cache first
        configuration = await get_provider_configuration_from_cache(company_id, provider)

        if not configuration:
            logger.warning(f"Provider configuration not found: company_id={company_id}, provider={provider}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Provider configuration not found for company_id={company_id} and provider={provider}",
            )

        config_model = ProviderConfigurationModel.model_validate(configuration)

        logger.info(f"Successfully retrieved provider configuration for company_id={company_id}, provider={provider}")
        return ProviderConfigurationResponse(
            item=config_model,
            status="success",
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Error retrieving provider configuration for company_id={company_id}, provider={provider}: {str(e)}",
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving provider configuration: {str(e)}",
        )


@router.get(
    "/by-company/{company_id}",
    response_model=ProviderConfigurationListResponse,
    status_code=200,
    summary="Get provider configurations by company",
    description="Retrieve all provider configurations for a specific company",
)
async def get_provider_configurations_by_company(
    company_id: int,
    session: AsyncSession = Depends(get_session),
) -> ProviderConfigurationListResponse:
    """
    Get all provider configurations for a specific company.

    Args:
        company_id: Company identifier
        session: Database session (injected)

    Returns:
        ProviderConfigurationListResponse with count and list of configurations

    Example:
        GET /api/v1/provider-configuration/by-company/1
    """
    logger.info(f"Retrieving all provider configurations for company_id={company_id}")

    try:
        query = select(ProviderConfiguration).where(ProviderConfiguration.CompanyId == company_id)
        result = await session.execute(query)
        configurations = result.scalars().all()

        logger.info(f"Retrieved {len(configurations)} provider configurations for company_id={company_id}")

        # Convert to response models
        config_models = [ProviderConfigurationModel.model_validate(config) for config in configurations]

        return ProviderConfigurationListResponse(
            count=len(config_models),
            items=config_models,
            status="success",
        )

    except Exception as e:
        logger.error(
            f"Error retrieving provider configurations for company_id={company_id}: {str(e)}",
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving provider configurations: {str(e)}",
        )
