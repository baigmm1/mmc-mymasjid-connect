"""
Utility functions for Recurring Transactions operations.

Provides helper functions for creating, reading, updating, and deleting recurring transactions.
These functions use stored procedures for data operations and can be reused from endpoints,
webhook handlers, and the Stripe subscription sync script.
"""

from datetime import datetime
from decimal import Decimal
from typing import Optional, List, Dict, Any

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from src.core.logging import get_logger
from src.core.stored_procedure_utils import execute_stored_procedure, execute_stored_procedure_with_output
from src.database.models.recurring_transactions import RecurringTransactions
from src.database.models.recurring_transaction_details import RecurringTransactionDetails
from src.database.models.recurring_transaction_payments import RecurringTransactionPayments
from src.models.recurring_transactions import (
    RecurringTransactionModel,
    RecurringTransactionCreateModel,
    RecurringTransactionResponse,
    RecurringTransactionUpdateModel,
    RecurringTransactionDetailModel,
    RecurringTransactionDetailsModel,
    RecurringTransactionPaymentsModel,
    RecurringTransactionListResponse,
)
from src.database.models.donation_type import DonationType
logger = get_logger(__name__)


async def create_recurring_transaction(
    session: AsyncSession,
    transaction_data: RecurringTransactionCreateModel,
    created_by: int = 0,
) -> Optional[int]:
    """
    Create a new recurring transaction using stored procedure.

    Args:
        session: Database session
        transaction_data: Transaction creation data
        created_by: User ID who is creating the transaction (default: 0 for system)

    Returns:
        TransactionId if successful, None if failed

    Note:
        Expected stored procedure: [dbo].[sp_CreateRecurringTransaction]
        The procedure should create the transaction and return the new TransactionId.
    """
    try:
        logger.info(
            "Creating recurring transaction",
            extra={
                "company_id": transaction_data.companyId,
                "subscription_id": transaction_data.subscriptionId,
                "provider": transaction_data.providerName,
            },
        )

        parameters = {
            "CompanyId": transaction_data.companyId,
            "DonorId": transaction_data.donorId,
            "ReviewDonorId": transaction_data.reviewDonorId,
            "StartDate": transaction_data.startDate,
            "Frequency": transaction_data.frequency,
            "FrequencyCount": transaction_data.frequencyCount,
            "EndDate": transaction_data.endDate,
            "ProviderName": transaction_data.providerName,
            "SubscriptionId": transaction_data.subscriptionId,
            "CustomerId": transaction_data.customerId,
            "PaymentMethodId": transaction_data.paymentMethodId,
            "PaymentMethod": transaction_data.paymentMethod,
            "TotalAmount": transaction_data.totalAmount,
            "Status": transaction_data.status,
            "LoggedUser": created_by,
        }

        output_params = {   
            "TransactionId": "int", 
        }

        # Remove None values
        parameters = {k: v for k, v in parameters.items() if v is not None}

        # Execute stored procedure
        results = await execute_stored_procedure_with_output(
            session=session,
            procedure_name="[dbo].[UIActionRecurringTransactions]",
            parameters=parameters,
            output_params=output_params,            
        )

        if results and len(results) > 0:
            transaction_id = results[1]['TransactionId']
            
            if transaction_id:
                logger.info(f"Recurring transaction created successfully: {transaction_id}")
                
                # Create detail line items if provided
                if transaction_data.details:
                    line_number = 1
                    for detail in transaction_data.details:
                        detail_parameters = {
                            "DataType": 11,
                            "CompanyId": transaction_data.companyId,
                            "TransactionId": transaction_id,
                            "LineNumber": line_number,
                            "DonationType": detail.donationType,
                            "PriceId": detail.priceId,
                            "ProductId": detail.productId,
                            "CauseId": detail.causeId,
                            "Amount": detail.amount,
                            "Currency": detail.currency,
                            "LoggedUser": created_by,
                        }
                        await execute_stored_procedure(
                            session=session,
                            procedure_name="[dbo].[UIActionRecurringTransactions]",
                            parameters=detail_parameters,
                            fetch_results=False
                        )
                        line_number += 1
                
                return transaction_id
            else:
                logger.error(f"Failed to create recurring transaction")
                return None

        logger.error("No result returned from stored procedure")
        return None

    except Exception as e:
        logger.error(f"Error creating recurring transaction: {str(e)}", exc_info=True)
        raise


