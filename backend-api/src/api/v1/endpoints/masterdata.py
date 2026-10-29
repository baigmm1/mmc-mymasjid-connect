"""
Masterdata endpoints for country codes, state codes, and key-value pairs.

Provides GET endpoints for retrieving masterdata with optional filtering.
All endpoints support filtering via query parameters.

Endpoints:
    GET /api/v1/masterdata/countries - Get all or filtered country codes
    GET /api/v1/masterdata/countries/{country_code} - Get single country by code
    GET /api/v1/masterdata/states - Get all or filtered state codes
    GET /api/v1/masterdata/states/{state_id} - Get single state by ID
    GET /api/v1/masterdata/keyvaluepairs - Get all or filtered key-value pairs
    GET /api/v1/masterdata/keyvaluepairs/{id} - Get single key-value pair by ID
    GET /api/v1/masterdata/namevaluepairs - Get all or filtered name-value pairs
    GET /api/v1/masterdata/namevaluepairs/{id} - Get single name-value pair by ID
"""

import datetime

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import settings
from src.core.logging import get_logger
from src.database import get_session
from src.database.models.masterdata import (
    CountryCodes,
    KeyValuePairs,
    NameValuePair,
    StateCodes,
)
from src.models.masterdata import (
    CountryCodeListResponse,
    CountryCodeModel,
    CountryCodeResponse,
    KeyValuePairListResponse,
    KeyValuePairModel,
    KeyValuePairResponse,
    NameValuePairListResponse,
    NameValuePairModel,
    NameValuePairResponse,
    StateCodeListResponse,
    StateCodeModel,
    StateCodeResponse,
)
from src.models.error import ErrorResponse

router = APIRouter(prefix="/masterdata", tags=["masterdata"])
logger = get_logger(__name__, level=settings.LOG_LEVEL)


@router.get(
    "/countries",
    response_model=CountryCodeListResponse,
    status_code=200,
    summary="Get country codes",
    description="Retrieve all country codes or filter by country code or name",
)
async def get_countries(
    country_code: Optional[str] = Query(None, description="Filter by country code (e.g., 'USA')"),
    country_name: Optional[str] = Query(None, description="Filter by country name (partial match)"),
    session: AsyncSession = Depends(get_session),
) -> CountryCodeListResponse:
    """
    Get list of country codes with optional filtering.

    Args:
        country_code: Optional country code filter
        country_name: Optional country name filter (case-insensitive partial match)
        session: Database session (injected)

    Returns:
        CountryCodeListResponse with count and list of country codes

    Example:
        GET /api/v1/masterdata/countries
        GET /api/v1/masterdata/countries?country_code=USA
        GET /api/v1/masterdata/countries?country_name=United
    """
    logger.info(
        "Retrieving country codes",
        extra={
            "country_code_filter": country_code,
            "country_name_filter": country_name,
        },
    )
    #print(f"Country code filter: {country_code}, Country name filter: {country_name}")
    try:
        query = select(CountryCodes)

        if country_code:
            query = query.where(CountryCodes.CountryCode == country_code)
            logger.debug(f"Applied country_code filter: {country_code}")
        if country_name:
            query = query.where(CountryCodes.CountryName.ilike(f"%{country_name}%"))
            logger.debug(f"Applied country_name filter: {country_name}")

        result = await session.execute(query)
        countries = result.scalars().all()

        logger.info(
            f"Retrieved {len(countries)} country codes",
            extra={"count": len(countries)},
        )

        return CountryCodeListResponse(
            count=len(countries),
            items=[CountryCodeModel.model_validate(country) for country in countries],
            status="success"
        )
    except Exception as e:
        logger.error(
            f"Error retrieving country codes: {str(e)}",
            extra={"error": str(e), "error_type": type(e).__name__},
            exc_info=True,
        )
        raise        


