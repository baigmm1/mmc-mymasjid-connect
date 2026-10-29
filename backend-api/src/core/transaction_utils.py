"""
Transaction utility functions for retrieving and managing transaction data.

Provides helper functions for:
- Retrieving transactions by different identifiers (transactionId, providerId, providerToken)
- Building transaction models from database results
- Saving/updating donor information from transaction data
"""

from datetime import datetime
from typing import Optional, Any, Dict
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from src.config import settings
from src.core.logging import get_logger
from src.core.stored_procedure_utils import execute_stored_procedure, execute_stored_procedure_with_output
from src.models.transaction import TransactionModel, TransactionDetailsModel
from src.models.donors import DonorsModel
from src.core.donors_utils import find_donor_by_email, get_donor_by_id
from src.core.provider_manager import StripePaymentProvider
from src.models.bank_deposit_batch import BankDepositBatchCreateModel, BankDepositBatchTransactionCreateModel
from src.core.bank_deposit_batch_utils import create_bank_deposit_batch
from src.core.recurring_transactions_utils import get_recurring_transaction
from src.core.payment_utils import get_transaction_description
import stripe

logger = get_logger(__name__, level=settings.LOG_LEVEL)


async def get_transaction_by_criteria(
    session: AsyncSession,
    company_id: int,
    transaction_id: Optional[int] = None,
    provider_id: Optional[str] = None,
    provider_token: Optional[str] = None,
    provider_agreement_id: Optional[str] = None,
    provider_plan_id: Optional[str] = None
) -> Optional[TransactionModel]:
    """
    Retrieve a transaction from the database using various criteria.
    
    This function can search for transactions using:
    - transaction_id (donationReceiptId)
    - provider_id
    - provider_token (checkout session ID or payment intent ID)
    
    Args:
        session: Database session
        company_id: Company ID for the transaction
        transaction_id: Transaction/Donation Receipt ID (optional)
        provider_id: Provider ID (optional)
        provider_token: Provider token/session ID (optional)
        
    Returns:
        TransactionModel with complete details if found, None otherwise
        
    Raises:
        ValueError: If no search criteria provided or multiple criteria provided
        
    Example:
        # Get by transaction ID
        transaction = await get_transaction_by_criteria(
            session=session,
            company_id=1,
            transaction_id=12345
        )
        
        # Get by provider token (e.g., Stripe session ID)
        transaction = await get_transaction_by_criteria(
            session=session,
            company_id=1,
            provider_token="cs_test_1234567890"
        )
    """
    # Validate that exactly one search criterion is provided
    criteria_count = sum([
        transaction_id is not None,
        provider_id is not None,
        provider_token is not None,
        provider_agreement_id is not None,
        provider_plan_id is not None
    ])
    
    if criteria_count == 0:
        raise ValueError("At least one search criterion must be provided")
    
    if criteria_count > 1:
        raise ValueError("Only one search criterion can be provided at a time")
    
    logger.info(
        "Retrieving transaction by criteria",
        extra={
            "company_id": company_id,
            "transaction_id": transaction_id,
            "provider_id": provider_id,
            "provider_token": provider_token,
            "provider_agreement_id": provider_agreement_id,
            "provider_plan_id": provider_plan_id
        }
    )
    
    try:
        # Build parameters based on search criteria
        if transaction_id:
            # Search by donation receipt ID
            parameters = {
                "DataType": -9,  # Get transaction header
                "DonationReceiptId": transaction_id,
            }
        elif provider_id:
            # Search by provider ID
            parameters = {
                "DataType": -9,  # Get by provider ID
                "CompanyId": company_id,
                "ProviderId": provider_id,
            }
        elif provider_token:  # provider_token
            # Search by provider token
            parameters = {
                "DataType": -9,  # Get by provider token
                "CompanyId": company_id,
                "ProviderToken": provider_token,
            }
        elif provider_agreement_id:  # provider_agreement_id
            # Search by provider agreement ID
            parameters = {
                "DataType": -9,  # Get by provider agreement ID
                "CompanyId": company_id,
                "ProviderAgreementId": provider_agreement_id,
            }
        elif provider_plan_id:  # provider_plan_id
            # Search by provider plan ID
            parameters = {
                "DataType": -9,  # Get by provider plan ID
                "CompanyId": company_id,
                "ProviderPlanId": provider_plan_id,
            }
        
        # Retrieve transaction header
        result = await execute_stored_procedure(
            session=session,
            procedure_name="[dbo].[UIQueryGetDonations]",
            parameters=parameters,
            fetch_results=True,
            fetch_multiple=False
        )
        
        if not result or len(result) == 0:
            logger.warning(
                "Transaction not found",
                extra={
                    "company_id": company_id,
                    "transaction_id": transaction_id,
                    "provider_id": provider_id,
                    "provider_token": provider_token,
                    "provider_agreement_id": provider_agreement_id,
                }
            )
            return None
        
        # Parse transaction data - result is a list, get first element
        transaction_data: dict = result[0]  # type: ignore # Type hint to help linter
        actual_transaction_id = transaction_data.get('DonationReceiptId')
        
        if not actual_transaction_id:
            logger.error("Transaction ID not found in result")
            return None
        
        # Retrieve transaction details
        detail_parameters = {
            "DataType": -10,  # Get transaction details
            "DonationReceiptId": actual_transaction_id,
        }
        
        detail_result = await execute_stored_procedure(
            session=session,
            procedure_name="[dbo].[UIQueryGetDonations]",
            parameters=detail_parameters,
            fetch_results=True,
            fetch_multiple=False
        )
        
        if not detail_result or len(detail_result) == 0:
            logger.warning(
                f"Transaction details not found for transaction {actual_transaction_id}"
            )
            transaction_details = []
        else:
            transaction_details = detail_result
        
        # Convert datetime to ISO format string if needed
        donation_date = transaction_data.get('DonationDate')
        if isinstance(donation_date, datetime):
            donation_date = donation_date.isoformat()
        elif not donation_date:
            donation_date = datetime.now().isoformat()
        
        # Build transaction model with all required fields
        transaction = TransactionModel(
            transactionId=actual_transaction_id,
            companyId=transaction_data.get('CompanyId', company_id),
            terminalId=transaction_data.get('Provider'),
            donorId=transaction_data.get('DonorId'),
            donorName=transaction_data.get('DonorName'),
            donorPhone=transaction_data.get('DonorPhoneNumber'),
            donorEmail=transaction_data.get('DonorEMail'),
            donorBillingZip=transaction_data.get('DonorPostalCode'),
            transactionDate=donation_date,
            purposeId=transaction_data.get('Purpose', 1),
            totalAmount=float(transaction_data.get('TotalAmount', 0)),
            currency=transaction_data.get('Currency', 'USD'),
            recurring=transaction_data.get('Recurring', False),
            recurringFrequency=transaction_data.get('Frequency', 1),
            numberofMonths=transaction_data.get('NumberofMonths'),
            paymentMethod=transaction_data.get('PaymentMethodText', 'Credit Card'),
            paymentMethodId=transaction_data.get('PaymentMethod'),
            provider=transaction_data.get('Provider'),
            providerName=transaction_data.get('ProviderName'),
            providerId=transaction_data.get('ProviderId'),
            providerToken=transaction_data.get('ProviderToken'),
            successUrl=None,
            cancelUrl=None,
            checkoutUrl=None,
            status="completed",
            statusCode=transaction_data.get('StatusCode', 2),
            donorDetails= None,
            details=[
                TransactionDetailsModel(
                    lineNumber=int(detail.get('LineNumber', 0)), # type: ignore
                    description=detail.get('DonationTypeText'),  # type: ignore
                    donationTypeId=int(detail.get('DonationType', 0)), # type: ignore
                    amount=float(detail.get('Amount', 0)), # type: ignore
                    feePercent=0.0,
                    feeAmount=0.0
                ) 
                for detail in transaction_details
            ]
        )
        transaction.DonorDetails = await build_donor_from_transaction(transaction_data)
        
        logger.info(
            "Transaction retrieved successfully",
            extra={
                "transaction_id": actual_transaction_id,
                "company_id": company_id,
                "donor_email": transaction.DonorEmail  # type: ignore
            }
        )
        
        return transaction
        
    except Exception as e:
        logger.error(
            f"Error retrieving transaction: {str(e)}",
            extra={
                "error": str(e),
                "error_type": type(e).__name__,
                "company_id": company_id,
                "transaction_id": transaction_id,
            },
            exc_info=True,
        )
        raise