async def get_recurring_transaction_old(
    session: AsyncSession,
    company_id: int,
    transaction_id: int,
    sub_id: Optional[str] = None,
    include_details: bool = True,
    include_payments: bool = True,
) -> Optional[RecurringTransactionDetailModel]:
    """
    Get a specific recurring transaction with optional details and payments.

    Args:
        session: Database session
        company_id: The company ID to which the transaction belongs
        transaction_id: The transaction ID to retrieve
        sub_id: The subscription ID associated with the recurring transaction (optional)
        include_details: Include transaction detail line items
        include_payments: Include payment history

    Returns:
        RecurringTransactionDetailModel with transaction, details, and payments, or None if not found
    """
    try:
        logger.info(f"Retrieving recurring transaction: {transaction_id}")

        # Get the main transaction record
        if sub_id:
            # we have subsription id use that to get the transaction
            stmt = select(RecurringTransactions).where(
                RecurringTransactions.SubscriptionId == sub_id and RecurringTransactions.CompanyId == company_id
            )
        else:
            stmt = select(RecurringTransactions).where(
                RecurringTransactions.TransactionId == transaction_id and RecurringTransactions.CompanyId == company_id
            )
        result = await session.execute(stmt)
        transaction = result.scalar_one_or_none()

        if not transaction:
            logger.warning(f"Recurring transaction not found: {transaction_id}")
            return None

        # Convert to Pydantic model
        #logger.info(f"db transaction: {transaction}")
        transaction_model = RecurringTransactionModel.model_validate(transaction)
        #logger.info(f"Converted transaction model: {transaction_model}")

        # Get details if requested
        details_models = []
        if include_details:
            details_stmt = select(RecurringTransactionDetails.TransactionId, RecurringTransactionDetails.LineNumber, RecurringTransactionDetails.DonationType, DonationType.DetailedTextHeader.label("Description"), RecurringTransactionDetails.Amount, RecurringTransactionDetails.Currency).join(
                                    DonationType, RecurringTransactionDetails.CompanyId == DonationType.CompanyId and 
                        RecurringTransactionDetails.DonationType == DonationType.DonationType).where(
                RecurringTransactionDetails.TransactionId == transaction_model.transactionId
            ).order_by(RecurringTransactionDetails.LineNumber)
            
            details_result = await session.execute(details_stmt)
            details = details_result.scalars().all()
            
            details_models = [
                RecurringTransactionDetailsModel.model_validate(detail)
                for detail in details
            ]

        # Get payments if requested
        payments_models = []
        if include_payments:
            payments_stmt = select(RecurringTransactionPayments).where(
                RecurringTransactionPayments.TransactionId == transaction_model.transactionId
            ).order_by(RecurringTransactionPayments.LineNumber)
            
            payments_result = await session.execute(payments_stmt)
            payments = payments_result.scalars().all()
            
            payments_models = [
                RecurringTransactionPaymentsModel.model_validate(payment)
                for payment in payments
            ]

        # Create the detail model
        detail_model = RecurringTransactionDetailModel(
            transaction=transaction_model,
            details=details_models,
            payments=payments_models,
        )

        logger.info(f"Retrieved recurring transaction {transaction_id} with {len(details_models)} details and {len(payments_models)} payments")
        return detail_model

    except Exception as e:
        logger.error(f"Error retrieving recurring transaction: {str(e)}", exc_info=True)
        raise