@router.get(
    "/states",
    response_model=StateCodeListResponse,
    status_code=200,
    summary="Get state codes",
    description="Retrieve all state codes or filter by country code, state code, or name",
)
async def get_states(
    country_code: Optional[str] = Query(None, description="Filter by country code (e.g., 'USA')"),
    state_code: Optional[str] = Query(None, description="Filter by state code (e.g., 'CA')"),
    state_name: Optional[str] = Query(None, description="Filter by state name (partial match)"),
    session: AsyncSession = Depends(get_session),
) -> StateCodeListResponse:
    """
    Get list of state codes with optional filtering.

    Args:
        country_code: Optional country code filter
        state_code: Optional state code filter
        state_name: Optional state name filter (case-insensitive partial match)
        session: Database session (injected)

    Returns:
        StateCodeListResponse with count and list of state codes

    Example:
        GET /api/v1/masterdata/states
        GET /api/v1/masterdata/states?country_code=USA
        GET /api/v1/masterdata/states?state_code=CA
        GET /api/v1/masterdata/states?state_name=California
    """
    logger.info(
        "Retrieving state codes",
        extra={
            "country_code_filter": country_code,
            "state_code_filter": state_code,
            "state_name_filter": state_name,
        },
    )

    try:
        query = select(StateCodes)

        if country_code:
            query = query.where(StateCodes.CountryCode == country_code)
            logger.debug(f"Applied country_code filter: {country_code}")
        if state_code:
            query = query.where(StateCodes.StateCode == state_code)
            logger.debug(f"Applied state_code filter: {state_code}")
        if state_name:
            query = query.where(StateCodes.StateName.ilike(f"%{state_name}%"))
            logger.debug(f"Applied state_name filter: {state_name}")

        result = await session.execute(query)
        states = result.scalars().all()

        logger.info(
            f"Retrieved {len(states)} state codes",
            extra={"count": len(states)},
        )

        return StateCodeListResponse(
            count=len(states),
            items=[StateCodeModel.model_validate(state) for state in states],
            status="success"
        )
    except Exception as e:
        logger.error(
            f"Error retrieving state codes: {str(e)}",
            extra={"error": str(e), "error_type": type(e).__name__},
            exc_info=True,
        )
        raise


@router.get(
    "/keyvaluepairs",
    response_model=KeyValuePairListResponse,
    status_code=200,
    summary="Get key-value pairs",
    description="Retrieve all key-value pairs or filter by type or key",
)
async def get_keyvaluepairs(
    type_filter: Optional[int] = Query(None, alias="type", description="Filter by type", ge=0),
    key: Optional[int] = Query(None, description="Filter by key", ge=0),
    session: AsyncSession = Depends(get_session)
) -> KeyValuePairListResponse:
    """
    Get list of key-value pairs with optional filtering.

    Args:
        type_filter: Optional type filter
        key: Optional key filter
        session: Database session (injected)

    Returns:
        KeyValuePairListResponse with count and list of key-value pairs

    Example:
        GET /api/v1/masterdata/keyvaluepairs
        GET /api/v1/masterdata/keyvaluepairs?type=1
        GET /api/v1/masterdata/keyvaluepairs?key=100
    """
    logger.info(
        "Retrieving key-value pairs",
        extra={"type_filter": type_filter, "key_filter": key},
    )

    try:
        query = select(KeyValuePairs)

        if type_filter is not None:
            query = query.where(KeyValuePairs.Type == type_filter)
            logger.debug(f"Applied type filter: {type_filter}")
        if key is not None:
            query = query.where(KeyValuePairs.Key == key)
            logger.debug(f"Applied key filter: {key}")

        result = await session.execute(query)
        pairs = result.scalars().all()

        logger.info(
            f"Retrieved {len(pairs)} key-value pairs",
            extra={"count": len(pairs)},
        )

        return KeyValuePairListResponse(
            count=len(pairs),
            items=[KeyValuePairModel.model_validate(pair) for pair in pairs],
            status="success"
        )
    except Exception as e:
        logger.error(
            f"Error retrieving key-value pairs: {str(e)}",
            extra={"error": str(e), "error_type": type(e).__name__},
            exc_info=True,
        )
        raise


