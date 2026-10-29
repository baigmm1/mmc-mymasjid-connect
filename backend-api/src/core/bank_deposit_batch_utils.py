"""
Utility functions for Bank Deposit Batch operations.

Provides helper functions for creating, reading, updating, and deleting bank deposit batches.
These functions use stored procedures for data operations and can be reused from endpoints
as well as from webhook handlers and transaction processors.
"""

from datetime import datetime
from decimal import Decimal
from typing import Optional, List, Dict, Any

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from src.core.logging import get_logger
from src.core.stored_procedure_utils import execute_stored_procedure, execute_stored_procedure_with_output
from src.database.models.bank_deposit_batch import BankDepositBatch
from src.database.models.bank_deposit_batch_transactions import BankDepositBatchTransactions
from src.models.bank_deposit_batch import (
    BankDepositBatchCreateModel,
    BankDepositBatchDetailModel,
    BankDepositBatchModel,
    BankDepositBatchTransactionModel,
    BankDepositBatchUpdateModel,
)

logger = get_logger(__name__)


async def create_bank_deposit_batch(
    session: AsyncSession,
    batch_data: BankDepositBatchCreateModel,
    logged_user_id: Optional[int] = None,
) -> Optional[int]:
    """
    Create a new bank deposit batch with transactions using stored procedure.

    Args:
        session: Database session
        batch_data: Batch creation data including transactions
        logged_user_id: Optional logged user ID for auditing (can be used in stored procedure)
    Returns:
        BatchNumber if successful, None if failed

    Note:
        The actual stored procedure name should be updated. Stub uses placeholder.
        Expected stored procedure: [dbo].[sp_CreateBankDepositBatch]
        Expected to handle batch creation and return the new batch number.
    """
    try:
        logger.info(
            "Creating bank deposit batch",
            extra={
                "company_id": batch_data.companyId,
                "amount": batch_data.amount,
                "transaction_count": len(batch_data.transactions),
            },
        )

        parameters = {
            "DataType": 0,      
            "CompanyId": batch_data.companyId,
            "ProviderId": batch_data.providerId,
            "BatchDate": batch_data.batchDate,
            "BankDepositDate": batch_data.bankDepositDate,
            "BatchStatus": batch_data.batchStatus,
            "BatchMethodType": batch_data.batchMethodTypeId,
            "Amount": batch_data.amount,
            "LoggedUser": logged_user_id,
        }
        
        output_params = {   
            "BatchNumber": "int", 
        }

        # Remove None values
        parameters = {k: v for k, v in parameters.items() if v is not None}

        # Execute stored procedure to create transaction header
        logger.info("Executing UIActionCRUDBankBatch stored procedure")
        results = await execute_stored_procedure_with_output(
            session=session,
            procedure_name="dbo.UIActionCRUDBankBatch",
            parameters=parameters,
            output_params=output_params
        )
        
        batch_number = results[1]['BatchNumber']
        if batch_number is None:
            logger.error("Failed to create bank deposit batch: No batch number returned")
            raise Exception("Failed to create bank deposit batch: No batch number returned")

        line_number = 1
        for transaction in batch_data.transactions:
            detail_params = {
                "DataType": 11,            
                "BatchNumber": batch_number,
                "CompanyId": batch_data.companyId,
                "LineNumber": line_number,
                "ReceiptId": transaction.donationReceiptId,
                "TransactionId": transaction.providerId,
                "TransactionType": transaction.transactionType,
                "TransactionAmount": transaction.amount,
                "FeeAmount": transaction.feeAmount,
                "LoggedUser": logged_user_id,
            }
            detail_params = {k: v for k, v in detail_params.items() if v is not None}
            await execute_stored_procedure(
                session=session,
                procedure_name="dbo.UIActionCRUDBankBatch",
                parameters=detail_params,
                fetch_results=False
            )
            line_number += 1


        summary_params = {
            "DataType": 99,
            "BatchNumber": batch_number,
            "CompanyId": batch_data.companyId,
            "LoggedUser": logged_user_id,
        }
        summary_params = {k: v for k, v in summary_params.items() if v is not None}
        await execute_stored_procedure(
            session=session,    
            procedure_name="dbo.UIActionCRUDBankBatch",
            parameters=summary_params,
            fetch_results=False
        )

        logger.info(f"Bank deposit batch created successfully: {batch_number}")
        return batch_number
    except Exception as e:
        logger.error(f"Error creating bank deposit batch: {str(e)}", exc_info=True)
        raise