async def get_recurring_transaction(
    session: AsyncSession,
    company_id: int,
    transaction_id: int,
    sub_id: Optional[str] = None,
    include_details: bool = True,
    include_payments: bool = True,
) -> RecurringTransactionResponse:
    """
    Get all recurring transactions for a company.

    Args:
        session: Database session
        company_id: Company ID to filter by
        transaction_id: Transaction ID to filter by
        include_details: Whether to include transaction details
        include_payments: Whether to include transaction payments

    Returns:
        RecurringTransactionResponse with the transaction details and payment history
    """
    try:
        logger.info(
            f"Retrieving recurring transactions for company {company_id}",
            extra={"transaction_id": transaction_id}
        )

        parameters = {
            "DataType": -1,
            "CompanyId": company_id,
            "TransactionId": transaction_id if transaction_id != 0 else None,
            "SubscriptionId": sub_id if sub_id else None,
        }

        result = await execute_stored_procedure(
            session=session,
            procedure_name="[dbo].[UIQueryReccurringTransactions]",
            parameters=parameters,
            fetch_results=True,
        )

        if not result or len(result) == 0:
            logger.warning(
                "Recurring transactions stored procedure returned no results",
                extra={
                    "company_id": company_id,
                    "transaction_id": transaction_id,
                    "subscription_id": sub_id,
                }
            )
            return RecurringTransactionResponse(item=None, status="error")        
            
        if include_details:
            parameters["DataType"] = -2  # Get details by transaction ID
            details_result = await execute_stored_procedure(
                session=session,
                procedure_name="[dbo].[UIQueryReccurringTransactions]",
                parameters=parameters,
                fetch_results=True,
            )

        if include_payments:
            parameters["DataType"] = -3  # Get payments by transaction ID
            payments_result = await execute_stored_procedure(
                session=session,
                procedure_name="[dbo].[UIQueryReccurringTransactions]",
                parameters=parameters,
                fetch_results=True,
            )   
                    
        # Convert results to models
        transactions = []
        for row in result: # type: ignore
            transaction_model = RecurringTransactionModel(
                TransactionId=row.get("TransactionId"), # type: ignore
                CompanyId=row.get("CompanyId"), # type: ignore
                DonorId=row.get("DonorId"), # type: ignore
                ReviewDonorId=row.get("ReviewDonorId"), # type: ignore
                StartDate=row.get("StartDate"), # type: ignore
                Frequency=row.get("Frequency"), # type: ignore
                FrequencyDescription=_map_frequency_to_description(row.get("Frequency")), # type: ignore
                FrequencyCount=row.get("FrequencyCount"), # type: ignore
                EndDate=row.get("EndDate") or row.get("endDate"), # type: ignore
                ProviderName=row.get("ProviderName") or row.get("providerName"), # type: ignore
                SubscriptionId=row.get("SubscriptionId") or row.get("subscriptionId"), # type: ignore
                PaymentMethod=row.get("PaymentMethod") or row.get("paymentMethod"), # type: ignore
                TotalAmount=row.get("TotalAmount") or row.get("totalAmount"), # type: ignore
                Status=row.get("Status"),  # type: ignore
                details=[
                    RecurringTransactionDetailsModel(
                        TransactionId=detail_row.get("TransactionId"), # type: ignore
                        CompanyId=detail_row.get("CompanyId"), # type: ignore
                        LineNumber=detail_row.get("LineNumber"), # type: ignore
                        DonationType=detail_row.get("DonationType"), # type: ignore
                        Description=detail_row.get("Description"), # type: ignore
                        Amount=detail_row.get("Amount"), # type: ignore
                        Currency=detail_row.get("Currency"), # type: ignore
                    )                      for detail_row in details_result if detail_row.get("TransactionId") == row.get("TransactionId") # type: ignore       
                ] if include_details else [],
                payments=[  
                    RecurringTransactionPaymentsModel(
                        TransactionId=payment_row.get("TransactionId"), # type: ignore
                        LineNumber=payment_row.get("LineNumber"), # type: ignore
                        DonationReceiptId=payment_row.get("DonationReceiptId"), # type: ignore
                        ProviderId=payment_row.get("ProviderId"), # type: ignore
                        DonationDate=payment_row.get("DonationDate"), # type: ignore
                    ) for payment_row in payments_result if payment_row.get("TransactionId") == row.get("TransactionId") # type: ignore
                ] if include_payments else []
            )
            transactions.append(transaction_model)
        
        return RecurringTransactionResponse(
            item=transactions[0] if transactions else None,
            status="success"
        )

    except Exception as e:
        logger.error(f"Error retrieving recurring transactions: {str(e)}", exc_info=True)
        raise