@router.get(
    "/namevaluepairs",
    response_model=NameValuePairListResponse,
    status_code=200,
    summary="Get name-value pairs",
    description="Retrieve all name-value pairs or filter by type or name",
)
async def get_namevaluepairs(
    type_filter: Optional[int] = Query(None, alias="type", description="Filter by type", ge=0),
    name: Optional[str] = Query(None, description="Filter by name (partial match)"),
    session: AsyncSession = Depends(get_session),
) -> NameValuePairListResponse:
    """
    Get list of name-value pairs with optional filtering.

    Args:
        type_filter: Optional type filter
        name: Optional name filter (case-insensitive partial match)
        session: Database session (injected)

    Returns:
        NameValuePairListResponse with count and list of name-value pairs

    Example:
        GET /api/v1/masterdata/namevaluepairs
        GET /api/v1/masterdata/namevaluepairs?type=1
        GET /api/v1/masterdata/namevaluepairs?name=theme
    """
    logger.info(
        "Retrieving name-value pairs",
        extra={"type_filter": type_filter, "name_filter": name},
    )

    try:
        query = select(NameValuePair)

        if type_filter is not None:
            query = query.where(NameValuePair.Type == type_filter)
            logger.debug(f"Applied type filter: {type_filter}")
        if name:
            query = query.where(NameValuePair.Name.ilike(f"%{name}%"))
            logger.debug(f"Applied name filter: {name}")

        result = await session.execute(query)
        pairs = result.scalars().all()

        logger.info(
            f"Retrieved {len(pairs)} name-value pairs",
            extra={"count": len(pairs)},
        )

        return NameValuePairListResponse(
            count=len(pairs),
            items=[NameValuePairModel.model_validate(pair) for pair in pairs],
            status="success"
        )
    except Exception as e:
        logger.error(
            f"Error retrieving name-value pairs: {str(e)}",
            extra={"error": str(e), "error_type": type(e).__name__},
            exc_info=True,
        )
        raise


# Single object endpoints

@router.get(
    "/countries/{country_code}",
    response_model=CountryCodeResponse,
    status_code=200,
    summary="Get country by code",
    description="Retrieve a single country by its country code",
)
async def get_country_by_code(
    country_code: str,
    session: AsyncSession = Depends(get_session),
) -> CountryCodeResponse:
    """
    Get a single country by country code.

    Args:
        country_code: Country code (e.g., 'US', 'CA')
        session: Database session (injected)

    Returns:
        CountryCodeResponse with country details

    Raises:
        HTTPException: 404 if country code not found

    Example:
        GET /api/v1/masterdata/countries/US
        GET /api/v1/masterdata/countries/CA
    """
    logger.info(
        f"Retrieving country by code: {country_code}",
        extra={"country_code": country_code},
    )

    try:
        query = select(CountryCodes).where(CountryCodes.CountryCode == country_code)
        result = await session.execute(query)
        country = result.scalar_one_or_none()

        if country is None:
            logger.warning(f"Country code not found: {country_code}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Country with code '{country_code}' not found"
            )

        logger.info(f"Retrieved country: {country.CountryName}")
        return CountryCodeResponse(
            item=CountryCodeModel.model_validate(country),
            status="success"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Error retrieving country by code: {str(e)}",
            extra={"error": str(e), "error_type": type(e).__name__},
            exc_info=True,
        )
        raise