async def get_bank_deposit_batch(
    session: AsyncSession,
    batch_number: int,
) -> Optional[BankDepositBatchDetailModel]:
    """
    Get a specific bank deposit batch with all transactions.

    Args:
        session: Database session
        batch_number: The batch number to retrieve

    Returns:
        BankDepositBatchDetailModel with batch and transactions, or None if not found
    """
    try:
        logger.info(f"Retrieving bank deposit batch: {batch_number}")

        # Call stored procedure to get batch and transactions
        result = await execute_stored_procedure(
            session=session,
            procedure_name="[dbo].[sp_GetBankDepositBatch]",
            parameters={"BatchNumber": batch_number},
            fetch_multiple=False,
        )

        if not result:
            logger.warning(f"Bank deposit batch not found: {batch_number}")
            return None

        # Parse the result - assuming procedure returns batch data in first record
        # and transactions in subsequent records
        if len(result) == 0:
            return None

        batch_row = result[0]
        
        # Create batch model
        batch_model = BankDepositBatchModel(
            BatchNumber=batch_row.get("BatchNumber", batch_row.get("batchNumber")),
            BatchDate=batch_row.get("BatchDate", batch_row.get("batchDate")),
            BankDepositDate=batch_row.get("BankDepositDate", batch_row.get("bankDepositDate")),
            BatchStatus=batch_row.get("BatchStatus", batch_row.get("batchStatus")),
            CreatedBy=batch_row.get("CreatedBy", batch_row.get("createdBy")),
            CreatedDate=batch_row.get("CreatedDate", batch_row.get("createdDate")),
            ModifiedBy=batch_row.get("ModifiedBy", batch_row.get("modifiedBy")),
            ModifiedDate=batch_row.get("ModifiedDate", batch_row.get("modifiedDate")),
            BatchMethodType=batch_row.get("BatchMethodType", batch_row.get("batchMethodType")),
            CompanyId=batch_row.get("CompanyId", batch_row.get("companyId")),
            ProviderId=batch_row.get("ProviderId", batch_row.get("providerId")),
            Amount=batch_row.get("Amount", batch_row.get("amount")),
        )

        # Create transaction models from result rows
        transactions = []
        for row in result[1:]:  # Skip batch row
            transaction_model = BankDepositBatchTransactionModel(
                CompanyId=row.get("CompanyId", row.get("companyId")),
                BatchNumber=row.get("BatchNumber", row.get("batchNumber")),
                LineNumber=row.get("LineNumber", row.get("lineNumber")),
                DonationReceiptId=row.get("DonationReceiptId", row.get("donationReceiptId")),
                ProviderId=row.get("ProviderId", row.get("providerId")),
                TransactionType=row.get("TransactionType", row.get("transactionType")),
                Amount=row.get("Amount", row.get("amount")),
                CreatedBy=row.get("CreatedBy", row.get("createdBy")),
                CreatedDate=row.get("CreatedDate", row.get("createdDate")),
                ModifiedBy=row.get("ModifiedBy", row.get("modifiedBy")),
                ModifiedDate=row.get("ModifiedDate", row.get("modifiedDate")),
            )
            transactions.append(transaction_model)

        detail_model = BankDepositBatchDetailModel(batch=batch_model, transactions=transactions)
        logger.info(f"Retrieved batch {batch_number} with {len(transactions)} transactions")
        return detail_model

    except Exception as e:
        logger.error(f"Error retrieving bank deposit batch: {str(e)}", exc_info=True)
        raise