async def update_transaction_status(
    transaction_id: int,
    provider_id: str,
    status_code: int,
    subscription_id: Optional[str],
    customer_id: Optional[str],
    payment_method_id: Optional[str],
    plan_id: Optional[str],    
    end_date: Optional[datetime],
    payment_method: Optional[str],   
    session: AsyncSession,
    logged_in_user_id: int = -1
) -> None:
    """
    Update the status code of an existing transaction.
    
    This function updates only the status code of a transaction using the
    UIActionCreateDonation stored procedure with DataType = 5.
    
    Args:
        transaction_id: Transaction/Donation Receipt ID to update
        status_code: New status code to set (1=pending, 2=completed, 3=failed, etc.)
        session: Database session
        
    Returns:
        None
        
    Raises:
        ValueError: If transaction_id or status_code is invalid
        Exception: If stored procedure execution fails
        
    Example:
        # Mark transaction as completed
        await update_transaction_status(
            transaction_id=12345,
            status_code=2,
            session=session
        )
        
        # Mark transaction as failed
        await update_transaction_status(
            transaction_id=12345,
            status_code=3,
            session=session
        )
    """
    if not transaction_id or transaction_id <= 0:
        raise ValueError("transaction_id must be a positive integer")
    
    if not status_code or status_code <= 0:
        raise ValueError("status_code must be a positive integer")
    
    logger.info(
        "Updating transaction status",
        extra={
            "transaction_id": transaction_id,
            "status_code": status_code,
        }
    )
    
    try:
        # Prepare parameters for stored procedure
        parameters = {
            "DataType": 5,
            "DonationReceiptId": transaction_id,
            "ProviderId": provider_id,
            "ProviderPlanId": plan_id,
            "ProviderAgreementId": subscription_id,
            "CustomerId": customer_id,
            "PaymentMethodId": payment_method_id,
            "StatusCode": status_code,
            "EndDate": end_date.isoformat() if end_date else None,
            "ProviderToken": payment_method,
            "LoggedUserId": logged_in_user_id
        }

        # Execute stored procedure to update status
        await execute_stored_procedure(
            session=session,
            procedure_name="dbo.UIActionCreateDonation",
            parameters=parameters,
            fetch_results=False
        )
        
        logger.info(
            "Transaction status updated successfully",
            extra={
                "transaction_id": transaction_id,
                "status_code": status_code
            }
        )
        
    except Exception as e:
        logger.error(
            f"Error updating transaction status: {str(e)}",
            extra={
                "error": str(e),
                "error_type": type(e).__name__,
                "transaction_id": transaction_id,
                "status_code": status_code
            },
            exc_info=True,
        )
        raise