@router.get(
    "/states/{state_id}",
    response_model=StateCodeResponse,
    status_code=200,
    summary="Get state by ID",
    description="Retrieve a single state by its unique ID",
)
async def get_state_by_id(
    state_id: int,
    session: AsyncSession = Depends(get_session),
) -> StateCodeResponse:
    """
    Get a single state by state ID.

    Args:
        state_id: Unique state identifier
        session: Database session (injected)

    Returns:
        StateCodeResponse with state details

    Raises:
        HTTPException: 404 if state ID not found

    Example:
        GET /api/v1/masterdata/states/1
        GET /api/v1/masterdata/states/25
    """
    logger.info(
        f"Retrieving state by ID: {state_id}",
        extra={"state_id": state_id},
    )

    try:
        query = select(StateCodes).where(StateCodes.StateId == state_id)
        result = await session.execute(query)
        state = result.scalar_one_or_none()

        if state is None:
            logger.warning(f"State ID not found: {state_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"State with ID '{state_id}' not found"
            )

        logger.info(f"Retrieved state: {state.StateName}")
        return StateCodeResponse(
            item=StateCodeModel.model_validate(state),
            status="success"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Error retrieving state by ID: {str(e)}",
            extra={"error": str(e), "error_type": type(e).__name__},
            exc_info=True,
        )
        raise


@router.get(
    "/keyvaluepairs/{id}",
    response_model=KeyValuePairResponse,
    status_code=200,
    summary="Get key-value pair by ID",
    description="Retrieve a single key-value pair by its unique ID",
)
async def get_keyvaluepair_by_id(
    id: int,
    session: AsyncSession = Depends(get_session),
) -> KeyValuePairResponse:
    """
    Get a single key-value pair by ID.

    Args:
        id: Unique key-value pair identifier
        session: Database session (injected)

    Returns:
        KeyValuePairResponse with key-value pair details

    Raises:
        HTTPException: 404 if ID not found

    Example:
        GET /api/v1/masterdata/keyvaluepairs/1
        GET /api/v1/masterdata/keyvaluepairs/100
    """
    logger.info(
        f"Retrieving key-value pair by ID: {id}",
        extra={"id": id},
    )

    try:
        query = select(KeyValuePairs).where(KeyValuePairs.Id == id)
        result = await session.execute(query)
        pair = result.scalar_one_or_none()

        if pair is None:
            logger.warning(f"Key-value pair ID not found: {id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Key-value pair with ID '{id}' not found"
            )

        logger.info(f"Retrieved key-value pair with key: {pair.Key}")
        return KeyValuePairResponse(
            item=KeyValuePairModel.model_validate(pair),
            status="success"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Error retrieving key-value pair by ID: {str(e)}",
            extra={"error": str(e), "error_type": type(e).__name__},
            exc_info=True,
        )
        raise


@router.get(
    "/namevaluepairs/{id}",
    response_model=NameValuePairResponse,
    status_code=200,
    summary="Get name-value pair by ID",
    description="Retrieve a single name-value pair by its unique ID",
)
async def get_namevaluepair_by_id(
    id: int,
    session: AsyncSession = Depends(get_session),
) -> NameValuePairResponse:
    """
    Get a single name-value pair by ID.

    Args:
        id: Unique name-value pair identifier
        session: Database session (injected)

    Returns:
        NameValuePairResponse with name-value pair details

    Raises:
        HTTPException: 404 if ID not found

    Example:
        GET /api/v1/masterdata/namevaluepairs/1
        GET /api/v1/masterdata/namevaluepairs/50
    """
    logger.info(
        f"Retrieving name-value pair by ID: {id}",
        extra={"id": id},
    )

    try:
        query = select(NameValuePair).where(NameValuePair.Id == id)
        result = await session.execute(query)
        pair = result.scalar_one_or_none()

        if pair is None:
            logger.warning(f"Name-value pair ID not found: {id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Name-value pair with ID '{id}' not found"
            )

        logger.info(f"Retrieved name-value pair with name: {pair.Name}")
        return NameValuePairResponse(
            item=NameValuePairModel.model_validate(pair),
            status="success"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Error retrieving name-value pair by ID: {str(e)}",
            extra={"error": str(e), "error_type": type(e).__name__},
            exc_info=True,
        )
        raise