async def get_bank_deposit_batches(
    session: AsyncSession,
    company_id: Optional[int] = None,
    batch_status: Optional[int] = None,
    from_date: Optional[datetime] = None,
    to_date: Optional[datetime] = None,
    limit: int = 100,
    offset: int = 0,
) -> tuple[List[BankDepositBatchModel], int]:
    """
    Get a list of bank deposit batches with optional filters.

    Args:
        session: Database session
        company_id: Filter by company ID
        batch_status: Filter by batch status
        from_date: Filter batches from this date
        to_date: Filter batches to this date
        limit: Maximum number of results
        offset: Number of results to skip

    Returns:
        Tuple of (list of BankDepositBatchModel, total count)
    """
    try:
        logger.info(
            "Retrieving bank deposit batches",
            extra={
                "company_id": company_id,
                "batch_status": batch_status,
                "from_date": from_date,
                "to_date": to_date,
            },
        )

        # Call stored procedure to get batches
        result = await execute_stored_procedure(
            session=session,
            procedure_name="[dbo].[sp_GetBankDepositBatches]",
            parameters={
                "CompanyId": company_id,
                "BatchStatus": batch_status,
                "FromDate": from_date,
                "ToDate": to_date,
                "Limit": limit,
                "Offset": offset,
            },
            fetch_results=True,
        )

        if not result:
            logger.info("No batches found")
            return [], 0

        # Convert rows to models
        batches = [
            BankDepositBatchModel(
                BatchNumber=row.get("BatchNumber", row.get("batchNumber")),
                BatchDate=row.get("BatchDate", row.get("batchDate")),
                BankDepositDate=row.get("BankDepositDate", row.get("bankDepositDate")),
                BatchStatus=row.get("BatchStatus", row.get("batchStatus")),
                CreatedBy=row.get("CreatedBy", row.get("createdBy")),
                CreatedDate=row.get("CreatedDate", row.get("createdDate")),
                ModifiedBy=row.get("ModifiedBy", row.get("modifiedBy")),
                ModifiedDate=row.get("ModifiedDate", row.get("modifiedDate")),
                BatchMethodType=row.get("BatchMethodType", row.get("batchMethodType")),
                CompanyId=row.get("CompanyId", row.get("companyId")),
                ProviderId=row.get("ProviderId", row.get("providerId")),
                Amount=row.get("Amount", row.get("amount")),
            )
            for row in result
        ]

        # Get total count (usually in last result or separate field)
        total_count = len(batches)
        if result and len(result) > 0:
            total_count = result[0].get("TotalCount", len(batches))

        logger.info(f"Retrieved {len(batches)} batches (total: {total_count})")
        return batches, total_count

    except Exception as e:
        logger.error(f"Error retrieving bank deposit batches: {str(e)}", exc_info=True)
        raise


async def update_bank_deposit_batch(
    session: AsyncSession,
    batch_number: int,
    batch_data: BankDepositBatchUpdateModel,
    modified_by: str,
) -> bool:
    """
    Update an existing bank deposit batch using stored procedure.

    Args:
        session: Database session
        batch_number: The batch number to update
        batch_data: Update data (only non-None fields are updated)
        modified_by: User ID who is modifying the batch

    Returns:
        True if successful, False otherwise
    """
    try:
        logger.info(f"Updating bank deposit batch: {batch_number}")

        # Build parameters only for non-None fields
        parameters = {
            "BatchNumber": batch_number,
            "ModifiedBy": modified_by,
        }

        if batch_data.batchDate is not None:
            parameters["BatchDate"] = batch_data.batchDate
        if batch_data.bankDepositDate is not None:
            parameters["BankDepositDate"] = batch_data.bankDepositDate
        if batch_data.batchStatus is not None:
            parameters["BatchStatus"] = batch_data.batchStatus
        if batch_data.batchMethodType is not None:
            parameters["BatchMethodType"] = batch_data.batchMethodType
        if batch_data.amount is not None:
            parameters["Amount"] = batch_data.amount

        result = await execute_stored_procedure(
            session=session,
            procedure_name="[dbo].[sp_UpdateBankDepositBatch]",
            parameters=parameters,
            fetch_results=True,
        )

        # Check if update was successful
        if result and len(result) > 0:
            success = bool(result[0].get("Success") or result[0].get("success"))
            if success:
                logger.info(f"Bank deposit batch updated successfully: {batch_number}")
            else:
                logger.warning(f"Update failed for batch: {batch_number}")
            return success

        return False

    except Exception as e:
        logger.error(f"Error updating bank deposit batch: {str(e)}", exc_info=True)
        raise