async def build_donor_from_transaction(
    transaction_data: dict
) -> DonorsModel:
    """
    Build a DonorsModel from transaction data retrieved from the database.
    
    Args:
        transaction_data: Dictionary containing transaction data from stored procedure
        
    Returns:
        DonorsModel populated with donor information from transaction
        
    Example:
        donor = await build_donor_from_transaction(transaction_data)
    """
    donor_id = transaction_data.get('DonorId')
    
    return DonorsModel(
        donorId=donor_id if donor_id else 0,
        namePrefix=transaction_data.get('DonorNamePrefix'),
        firstName=None,
        middleName=None,
        lastName=None,
        suffix=None,
        completeName=transaction_data.get('DonorName') or "Valued Donor",
        companyName=None,
        taxReceiptName=None,
        addressLine1=transaction_data.get('DonorAddressLine1'),
        addressLine2=transaction_data.get('DonorAddressLine2'),
        city=transaction_data.get('DonorCity'),
        state=transaction_data.get('DonorState'),
        postalCode=transaction_data.get('DonorPostalCode'),
        countryCode=transaction_data.get('DonorCountryCode'),
        phoneNumber=transaction_data.get('DonorPhoneNumber'),
        eMail=transaction_data.get('DonorEMail'),
        occupation=None,
        physician=None,
        incorrectAddress=None,
        publishinDonorList=None,
        taxReceiptRequired=None,
        statusCode=None,
        createdBy=None,
        createdDate=None,
        modifiedBy=None,
        modifiedDate=None
    )


async def get_transaction_by_provider_token(
    session: AsyncSession,
    provider_token: str,
    company_id: Optional[int] = None
) -> Optional[TransactionModel]:
    """
    Retrieve a transaction by provider token (e.g., Stripe checkout session ID).
    
    This is a convenience wrapper around get_transaction_by_criteria for the common
    case of looking up transactions by provider token.
    
    Args:
        session: Database session
        provider_token: Provider token/session ID
        company_id: Optional company ID for filtering (recommended for performance)
        
    Returns:
        TransactionModel if found, None otherwise
        
    Example:
        transaction = await get_transaction_by_provider_token(
            session=session,
            provider_token="cs_test_1234567890",
            company_id=1
        )
    """
    if not company_id:
        # If no company_id provided, we need to search across all companies
        # This is less efficient but necessary if company_id is unknown
        logger.warning(
            "get_transaction_by_provider_token called without company_id, "
            "performance may be impacted"
        )
        company_id = 0  # Use 0 or implement a different stored procedure
    
    return await get_transaction_by_criteria(
        session=session,
        company_id=company_id,
        provider_token=provider_token
    )


async def create_transaction_in_database(
    transaction: TransactionModel,    
    session: AsyncSession,
    logged_in_user_id: int = -1
) -> TransactionModel:
    """
    Create a new transaction record in the database.
    
    This function handles the complete transaction creation workflow including:
    - Executing stored procedures to create the transaction header
    - Adding all transaction detail line items
    - Recalculating totals
    - Optionally sending receipt email
    
    Args:
        transaction: Transaction data model with all required fields
        session: Database session
        logged_in_user_id: ID of the currently logged-in user (optional)
    Returns:
        TransactionModel with updated transactionId after creation
        
    Raises:
        ValueError: If required transaction data is missing
        Exception: If stored procedure execution fails
        
    Example:
        transaction = TransactionModel(
            companyId=1,
            donorId=123,
            donorName="John Doe",
            transactionDate="2025-12-18T10:30:00Z",
            totalAmount=100.00,
            details=[...]
        )
        created_transaction = await create_transaction_in_database(
            transaction=transaction,
            session=session,
        )
    """
    logger.info(
        "Creating transaction in database",
        extra={
            "company_id": transaction.CompanyId,
            "donor_id": transaction.DonorId,
            "total_amount": transaction.TotalAmount,
        }
    )
    
    try:
        # Build description based on purpose
        if transaction.Description is None:
            transaction.Description = get_transaction_description(transaction=transaction)
        # if transaction.PurposeId == 1:
        #     description = f"Donation from {transaction.DonorName}" if transaction.DonorName else "Donation"
        # else:
        #     description = f"Payment for Service from {transaction.DonorName}" if transaction.DonorName else "Payment for Service"

        # Prepare parameters for stored procedure
        parameters = {
            "DataType": 1,            
            "CompanyId": transaction.CompanyId,
            "DonorId": transaction.DonorId,
            "CompleteName": transaction.DonorName,
            "AddressLine1": transaction.DonorDetails.AddressLine1 if transaction.DonorDetails else None,
            "AddressLine2": transaction.DonorDetails.AddressLine2 if transaction.DonorDetails else None,
            "City": transaction.DonorDetails.City if transaction.DonorDetails else None,
            "State": transaction.DonorDetails.State if transaction.DonorDetails else None,
            "PostalCode": transaction.DonorDetails.PostalCode if transaction.DonorDetails else None,
            "CountryCode": transaction.DonorDetails.CountryCode if transaction.DonorDetails else None,  
            "Description": transaction.Description,
            "DonationDate": transaction.TransactionDate,
            "PaymentMethod": transaction.PaymentMethodId,
            "Provider": transaction.Provider,
            "ProviderName": transaction.TerminalId if transaction.TerminalId else transaction.ProviderName,
            "ProviderId": transaction.ProviderId,
            "ProviderToken": transaction.ProviderToken,
            "ProviderPlanId": transaction.ProviderPlanId,
            "ProviderAgreementId": transaction.ProviderAgreementId, 
            "PhoneNumber": transaction.DonorPhone,
            "EMail": transaction.DonorEmail,
            "Purpose": transaction.PurposeId,
            "Recurring": 1 if transaction.Recurring else 0,
            "Frequency": transaction.RecurringFrequency if (transaction.Recurring and transaction.RecurringFrequency) else (1 if transaction.Recurring else 0),
            "RecurringCount": transaction.NumberofMonths if transaction.Recurring else 0,
            "StatusCode": transaction.StatusCode or 1,
            "LoggedUserId": logged_in_user_id
        }
        
        output_params = {   
            "DonationReceiptId": "int", 
        }

        # Remove None values
        parameters = {k: v for k, v in parameters.items() if v is not None}

        # Execute stored procedure to create transaction header
        logger.info("Executing UIActionCreateDonation stored procedure")
        results = await execute_stored_procedure_with_output(
            session=session,
            procedure_name="dbo.UIActionCreateDonation",
            parameters=parameters,
            output_params=output_params
        )
        
        transaction_id = results[1]['DonationReceiptId']
        transaction.TransactionId = transaction_id
        
        logger.info(
            f"Transaction header created with ID: {transaction_id}",
            extra={"transaction_id": transaction_id}
        )

        # Add transaction details
        if transaction.Details:
            logger.info(
                f"Adding {len(transaction.Details)} transaction details",
                extra={"transaction_id": transaction_id, "detail_count": len(transaction.Details)}
            )
            
            for detail in transaction.Details:
                detail_params = {
                    "DataType": 11,
                    "DonationReceiptId": transaction_id,
                    "LineNo": detail.LineNumber,
                    "CompanyId": transaction.CompanyId,
                    "DonationType": detail.DonationTypeId,
                    "Amount": float(detail.Amount),
                    "Currency": transaction.Currency or "USD",
                    "LineDescription": detail.Description,
                    "PriceId": detail.PriceId,
                    "LoggedUserId": logged_in_user_id
                }
                await execute_stored_procedure(
                    session=session,
                    procedure_name="dbo.UIActionCreateDonation",
                    parameters=detail_params,
                    fetch_results=False
                )

            # Recalculate totals
            logger.info(f"Recalculating totals for transaction {transaction_id}")
            recalc_params = {
                "DataType": 99,
                "DonationReceiptId": transaction_id,
                "LoggedUserId": logged_in_user_id
            }
            await execute_stored_procedure(
                session=session,
                procedure_name="dbo.UIActionCreateDonation",
                parameters=recalc_params,
                fetch_results=False
            )

        logger.info(
            "Transaction created successfully in database",
            extra={
                "transaction_id": transaction.TransactionId,
                "company_id": transaction.CompanyId,
            }
        )

        return transaction
        
    except Exception as e:
        logger.error(
            f"Error creating transaction in database: {str(e)}",
            extra={
                "error": str(e),
                "error_type": type(e).__name__,
                "company_id": transaction.CompanyId,
            },
            exc_info=True,
        )
        raise