async def get_recurring_transactions_by_criteria(
    session: AsyncSession,
    company_id: int,
    donor_id: Optional[int] = None,
    status_filter: Optional[int] = None,
    provider_name: Optional[str] = None,
    include_details: bool = True,
    include_payments: bool = True,
    transaction_id: Optional[int] = None,
) -> RecurringTransactionListResponse:
    """
    Get all recurring transactions for a company.

    Args:
        session: Database session
        company_id: Company ID to filter by
        donor_id: Optional donor ID to filter by
        status_filter: Optional status code to filter by (1=Active, 2=Canceled, etc.)
        provider_name: Optional provider name to filter by (e.g., 'Stripe')

    Returns:
        RecurringTransactionListResponse with list of transactions
    """
    try:
        logger.info(
            f"Retrieving recurring transactions for company {company_id}",
            extra={"status_filter": status_filter, "provider": provider_name}
        )

        parameters = {
            "DataType": 0 if donor_id is None else 1,  # 0=Get all for company, 1=Get for company and donor
            "CompanyId": company_id,
            "DonorId": donor_id if donor_id is not None else None,
            "TransactionId": transaction_id if transaction_id is not None else None,
        }
        if transaction_id is not None:
            parameters["DataType"] = -1  # Get by transaction ID

        result = await execute_stored_procedure(
            session=session,
            procedure_name="[dbo].[UIQueryReccurringTransactions]",
            parameters=parameters,
            fetch_results=True,
        )

        if not result or len(result) == 0:
            logger.warning(
                "Recurring transactions stored procedure returned no results",
                extra={
                    "company_id": company_id,
                    "donor_id": donor_id
                }
            )
            return RecurringTransactionListResponse(count=0, items=[], status="error")
        
            
        if include_details:
            if transaction_id is not None:
                parameters["DataType"] = -2  # Get details by transaction ID
            else:   
                parameters["DataType"] = 2  # Get details
            details_result = await execute_stored_procedure(
                session=session,
                procedure_name="[dbo].[UIQueryReccurringTransactions]",
                parameters=parameters,
                fetch_results=True,
            )

        if include_payments:
            if transaction_id is not None:
                parameters["DataType"] = -3  # Get payments by transaction ID
            else:
                parameters["DataType"] = 3  # Get payments
            payments_result = await execute_stored_procedure(
                session=session,
                procedure_name="[dbo].[UIQueryReccurringTransactions]",
                parameters=parameters,
                fetch_results=True,
            )   
                    
        # Convert results to models
        transactions = []
        for row in result: # type: ignore
            transaction_model = RecurringTransactionModel(
                TransactionId=row.get("TransactionId"), # type: ignore
                CompanyId=row.get("CompanyId"), # type: ignore
                DonorId=row.get("DonorId"), # type: ignore
                ReviewDonorId=row.get("ReviewDonorId"), # type: ignore
                StartDate=row.get("StartDate"), # type: ignore
                Frequency=row.get("Frequency"), # type: ignore
                FrequencyDescription=_map_frequency_to_description(row.get("Frequency")), # type: ignore
                FrequencyCount=row.get("FrequencyCount"), # type: ignore
                EndDate=row.get("EndDate") or row.get("endDate"), # type: ignore
                ProviderName=row.get("ProviderName") or row.get("providerName"), # type: ignore
                SubscriptionId=row.get("SubscriptionId") or row.get("subscriptionId"), # type: ignore
                PaymentMethod=row.get("PaymentMethod") or row.get("paymentMethod"), # type: ignore
                TotalAmount=row.get("TotalAmount") or row.get("totalAmount"), # type: ignore
                Status=row.get("Status"),  # type: ignore
                details=[
                    RecurringTransactionDetailsModel(
                        TransactionId=detail_row.get("TransactionId"), # type: ignore
                        CompanyId=detail_row.get("CompanyId"), # type: ignore
                        LineNumber=1, # type: ignore
                        DonationType=detail_row.get("DonationType"), # type: ignore
                        Description=detail_row.get("Description"), # type: ignore
                        Amount=detail_row.get("Amount"), # type: ignore
                        Currency=detail_row.get("Currency"), # type: ignore
                    )                      for detail_row in details_result if detail_row.get("TransactionId") == row.get("TransactionId") # type: ignore       
                ] if include_details else [],
                payments=[  
                    RecurringTransactionPaymentsModel(
                        TransactionId=payment_row.get("TransactionId"), # type: ignore
                        LineNumber=payment_row.get("LineNumber"), # type: ignore
                        DonationReceiptId=payment_row.get("DonationReceiptId"), # type: ignore
                        ProviderId=payment_row.get("ProviderId"), # type: ignore
                        DonationDate=payment_row.get("DonationDate"), # type: ignore
                    ) for payment_row in payments_result if payment_row.get("TransactionId") == row.get("TransactionId") # type: ignore
                ] if include_payments else []
            )
            transactions.append(transaction_model)

        # Apply additional filters if not using stored procedure
        if status_filter is not None and transactions:
            transactions = [tx for tx in transactions if tx.status == status_filter]
        
        if provider_name and transactions:
            transactions = [tx for tx in transactions if tx.providerName == provider_name]

        logger.info(f"Retrieved {len(transactions)} recurring transactions for company {company_id}")
        
        return RecurringTransactionListResponse(
            count=len(transactions),
            items=transactions,
            status="success"
        )

    except Exception as e:
        logger.error(f"Error retrieving recurring transactions: {str(e)}", exc_info=True)
        raise


