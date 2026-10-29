"""
Bank Deposit Batch endpoints for managing bank deposit batches.

Provides endpoints for retrieving, creating, updating, and deleting bank deposit batches.
All endpoints require authentication.

Endpoints:
    GET /api/v1/bank-deposit-batch - Get all batches
    GET /api/v1/bank-deposit-batch/{batch_number} - Get single batch by number
    GET /api/v1/bank-deposit-batch/{batch_number}/transactions - Get batch transactions
    POST /api/v1/bank-deposit-batch - Create new batch with transactions
    PUT /api/v1/bank-deposit-batch/{batch_number} - Update batch details
    DELETE /api/v1/bank-deposit-batch/{batch_number} - Delete batch
"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import settings
from src.core.logging import get_logger
from src.core.dependencies import User, get_current_user_required
from src.database import get_session
from src.core.bank_deposit_batch_utils import (
    create_bank_deposit_batch,
    get_bank_deposit_batch,
    get_bank_deposit_batches,
    update_bank_deposit_batch,
    delete_bank_deposit_batch,
    get_batch_transactions,
)
from src.models.bank_deposit_batch import (
    BankDepositBatchCreateModel,
    BankDepositBatchDetailResponse,
    BankDepositBatchListResponse,
    BankDepositBatchModel,
    BankDepositBatchResponse,
    BankDepositBatchUpdateModel,
    OperationResponse,
)

router = APIRouter(prefix="/bank-deposit-batch", tags=["bank-deposit-batch"])
logger = get_logger(__name__, level=settings.LOG_LEVEL)


@router.get(
    "",
    response_model=BankDepositBatchListResponse,
    status_code=200,
    summary="Get bank deposit batches",
    description="Retrieve all bank deposit batches with optional filtering. Requires authentication.",
)
async def get_batches(
    company_id: Optional[int] = Query(None, description="Filter by company ID"),
    batch_status: Optional[int] = Query(None, description="Filter by batch status"),
    from_date: Optional[str] = Query(None, description="Filter from date (ISO 8601 format)"),
    to_date: Optional[str] = Query(None, description="Filter to date (ISO 8601 format)"),
    limit: int = Query(100, ge=1, le=500, description="Maximum number of results"),
    offset: int = Query(0, ge=0, description="Number of results to skip"),
    current_user: User = Depends(get_current_user_required),
    session: AsyncSession = Depends(get_session),
) -> BankDepositBatchListResponse:
    """
    Retrieve a list of bank deposit batches with optional filtering.

    Args:
        company_id: Optional company ID filter
        batch_status: Optional batch status filter
        from_date: Optional start date filter (ISO 8601)
        to_date: Optional end date filter (ISO 8601)
        limit: Maximum number of results (1-500)
        offset: Number of results to skip for pagination
        current_user: Authenticated user (required)
        session: Database session (injected)

    Returns:
        BankDepositBatchListResponse with count and list of batches

    Example:
        GET /api/v1/bank-deposit-batch
        GET /api/v1/bank-deposit-batch?company_id=1
        GET /api/v1/bank-deposit-batch?batch_status=1&from_date=2024-01-01
    """
    logger.info(
        "Retrieving bank deposit batches",
        extra={
            "user_id": current_user.id,
            "company_id": company_id,
            "batch_status": batch_status,
        },
    )

    try:
        # Parse dates if provided
        from_datetime = None
        to_datetime = None
        if from_date:
            from datetime import datetime
            from_datetime = datetime.fromisoformat(from_date)
        if to_date:
            from datetime import datetime
            to_datetime = datetime.fromisoformat(to_date)

        batches, total_count = await get_bank_deposit_batches(
            session=session,
            company_id=company_id,
            batch_status=batch_status,
            from_date=from_datetime,
            to_date=to_datetime,
            limit=limit,
            offset=offset,
        )

        return BankDepositBatchListResponse(
            count=len(batches),
            items=batches,
            status="success",
        )

    except Exception as e:
        logger.error(f"Error retrieving batches: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Error retrieving bank deposit batches",
        )


@router.get(
    "/{batch_number}",
    response_model=BankDepositBatchDetailResponse,
    status_code=200,
    summary="Get bank deposit batch with transactions",
    description="Retrieve a specific bank deposit batch with all its transactions. Requires authentication.",
)
async def get_batch_detail(
    batch_number: int,
    current_user: User = Depends(get_current_user_required),
    session: AsyncSession = Depends(get_session),
) -> BankDepositBatchDetailResponse:
    """
    Get a specific bank deposit batch with all transaction details.

    Args:
        batch_number: The batch number to retrieve
        current_user: Authenticated user (required)
        session: Database session (injected)

    Returns:
        BankDepositBatchDetailResponse with batch header and transactions

    Raises:
        HTTPException: 404 if batch not found, 500 on database error
    """
    logger.info(
        f"Retrieving bank deposit batch details",
        extra={
            "user_id": current_user.id,
            "batch_number": batch_number,
        },
    )

    try:
        batch_detail = await get_bank_deposit_batch(session=session, batch_number=batch_number)

        if not batch_detail:
            logger.warning(f"Batch not found: {batch_number}")
            raise HTTPException(
                status_code=404,
                detail=f"Bank deposit batch {batch_number} not found",
            )

        return BankDepositBatchDetailResponse(
            item=batch_detail,
            status="success",
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving batch detail: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Error retrieving bank deposit batch",
        )


@router.get(
    "/{batch_number}/transactions",
    response_model=list,
    status_code=200,
    summary="Get batch transactions",
    description="Retrieve all transactions for a specific batch. Requires authentication.",
)
async def get_batch_trans(
    batch_number: int,
    current_user: User = Depends(get_current_user_required),
    session: AsyncSession = Depends(get_session),
):
    """
    Get all transactions for a specific batch.

    Args:
        batch_number: The batch number
        current_user: Authenticated user (required)
        session: Database session (injected)

    Returns:
        List of transaction details for the batch

    Raises:
        HTTPException: 404 if batch not found, 500 on database error
    """
    logger.info(
        f"Retrieving transactions for batch",
        extra={
            "user_id": current_user.id,
            "batch_number": batch_number,
        },
    )

    try:
        transactions = await get_batch_transactions(session=session, batch_number=batch_number)
        return transactions

    except Exception as e:
        logger.error(f"Error retrieving batch transactions: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Error retrieving batch transactions",
        )


@router.post(
    "",
    response_model=OperationResponse,
    status_code=201,
    summary="Create bank deposit batch",
    description="Create a new bank deposit batch with transaction details. Requires authentication.",
)
async def create_batch(
    batch_data: BankDepositBatchCreateModel,
    current_user: User = Depends(get_current_user_required),
    session: AsyncSession = Depends(get_session),
) -> OperationResponse:
    """
    Create a new bank deposit batch with transactions.

    The batch is created as an atomic operation with the header and all transaction
    details. All transactions must be provided at creation time.

    Args:
        batch_data: Batch creation data with transactions
        current_user: Authenticated user (required)
        session: Database session (injected)

    Returns:
        OperationResponse with success status and new batch number

    Raises:
        HTTPException: 400 for validation errors, 500 on database error
    """
    logger.info(
        "Creating bank deposit batch",
        extra={
            "user_id": current_user.id,
            "company_id": batch_data.companyId,
            "transaction_count": len(batch_data.transactions),
        },
    )

    try:
        # Validate transaction count
        if not batch_data.transactions or len(batch_data.transactions) == 0:
            raise HTTPException(
                status_code=400,
                detail="Batch must contain at least one transaction",
            )

        # Create batch
        batch_number = await create_bank_deposit_batch(
            session=session,
            batch_data=batch_data,
            created_by=current_user.id,
        )

        if not batch_number:
            raise HTTPException(
                status_code=500,
                detail="Failed to create batch - check logs for details",
            )

        logger.info(f"Batch created successfully: {batch_number}")

        return OperationResponse(
            success=True,
            message=f"Bank deposit batch created successfully",
            batchNumber=batch_number,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating batch: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Error creating bank deposit batch",
        )


@router.put(
    "/{batch_number}",
    response_model=OperationResponse,
    status_code=200,
    summary="Update bank deposit batch",
    description="Update an existing bank deposit batch details. Requires authentication.",
)
async def update_batch(
    batch_number: int,
    batch_data: BankDepositBatchUpdateModel,
    current_user: User = Depends(get_current_user_required),
    session: AsyncSession = Depends(get_session),
) -> OperationResponse:
    """
    Update an existing bank deposit batch.

    Only non-None fields are updated. Transaction changes must be done separately.

    Args:
        batch_number: The batch number to update
        batch_data: Fields to update
        current_user: Authenticated user (required)
        session: Database session (injected)

    Returns:
        OperationResponse with success status

    Raises:
        HTTPException: 400 for validation errors, 404 if batch not found, 500 on database error
    """
    logger.info(
        f"Updating bank deposit batch",
        extra={
            "user_id": current_user.id,
            "batch_number": batch_number,
        },
    )

    try:
        # Verify batch exists
        batch_detail = await get_bank_deposit_batch(session=session, batch_number=batch_number)
        if not batch_detail:
            raise HTTPException(
                status_code=404,
                detail=f"Bank deposit batch {batch_number} not found",
            )

        # Update batch
        success = await update_bank_deposit_batch(
            session=session,
            batch_number=batch_number,
            batch_data=batch_data,
            modified_by=current_user.id,
        )

        if not success:
            raise HTTPException(
                status_code=500,
                detail="Failed to update batch",
            )

        logger.info(f"Batch updated successfully: {batch_number}")

        return OperationResponse(
            success=True,
            message=f"Bank deposit batch {batch_number} updated successfully",
            batchNumber=batch_number,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating batch: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Error updating bank deposit batch",
        )


@router.delete(
    "/{batch_number}",
    response_model=OperationResponse,
    status_code=200,
    summary="Delete bank deposit batch",
    description="Delete a bank deposit batch and all its transactions. Requires authentication.",
)
async def delete_batch(
    batch_number: int,
    current_user: User = Depends(get_current_user_required),
    session: AsyncSession = Depends(get_session),
) -> OperationResponse:
    """
    Delete a bank deposit batch and all its associated transactions.

    Args:
        batch_number: The batch number to delete
        current_user: Authenticated user (required)
        session: Database session (injected)

    Returns:
        OperationResponse with success status

    Raises:
        HTTPException: 404 if batch not found, 500 on database error
    """
    logger.info(
        f"Deleting bank deposit batch",
        extra={
            "user_id": current_user.id,
            "batch_number": batch_number,
        },
    )

    try:
        # Verify batch exists
        batch_detail = await get_bank_deposit_batch(session=session, batch_number=batch_number)
        if not batch_detail:
            raise HTTPException(
                status_code=404,
                detail=f"Bank deposit batch {batch_number} not found",
            )

        # Delete batch
        success = await delete_bank_deposit_batch(
            session=session,
            batch_number=batch_number,
        )

        if not success:
            raise HTTPException(
                status_code=500,
                detail="Failed to delete batch",
            )

        logger.info(f"Batch deleted successfully: {batch_number}")

        return OperationResponse(
            success=True,
            message=f"Bank deposit batch {batch_number} deleted successfully",
            batchNumber=batch_number,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting batch: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Error deleting bank deposit batch",
        )