async def create_transaction_from_stripe_checkout_session(
    session: AsyncSession,
    checkout_session: stripe.checkout.Session,
    company_id: int,
    event_id: Optional[str] = None,
) -> TransactionModel:
    """
    Create a transaction from a Stripe checkout session.
    
    This utility function handles the complete workflow of creating a transaction
    from a Stripe checkout session, including:
    - Checking for duplicate transactions
    - Finding or creating donor from customer details
    - Building transaction with line items
    - Saving to database
    
    This function can be called from:
    - Webhook handlers (checkout.session.completed)
    - Direct API calls after checkout
    - Testing/debugging tools
    
    Args:
        session: Database session
        checkout_session: Stripe checkout session object (expanded with line_items, customer)
        company_id: Company ID for the transaction
        event_id: Optional webhook event ID for logging
        
    Returns:
        TransactionModel: Created transaction with ID populated
        
    Raises:
        ValueError: If checkout session is invalid or missing required fields
        Exception: If transaction creation fails
        
    Example:
        from src.core.provider_manager import get_stripe_provider
        from src.core.transaction_utils import create_transaction_from_stripe_checkout_session
        
        # Get Stripe provider
        stripe_provider = await get_stripe_provider(session, company_id)
        
        # Retrieve checkout session from Stripe
        checkout_session = await stripe_provider.get_checkout_session(
            session_id="cs_test_123",
            expand=["line_items", "customer"]
        )
        
        # Create transaction
        transaction = await create_transaction_from_stripe_checkout_session(
            session=session,
            checkout_session=checkout_session,
            company_id=company_id
        )
    """
    if not checkout_session:
        raise ValueError("checkout_session is required")
    
    checkout_session_id = checkout_session.id
    payment_intent = checkout_session.payment_intent
    
    logger.info(
        f"Creating transaction from Stripe checkout session {checkout_session_id}",
        extra={
            "session_id": checkout_session_id,
            "payment_intent": payment_intent,
            "company_id": company_id,
            "event_id": event_id
        }
    )
    
    # Check if transaction already exists by session ID
    existing_transaction = await get_transaction_by_criteria(
        session=session,
        company_id=company_id,
        provider_token=checkout_session_id
    )
    if existing_transaction:
        logger.info(
            f"Transaction already exists for session {checkout_session_id}",
            extra={
                "transaction_id": existing_transaction.TransactionId,
                "session_id": checkout_session_id,
                "company_id": company_id
            }
        )
        return existing_transaction
    
    # Check by payment intent
    if payment_intent:
        existing_transaction = await get_transaction_by_criteria(
            session=session,
            company_id=company_id,
            provider_id=payment_intent # type: ignore
        )
        if existing_transaction:
            logger.info(
                f"Transaction already exists for payment intent {payment_intent}",
                extra={
                    "transaction_id": existing_transaction.TransactionId,
                    "payment_intent": payment_intent,
                    "company_id": company_id
                }
            )
            return existing_transaction
    
    # Get customer details
    customer_email = checkout_session.customer_details.email if checkout_session.customer_details else None
    customer_details = checkout_session.customer_details
    
    # Find or create donor
    donor = await find_donor_by_email(session, customer_email) if customer_email else None
    donor_id = donor.DonorId if donor else 0
    
    if not donor and customer_details:
        # Create donor model (not saving to DB yet, will be saved with transaction)
        donor = DonorsModel(
            donorId=0,
            namePrefix="",
            completeName=customer_details.name if customer_details else "",
            firstName="",
            middleName="",
            lastName="",
            suffix="",
            companyName="",
            taxReceiptName="",
            addressLine1=customer_details.address.line1 if customer_details and customer_details.address else "",
            addressLine2=customer_details.address.line2 if customer_details and customer_details.address else "",
            city=customer_details.address.city if customer_details and customer_details.address else "",
            state=customer_details.address.state if customer_details and customer_details.address else "",
            postalCode=customer_details.address.postal_code if customer_details and customer_details.address else "",
            countryCode=customer_details.address.country if customer_details and customer_details.address else "",
            phoneNumber="",
            eMail=customer_email or "",
            occupation="",
            physician=False,
            incorrectAddress=False,
            publishinDonorList=False,
            taxReceiptRequired=False,
            statusCode=1,
            createdBy=0,
            createdDate=datetime.utcnow(),
            modifiedBy=0,
            modifiedDate=datetime.utcnow(),
        )
    
    # Build transaction model
    transaction = TransactionModel(
        transactionId=0,
        description=None,
        companyId=company_id,
        terminalId="",
        donorId=donor_id,
        donorName=donor.CompleteName if donor else "",
        donorPhone="",
        donorEmail=customer_email or "",
        donorBillingZip=donor.PostalCode if donor else "",
        transactionDate=datetime.fromtimestamp(checkout_session.created).isoformat() if checkout_session.created else datetime.utcnow().isoformat(),
        purposeId=1,
        totalAmount=checkout_session.amount_total / 100 if checkout_session.amount_total else 0,  # Convert from cents
        currency=checkout_session.currency.upper() if checkout_session.currency else "USD",
        recurring=False,
        numberofMonths=0,
        paymentMethod="stripe",
        paymentMethodId=4,
        provider="Stripe",
        providerName=event_id or checkout_session_id,
        providerId=payment_intent, # type: ignore
        providerToken=checkout_session_id,
        successUrl=None,
        cancelUrl=None,
        checkoutUrl=None,
        status="completed",
        statusCode=2,
        donorDetails=donor if donor else None,  # type: ignore
        details=[],
    )
    
    # Add line items as transaction details
    line_items = checkout_session.line_items.data if checkout_session.line_items and checkout_session.line_items.data else []
    details = []
    for line_no, line_item in enumerate(line_items, start=1):
        transaction_detail = TransactionDetailsModel(
            lineNumber=line_no,
            description=line_item.description,
            donationTypeId=0,
            amount=line_item.amount_total / 100 if line_item.amount_total else 0,  # Convert from cents
            feePercent=0,
            feeAmount=0,
            priceId=line_item.price.id if line_item.price else None,
            productId=None
        )
        details.append(transaction_detail)
    
    transaction.Details = details
    
    # Save transaction to database
    transaction = await create_transaction_in_database(
        session=session,
        transaction=transaction
    )
    
    logger.info(
        f"Transaction created successfully from checkout session {checkout_session_id}",
        extra={
            "transaction_id": transaction.TransactionId,
            "session_id": checkout_session_id,
            "company_id": company_id
        }
    )
    
    return transaction