async def update_recurring_transaction(
    session: AsyncSession,
    transaction_id: int,
    transaction_data: RecurringTransactionUpdateModel,
    modified_by: int = 0,
) -> bool:
    """
    Update an existing recurring transaction using stored procedure.

    Args:
        session: Database session
        transaction_id: Transaction ID to update
        transaction_data: Transaction update data
        modified_by: User ID who is modifying the transaction (default: 0 for system)

    Returns:
        True if successful, False otherwise
    """
    try:
        logger.info(
            f"Updating recurring transaction {transaction_id}",
            extra={"modified_by": modified_by}
        )

        parameters = {
            "TransactionId": transaction_id,
            "DonorId": transaction_data.donorId,
            "ReviewDonorId": transaction_data.reviewDonorId,
            "EndDate": transaction_data.endDate,
            "PaymentMethod": transaction_data.paymentMethod,
            "TotalAmount": transaction_data.totalAmount,
            "Status": transaction_data.status,
            "ModifiedBy": modified_by,
        }

        # Remove None values to avoid overwriting with NULL
        parameters = {k: v for k, v in parameters.items() if v is not None}

        # Execute stored procedure
        result = await execute_stored_procedure(
            session=session,
            procedure_name="[dbo].[sp_UpdateRecurringTransaction]",
            parameters=parameters,
            fetch_results=True,
        )

        if result and len(result) > 0:
            success = result[0].get("Success") or result[0].get("success")
            if success:
                logger.info(f"Recurring transaction {transaction_id} updated successfully")
                return True
            else:
                error_msg = result[0].get("Message") or result[0].get("message", "Unknown error")
                logger.error(f"Failed to update recurring transaction: {error_msg}")
                return False

        logger.error("No result returned from stored procedure")
        return False

    except Exception as e:
        logger.error(f"Error updating recurring transaction: {str(e)}", exc_info=True)
        raise