async def delete_bank_deposit_batch(
    session: AsyncSession,
    batch_number: int,
) -> bool:
    """
    Delete a bank deposit batch and all its transactions using stored procedure.

    Args:
        session: Database session
        batch_number: The batch number to delete

    Returns:
        True if successful, False otherwise
    """
    try:
        logger.info(f"Deleting bank deposit batch: {batch_number}")

        result = await execute_stored_procedure(
            session=session,
            procedure_name="[dbo].[sp_DeleteBankDepositBatch]",
            parameters={"BatchNumber": batch_number},
            fetch_results=True,
        )

        # Check if delete was successful
        if result and len(result) > 0:
            success = bool(result[0].get("Success") or result[0].get("success"))
            if success:
                logger.info(f"Bank deposit batch deleted successfully: {batch_number}")
            else:
                logger.warning(f"Delete failed for batch: {batch_number}")
            return success

        return False

    except Exception as e:
        logger.error(f"Error deleting bank deposit batch: {str(e)}", exc_info=True)
        raise


async def add_batch_transaction(
    session: AsyncSession,
    batch_number: int,
    company_id: int,
    donation_receipt_id: int,
    provider_id: str,
    transaction_type: str,
    amount: Decimal,
    created_by: int,
) -> bool:
    """
    Add a single transaction to an existing batch.

    This utility function can be called from Stripe webhooks or transaction processors
    to add transactions to existing batches.

    Args:
        session: Database session
        batch_number: The batch number to add transaction to
        company_id: Company identifier
        donation_receipt_id: Donation receipt identifier
        provider_id: Payment provider identifier
        transaction_type: Type of transaction
        amount: Transaction amount
        created_by: User ID creating the transaction

    Returns:
        True if successful, False otherwise
    """
    try:
        logger.info(
            "Adding transaction to batch",
            extra={
                "batch_number": batch_number,
                "donation_receipt_id": donation_receipt_id,
                "amount": amount,
            },
        )

        result = await execute_stored_procedure(
            session=session,
            procedure_name="[dbo].[sp_AddBankDepositBatchTransaction]",
            parameters={
                "BatchNumber": batch_number,
                "CompanyId": company_id,
                "DonationReceiptId": donation_receipt_id,
                "ProviderId": provider_id,
                "TransactionType": transaction_type,
                "Amount": amount,
                "CreatedBy": created_by,
            },
            fetch_results=True,
        )

        # Check if add was successful
        if result and len(result) > 0:
            success = bool(result[0].get("Success") or result[0].get("success"))
            if success:
                logger.info(f"Transaction added to batch {batch_number} successfully")
            else:
                logger.warning(f"Failed to add transaction to batch {batch_number}")
            return success

        return False

    except Exception as e:
        logger.error(f"Error adding transaction to batch: {str(e)}", exc_info=True)
        raise


async def get_batch_transactions(
    session: AsyncSession,
    batch_number: int,
) -> List[BankDepositBatchTransactionModel]:
    """
    Get all transactions for a specific batch.

    Args:
        session: Database session
        batch_number: The batch number

    Returns:
        List of transaction models
    """
    try:
        logger.info(f"Retrieving transactions for batch: {batch_number}")

        result = await execute_stored_procedure(
            session=session,
            procedure_name="[dbo].[sp_GetBankDepositBatchTransactions]",
            parameters={"BatchNumber": batch_number},
            fetch_results=True,
        )

        if not result:
            logger.info(f"No transactions found for batch: {batch_number}")
            return []

        transactions = [
            BankDepositBatchTransactionModel(
                CompanyId=row.get("CompanyId", row.get("companyId")),
                BatchNumber=row.get("BatchNumber", row.get("batchNumber")),
                LineNumber=row.get("LineNumber", row.get("lineNumber")),
                DonationReceiptId=row.get("DonationReceiptId", row.get("donationReceiptId")),
                ProviderId=row.get("ProviderId", row.get("providerId")),
                TransactionType=row.get("TransactionType", row.get("transactionType")),
                Amount=row.get("Amount", row.get("amount")),
                CreatedBy=row.get("CreatedBy", row.get("createdBy")),
                CreatedDate=row.get("CreatedDate", row.get("createdDate")),
                ModifiedBy=row.get("ModifiedBy", row.get("modifiedBy")),
                ModifiedDate=row.get("ModifiedDate", row.get("modifiedDate")),
            )
            for row in result
        ]

        logger.info(f"Retrieved {len(transactions)} transactions for batch {batch_number}")
        return transactions

    except Exception as e:
        logger.error(f"Error retrieving batch transactions: {str(e)}", exc_info=True)
        raise