async def process_stripe_invoice_paid(
    session: AsyncSession,
    invoice_data: stripe.Invoice,
    company_id: int,
    stripe_provider: StripePaymentProvider,
    event_id: Optional[str] = None,
) -> TransactionModel:
    """
    Process a Stripe invoice.paid event.
    
    This utility function handles invoice payment processing, including:
    - Validating invoice data
    - Updating invoice status in database
    - Sending receipt emails
    - Updating customer billing status
    
    This function can be called from:
    - Webhook handlers (invoice.paid)
    - Direct API calls for testing
    - Scheduled jobs for processing pending invoices
    
    Args:
        session: Database session
        invoice_data: Stripe invoice object data
        company_id: Company ID for the transaction
        event_id: Optional webhook event ID for logging
        
    Returns:
        TransactionModel
        
    Example:
        result = await process_stripe_invoice_paid(
            session=session,
            invoice_data=webhook_data.data.get("object", {}),
            company_id=company_id,
            event_id=webhook_data.id
        )
    """
    invoice_id = invoice_data.id
    customer_id = invoice_data.customer.get("id") if isinstance(invoice_data.customer, dict) else invoice_data.customer
    amount_paid = invoice_data.amount_paid / 100 if invoice_data.amount_paid else 0  # Convert from cents
    payment_intent = stripe_provider.extract_payment_intent_id(invoice_data)    
    logger.info(
        f"Processing invoice.paid for invoice {invoice_id}",
        extra={
            "event_id": event_id,
            "invoice_id": invoice_id,
            "customer_id": customer_id,
            "amount_paid": amount_paid,
            "company_id": company_id
        }
    )
    
    existing_transaction = await get_transaction_by_criteria(
        session=session,
        company_id=company_id,
        provider_plan_id=invoice_id
    )
    if existing_transaction:
        logger.info(
            f"Transaction already exists for Invoice {invoice_id}",
            extra={
                "transaction_id": existing_transaction.TransactionId,
                "invoice_id": invoice_id,
                "company_id": company_id
            }
        )
        return existing_transaction
    
    # Check by payment intent
    if payment_intent:
        existing_transaction = await get_transaction_by_criteria(
            session=session,
            company_id=company_id,
            provider_id=payment_intent # type: ignore
        )
        if existing_transaction:
            logger.info(
                f"Transaction already exists for payment intent {payment_intent}",
                extra={
                    "transaction_id": existing_transaction.TransactionId,
                    "payment_intent": payment_intent,
                    "company_id": company_id
                }
            )
            return existing_transaction
        
    # Get customer details
    donor = None
    donor_id = 10001
    customer_email = None
    sub_id = None
    recurring_transaction = None
    if invoice_data.billing_reason == "subscription_cycle":
        # get subscription data from the parent
        subscription_details = invoice_data.parent.subscription_details if invoice_data.parent and invoice_data.parent.subscription_details else None
        if subscription_details:
            sub_id = subscription_details.subscription.id if subscription_details.subscription else None    #type: ignore


    if sub_id:
        # get recurring donation by subscription ID
        logger.info(f"Looking up recurring transaction for subscription ID {sub_id} and company ID {company_id}")
        recurring_response = await get_recurring_transaction(session, company_id=company_id, 
                                                        sub_id=sub_id, transaction_id=0, include_details=True, include_payments=False)
    
        recurring_transaction = recurring_response.item if recurring_response and recurring_response.item else None

        if recurring_transaction and recurring_transaction.donorId:
            donor_id = recurring_transaction.donorId
            donor = await get_donor_by_id(session, donor_id) if donor_id else None
            customer_email = donor.EMail if donor else None
        
    else:
        customer_details = invoice_data.customer if isinstance(invoice_data.customer, dict) else None
        if customer_details:
            customer_email = customer_details.get("email")

            donor = await _get_donor_by_email(session, customer_email, customer_details) if customer_email else None
            donor_id = donor.DonorId if donor else 10001
        
    # Build transaction model
    transaction = TransactionModel(
        transactionId=0,
        description=None,
        companyId=company_id,
        terminalId="",
        donorId=donor_id,
        donorName=donor.CompleteName if donor else "",
        donorPhone="",
        donorEmail=customer_email or "",
        donorBillingZip=donor.PostalCode if donor else "",
        transactionDate=datetime.fromtimestamp(invoice_data.created).isoformat() if invoice_data.created else datetime.utcnow().isoformat(),
        purposeId=1,
        totalAmount=invoice_data.amount_paid / 100 if invoice_data.amount_paid else 0,  # Convert from cents
        currency=invoice_data.currency.upper() if invoice_data.currency else "USD",
        recurring=False,
        numberofMonths=0,
        paymentMethod="stripe",
        paymentMethodId=4,
        provider="Stripe",
        providerName=event_id or invoice_id,
        providerId=payment_intent, # type: ignore
        providerToken=invoice_id,
        providerPlanId=invoice_id,  
        providerAgreementId=sub_id,      
        successUrl=None,
        cancelUrl=None,
        checkoutUrl=None,
        status="completed",
        statusCode=2,
        donorDetails=donor if donor else None,  # type: ignore
        details=[],
    )
    
    # Add line items as transaction details
    details = []
    if recurring_transaction and recurring_transaction.details:
        # If this invoice is linked to an existing subscription/recurring donation, use the same details
        # add details from the recurring transaction with updated amounts and descriptions based on the invoice line items
        for detail in recurring_transaction.details:
            transaction_detail = TransactionDetailsModel(
                lineNumber=detail.lineNumber,
                description=detail.description,
                donationTypeId=detail.donationType,
                amount=float(detail.amount),  # type: ignore
                feePercent=0,
                feeAmount=0,
                priceId=None,
                productId=None
            )
            details.append(transaction_detail)            
    else:
        line_items = invoice_data.lines.data if invoice_data.lines and invoice_data.lines.data else []
        
        for line_no, line_item in enumerate(line_items, start=1):
            price = line_item.get("price", {})
            price_id = price.get("id") if price else None
            product_id = price.get("product") if price else None
            if not price:
                pricing = line_item.get("pricing", {})
                pricing_details = pricing.get("pricing_details", {}) if pricing else {}
                price_id = pricing_details.get("price", None) if pricing_details else None
                product_id = pricing_details.get("product", None) if pricing_details else None
                
            transaction_detail = TransactionDetailsModel(
                lineNumber=line_no,
                description=line_item.get("description"),
                donationTypeId=0,
                amount=line_item.get("amount", 0) / 100 if line_item.get("amount") else 0,  # Convert from cents
                feePercent=0,
                feeAmount=0,
                priceId=price_id,
                productId=product_id
            )
            details.append(transaction_detail)
    
    transaction.Details = details
    #logger.info(transaction.Details)

    # Save transaction to database
    transaction = await create_transaction_in_database(
        session=session,
        transaction=transaction
    )
    
    logger.info(
        f"Invoice paid processing stub executed for invoice {invoice_id}",
        extra={
            "event_id": event_id,
            "invoice_id": invoice_id,
            "company_id": company_id
        }
    )
    
    #return transaction    
    return None