async def get_recurring_transaction_by_subscription_id(
    session: AsyncSession,
    company_id: int,
    subscription_id: str,
) -> Optional[RecurringTransactionModel]:
    """
    Get a recurring transaction by Stripe subscription ID.

    Args:
        session: Database session
        subscription_id: Stripe subscription ID
        company_id: Company ID for filtering

    Returns:
        RecurringTransactionModel if found, None otherwise
    """
    try:
        logger.info(f"Retrieving recurring transaction by subscription ID: {subscription_id}")

        stmt = select(RecurringTransactions).where(
            RecurringTransactions.CompanyId == company_id,
            RecurringTransactions.SubscriptionId == subscription_id
        )

        result = await session.execute(stmt)
        transaction = result.scalar_one_or_none()

        if not transaction:
            logger.info(f"No recurring transaction found for subscription ID: {subscription_id}")
            return None

        transaction_model = RecurringTransactionModel.model_validate(transaction)
        logger.info(f"Found recurring transaction {transaction_model.transactionId} for subscription {subscription_id}")
        
        return transaction_model

    except Exception as e:
        logger.error(f"Error retrieving recurring transaction by subscription ID: {str(e)}", exc_info=True)
        raise

async def add_recurring_transaction_payment(
    session: AsyncSession,
    transaction_id: int,
    donation_receipt_id: int,
) -> bool:
    """
    Link a donation receipt to a recurring transaction (track payment).

    Args:
        session: Database session
        transaction_id: Recurring transaction ID
        donation_receipt_id: Donation receipt ID from processed payment

    Returns:
        True if successful, False otherwise
    """
    try:
        logger.info(f"Adding payment record for transaction {transaction_id}, receipt {donation_receipt_id}")

        # Get the next line number
        stmt = select(RecurringTransactionPayments).where(
            RecurringTransactionPayments.TransactionId == transaction_id
        )
        result = await session.execute(stmt)
        payments = result.scalars().all()
        next_line_number = len(payments) + 1

        # Create payment record directly (no stored procedure needed for simple insert)
        payment = RecurringTransactionPayments(
            TransactionId=transaction_id,
            LineNumber=next_line_number,
            DonationReceiptId=donation_receipt_id,
        )
        session.add(payment)
        await session.flush()

        logger.info(f"Payment record added successfully")
        return True

    except Exception as e:
        logger.error(f"Error adding payment record: {str(e)}", exc_info=True)
        raise


async def cancel_recurring_transaction(
    session: AsyncSession,
    transaction_id: int,
    end_date: Optional[datetime] = None,
    modified_by: int = 0,
) -> bool:
    """
    Cancel a recurring transaction by setting status to canceled and end date.

    Args:
        session: Database session
        transaction_id: Transaction ID to cancel
        end_date: Optional end date (defaults to current date/time)
        modified_by: User ID who is canceling the transaction

    Returns:
        True if successful, False otherwise
    """
    try:
        logger.info(f"Canceling recurring transaction {transaction_id}")

        update_data = RecurringTransactionUpdateModel(
            status=2,  # Canceled status
            endDate=end_date or datetime.utcnow(),
        )

        return await update_recurring_transaction(
            session=session,
            transaction_id=transaction_id,
            transaction_data=update_data,
            modified_by=modified_by,
        )

    except Exception as e:
        logger.error(f"Error canceling recurring transaction: {str(e)}", exc_info=True)
        raise

def _map_frequency_to_description(frequency: Optional[int]) -> Optional[str]:
    """
    Map frequency code to human-readable description.

    Args:
        frequency: Frequency code (1=Monthly, 2=Yearly, etc.)

    Returns:
        Description string or None if unknown
    """
    if frequency is None:
        return None
    
    mapping = {
        1: "Monthly",
        2: "Yearly",
        3: "Weekly",
        4: "Biweekly",
        5: "Quarterly",
        6: "Half-Yearly",
    }
    return mapping.get(frequency)