async def process_stripe_payout_paid(
    session: AsyncSession,
    payout_id: str,
    company_id: int,
    stripe_provider: StripePaymentProvider,
    event_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Process a Stripe payout.paid event.
    
    This utility function handles payout completion processing, including:
    - Validating payout data
    - Updating payout status in database
    - Sending notifications to finance team
    - Updating account balance records
    
    This function can be called from:
    - Webhook handlers (payout.paid)
    - Direct API calls for testing
    - Finance reporting tools
    
    Args:
        session: Database session
        payout_id: Stripe payout ID
        company_id: Company ID for the transaction
        event_id: Optional webhook event ID for logging
        stripe_provider: Stripe payment provider instance
        
    Returns:
        Dict containing processing results and status
        
    Example:
        result = await process_stripe_payout_paid(
            session=session,
            payout_data=webhook_data.data.get("object", {}),
            company_id=company_id,
            event_id=webhook_data.id
        )
    """
    
    starting_after = None
    more_transactions = True
    batch_number = None
    bank_deposit = None
    fee_total = 0
    while more_transactions:
        balance_transaction_object = await stripe_provider.get_balance_transactions(
            payout_id=payout_id,
            starting_after=starting_after
        )            
        for transaction in balance_transaction_object.data:
            starting_after = transaction.id            
            logger.info(
                f"Processing balance transaction {transaction.id} for payout {payout_id}",
                extra={
                    "event_id": event_id,
                    "payout_id": payout_id,
                    "transaction_id": transaction.id,
                    "company_id": company_id
                }
            )
            if transaction.type == "payout":                
                # Create the bank deposit batch and transaction records in the database
                logger.info(
                    f"Payout transaction details: amount={transaction.amount}, currency={transaction.currency}, status={transaction.status}",
                    extra={
                        "event_id": event_id,
                        "payout_id": payout_id,
                        "transaction_id": transaction.id,
                        "company_id": company_id
                    }
                )
                bank_deposit = BankDepositBatchCreateModel(
                    companyId=company_id,
                    batchDate=datetime.fromtimestamp(transaction.created).isoformat() if transaction.created else datetime.utcnow().isoformat(), # type: ignore
                    bankDepositDate=datetime.fromtimestamp(transaction.available_on).isoformat() if transaction.available_on else None, # type: ignore
                    batchStatus=3,  # pending review
                    batchMethodType="Credit Card",
                    batchMethodTypeId=4,
                    providerId=payout_id,
                    amount=(Decimal(transaction.amount) / 100) * -1,  # Convert from cents
                    transactions=[]
                )
            elif transaction.type == "charge":
                # process charge transaction
                charge_id = transaction.source if hasattr(transaction, 'source') else None
                fee_amount = transaction.fee if hasattr(transaction, 'fee') else 0
                fee_total += fee_amount / 100 if fee_amount > 0 else 0  # Convert from cents
                deposit_charge = BankDepositBatchTransactionCreateModel(
                    donationReceiptId=0,
                    providerId=charge_id, # type: ignore
                    amount=Decimal(transaction.amount) / 100 ,  # Convert from cents
                    feeAmount=(Decimal(fee_amount)/100)*-1 if fee_amount > 0 else None,
                    transactionType="charge-charge"
                )
                if charge_id:
                    logger.info(
                        f"Processing charge transaction {charge_id} linked to payout {payout_id}",
                        extra={
                            "event_id": event_id,
                            "payout_id": payout_id,
                            "transaction_id": transaction.id,
                            "charge_id": charge_id,
                            "company_id": company_id
                        }
                    )
                    dbTransaction = await process_stripe_charge(session, stripe_provider=stripe_provider, charge_id=str(charge_id), company_id=company_id)
                    if dbTransaction and bank_deposit:
                        logger.info(
                            f"Adding charge transaction {dbTransaction.TransactionId} to bank deposit batch for payout {payout_id}")
                        deposit_charge.donationReceiptId = dbTransaction.TransactionId
                        deposit_charge.providerId = dbTransaction.ProviderId # type: ignore
                
                bank_deposit.transactions.append(deposit_charge) # type: ignore
            elif transaction.type == "payment":
                fee_amount = transaction.fee if hasattr(transaction, 'fee') else 0
                fee_total += fee_amount / 100 if fee_amount > 0 else 0  # Convert from cents
                payment_charge = BankDepositBatchTransactionCreateModel(
                    donationReceiptId=0,
                    providerId=transaction.id, # type: ignore
                    amount=Decimal(transaction.amount) / 100 ,  # Convert from cents
                    feeAmount=(Decimal(fee_amount)/100)*-1 if fee_amount > 0 else None,
                    transactionType="payment"
                )
                if transaction.reporting_category == "charge":
                    # process charge
                    charge_id = transaction.source if hasattr(transaction, 'source') else None
                    if charge_id:
                        dbTransaction = await process_stripe_charge(session, stripe_provider=stripe_provider, charge_id=str(charge_id), company_id=company_id)
                        if dbTransaction:
                            if bank_deposit:
                                payment_charge.donationReceiptId = dbTransaction.TransactionId
                                payment_charge.providerId = dbTransaction.ProviderId # type: ignore
                                payment_charge.transactionType = "payment-charge"
                bank_deposit.transactions.append(payment_charge) # type: ignore

            elif transaction.type == "refund":
                fee_amount = transaction.fee if hasattr(transaction, 'fee') else 0
                fee_total += fee_amount / 100 if fee_amount > 0 else 0  # Convert from cents
                refund_charge = BankDepositBatchTransactionCreateModel(
                    donationReceiptId=0,
                    providerId=transaction.id, # type: ignore
                    amount=(Decimal(transaction.amount) / 100) * -1,  # Convert from cents and negate for refund
                    feeAmount=(Decimal(fee_amount)/100)*-1 if fee_amount > 0 else None,
                    transactionType="refund"
                )
                bank_deposit.transactions.append(refund_charge) # type: ignore
            else:
                # default case for other transaction types
                fee_amount = transaction.fee if hasattr(transaction, 'fee') else 0
                fee_total += fee_amount / 100 if fee_amount > 0 else 0  # Convert from cents
                other_transaction = BankDepositBatchTransactionCreateModel( 
                    donationReceiptId=0,
                    providerId=transaction.id, # type: ignore
                    amount=Decimal(transaction.amount) / 100 ,  # Convert from cents
                    feeAmount=(Decimal(fee_amount)/100)*-1 if fee_amount > 0 else None,
                    transactionType=transaction.type
                )
                bank_deposit.transactions.append(other_transaction) # type: ignore
    
        more_transactions = balance_transaction_object.has_more if hasattr(balance_transaction_object, 'has_more') else False

    if bank_deposit:
        # Save bank deposit batch and transactions to database
        logger.info(
            f"Bank deposit batch prepared with {len(bank_deposit.transactions)} transactions for payout {payout_id}",
            extra={
                "event_id": event_id,
                "payout_id": payout_id,
                "transaction_count": len(bank_deposit.transactions),
                "company_id": company_id
            }
        )
        # record a fee transaction for the total fees associated with the payout
        if fee_total > 0:
            bank_deposit.transactions.append(
                BankDepositBatchTransactionCreateModel(
                    donationReceiptId=0,
                    providerId=bank_deposit.providerId,
                    amount=Decimal(fee_total) * -1,  # Record fees as negative amount
                    feeAmount=None,
                    transactionType="payout-fee"
                )
            )
        # Here you would call a function to save the bank deposit batch to the database
        batch_number = await create_bank_deposit_batch(session, bank_deposit)
    
    logger.info(
        f"Payout paid processing stub executed for payout {payout_id}",
        extra={
            "event_id": event_id,
            "payout_id": payout_id,
            "company_id": company_id
        }
    )
    
    return {
        "status": "success",
        "payout_id": payout_id,
        "batch_number": batch_number,
        "message": "Payout paid processing completed (stub)"
    }

async def process_stripe_charge(
    session: AsyncSession,
    stripe_provider: StripePaymentProvider,
    charge_id: str,
    company_id: int
) -> TransactionModel | None:
    """
    Process a Stripe charge transaction.
    
    This function can be called from the payout processing workflow to handle
    charge transactions linked to a payout.
    
    Args:
        session: Database session
        stripe_provider: Stripe payment provider instance
        charge_id: Stripe charge ID to process
        company_id: Company ID for logging context  
    """
    try:
        charge = await stripe_provider.get_charge(charge_id=charge_id, expand=["customer"])
        logger.info(
            f"Processing charge {charge_id}",
            extra={
                "charge_id": charge_id,
                "company_id": company_id
            }
        )
        payment_intent = charge.payment_intent if hasattr(charge, 'payment_intent') else None
        payment_intent_id = None
        if payment_intent:
            # verify if charge is linked to a transaction in our database
            payment_intent_id = payment_intent if isinstance(payment_intent, str) else None
            existing_transaction = await get_transaction_by_criteria(
                session=session,
                company_id=company_id,
                provider_id=payment_intent_id
            )
            if existing_transaction:
                return existing_transaction
        
        charge_customer = charge.customer if hasattr(charge, 'customer') else None
        donor = None
        donor_id = 10001
        customer_email = None
        if charge_customer:
            customer = charge_customer if isinstance(charge_customer, dict) else None
            if customer:
                customer_email = customer.get("email")
                logger.info(
                    f"Looking up donor for charge {charge_id} using email {customer_email}",
                    extra={
                        "charge_id": charge_id,
                        "customer_email": customer_email,
                        "company_id": company_id
                    }
                )
                donor = await _get_donor_by_email(session, email=customer_email, customer=customer) # type: ignore
                donor_id = donor.DonorId if donor else 10001

        logger.info(f"Building transaction model for charge {charge_id} with donor {donor_id}",)
        transaction = TransactionModel(
            transactionId=0,
            companyId=company_id,
            terminalId="",
            donorId=donor_id,
            donorName=donor.CompleteName if donor else None,
            donorPhone=donor.PhoneNumber if donor else None,
            donorEmail=customer_email or None,
            donorBillingZip=donor.PostalCode if donor else None,
            transactionDate=datetime.fromtimestamp(charge.created).isoformat() if charge.created else datetime.utcnow().isoformat(),
            purposeId=1,
            totalAmount=charge.amount / 100 if charge.amount else 0,  # Convert from cents
            currency=charge.currency.upper() if charge.currency else "USD",
            recurring=False,
            numberofMonths=0,
            paymentMethod="stripe",
            paymentMethodId=4,
            provider="Stripe",
            providerName=charge_id,
            providerId=payment_intent_id, 
            providerToken=charge_id,
            providerPlanId=charge_id,        
            successUrl=None,
            cancelUrl=None,
            checkoutUrl=None,
            status="completed",
            statusCode=2,
            donorDetails=donor if donor else None, 
            details=[],
        )         # type: ignore
        logger.info(transaction)
        # Add line items as transaction details
        line_items = await stripe_provider.get_payment_intent_lineitems(payment_intent_id=payment_intent_id) if payment_intent_id else None
        details = []
        if line_items and line_items.data:
            for line_no, line_item in enumerate(line_items.data, start=1):                
                transaction_detail = TransactionDetailsModel(
                    lineNumber=line_no,
                    description=line_item.get("product_name") or line_item.get("description"),
                    donationTypeId=0,
                    amount=line_item.get("unit_cost", 0) / 100 if line_item.get("unit_cost") else 0,  # Convert from cents
                    feePercent=0,
                    feeAmount=0,
                    priceId=line_item.get("product_code") if line_item else None, # type: ignore
                )
                details.append(transaction_detail)
        else:
            # If no line items, add a single detail for the charge
            transaction_detail = TransactionDetailsModel(
                lineNumber=1,
                description=charge.description if hasattr(charge, 'description') else "Charge",
                donationTypeId=3,
                amount=charge.amount / 100 if charge.amount else 0,  # Convert from cents
                feePercent=0,
                feeAmount=0,
                priceId=None,
            ) # type: ignore
            details.append(transaction_detail)

        logger.info(details)
        transaction.Details = details
        
        # Save transaction to database
        transaction = await create_transaction_in_database(
            session=session,
            transaction=transaction
        )        
        
        logger.info(
            f"Charge transaction processed and saved with ID: {transaction.TransactionId}")
        
        return transaction    

    except Exception as e:
        logger.error(
            f"Error processing charge {charge_id}: {str(e)}",
            extra={
                "charge_id": charge_id,
                "company_id": company_id,
                "error": str(e),
                "error_type": type(e).__name__
            },
            exc_info=True
        )

async def _get_donor_by_email(session: AsyncSession, email: str, customer: stripe.Customer) -> DonorsModel:
    """
    Helper function to retrieve a donor by email.
    
    Args:
        session: Database session
        email: Donor email address
        customer: Stripe customer object
    Returns:
        DonorsModel if found, None otherwise
    """
    
    donor = await find_donor_by_email(session, email) 
    
    if not donor:
        # Create donor model (not saving to DB yet, will be saved with transaction)
        address = customer.address if hasattr(customer, 'address') else None
        donor = DonorsModel(
            donorId=0,
            namePrefix="",
            completeName=customer.name if customer else "",
            firstName=None,
            middleName=None,
            lastName=None,
            suffix=None,
            companyName=None,
            taxReceiptName=None,
            addressLine1=address.line1 if address else None,
            addressLine2=address.line2 if address else None,
            city=address.city if address else None,
            state=address.state if address else None,
            postalCode=address.postal_code if address else None,
            countryCode=address.country if address else None,
            phoneNumber=customer.phone if hasattr(customer, 'phone') else None,
            eMail=email or "",
            occupation="",
            physician=False,
            incorrectAddress=False,
            publishinDonorList=False,
            taxReceiptRequired=False,
            statusCode=1,
            createdBy=0,
            createdDate=datetime.utcnow(),
            modifiedBy=0,
            modifiedDate=datetime.utcnow(),
        )

    return donor # type: ignore