"""
Transaction endpoints for managing transaction data.

Provides POST endpoint for creating new transactions.

Endpoints:
    POST /api/v1/transaction - Create a new transaction
"""

import json
import uuid
from datetime import datetime
from decimal import Decimal
from typing import Optional

from anyio import sleep
from fastapi import APIRouter, Depends, HTTPException, status as http_status
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import settings
from src.core.logging import get_logger
from src.core.provider_manager import get_stripe_provider, get_email_provider
from src.database import get_session
from src.models.transaction import (
    TestPaymentMethodRequest,
    TestPaymentMethodResponse,
    TransactionModel,
    TransactionResponse
)
from src.database.models.donors import Donors
#from src.providers.stripe_payment_provider import StripePaymentProvider
#from src.providers.stripe_http_provider import StripeHTTPProvider
from src.core.cache_manager import get_company_from_cache
from src.core.payment_utils import get_payment_description, get_transaction_description
from src.core.donors_utils import find_donor_by_email
from src.models.donors import DonorsModel
from src.models.company import CompanyModel
#from src.providers.sendgrid_email_provider import SendGridEmailProvider
from src.core.email_utils import create_receipt_html
from src.core.transaction_utils import (
    get_transaction_by_criteria,
    create_transaction_in_database,
    update_transaction_status
)
#from src.models.stripe.subscription import SubscriptionModel
from src.core.dependencies import User, get_current_user_optional
from src.core.donors_utils import get_donor_by_user_id

router = APIRouter(prefix="/transaction", tags=["transaction"])
logger = get_logger(__name__, level=settings.LOG_LEVEL)

@router.post(
    "",
    response_model=TransactionResponse,
    status_code=http_status.HTTP_200_OK,
    summary="Create a new transaction",
    description="""
    Create a new transaction with details.
    
    This endpoint accepts transaction information including:
    - Company and donor information
    - Transaction date and amount
    - Payment method and provider details
    - Transaction line items/details
    
    The transaction will be validated, processed, and stored in the database.
    """,
    responses={
        200: {
            "description": "Transaction created successfully",
            "model": TransactionResponse,
        },
        400: {
            "description": "Invalid transaction data",
        },
        500: {
            "description": "Internal server error",
        },
    },      
)
async def create_transaction(
    transaction: TransactionModel,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user_optional)
) -> TransactionResponse:
    """
    Create a new transaction record in the database.
    
    This endpoint validates the provided transaction data, processes the payment
    using the specified payment provider, and stores the transaction record along
    with its details in the database.
    
    Args:
        transaction: Transaction data model with company, donor, amount, payment, and details
        session: Database session (injected)
        current_user: Optional[User] = The currently authenticated user (optional)
    Returns:
        TransactionResponse with created transaction details
        
    Raises:
        ValidationError: If transaction data is invalid
        NotFoundError: If company or payment provider not found
        
    Example:
        POST /api/v1/transaction
        Request Body:
        {
            "transactionId": 0,
            "companyId": 1,
            "donorId": 123,
            "donorName": "John Doe",
            "transactionDate": "2025-12-18T10:30:00Z",
            "purposeId": 1,
            "amount": 100.00,
            "paymentMethod": 1,
            "providerId": 1,
            "providerToken": "tok_1234567890",
            "status": "pending",
            "details": [
                {
                    "lineNumber": 1,
                    "description": "General Donation",
                    "donationTypeId": 5,
                    "amount": 100.00,
                    "feePercent": 2.9,
                    "feeAmount": 2.90
                }
            ]
        }
        Response 201:
        {
            "item": {
                "transactionId": 1001,
                "companyId": 1,
                "donorId": 123,
                "donorName": "John Doe",
                "transactionDate": "2025-12-18T10:30:00Z",
                "purposeId": 1,
                "amount": 100.00,
                "paymentMethod": "credit_card",
                "providerId": 1,
                "providerToken": "tok_1234567890",
                "status": "completed",
                "details": [...]
            },
            "status": "success"
        }   
    """
    logger.info(
        "Creating new transaction",
        extra={
            "company_id": transaction.CompanyId,
            "donor_id": transaction.DonorId,
            "amount": transaction.TotalAmount,
            "payment_method": transaction.PaymentMethod,
        },
    )
    
    try:
        current_logged_donor = None
        if current_user:
            current_logged_donor = await get_donor_by_user_id(session, current_user.id, active_only=True)
            
        # 1. Validate transaction data
        if not transaction.CompanyId:
            raise HTTPException(
                status_code=http_status.HTTP_400_BAD_REQUEST,
                detail="CompanyId is required"
            )
        
        company = await get_company_from_cache(transaction.CompanyId, session)
        if not company:
            raise HTTPException(
                status_code=http_status.HTTP_404_NOT_FOUND,
                detail=f"Company with ID {transaction.CompanyId} not found"
            )   
        if transaction.TotalAmount <= 0:
            raise HTTPException(
                status_code=http_status.HTTP_400_BAD_REQUEST,
                detail="TotalAmount must be greater than 0"
            )
        
        # 2. Create transaction in database using utility function
        created_transaction = await create_transaction_in_database(
            transaction=transaction,
            session=session,
            logged_in_user_id=current_logged_donor.DonorId if current_logged_donor else -1
        )

        # Send receipt email if requested and email is present
        if settings.SEND_EMAILS and transaction.DonorEmail:
            logger.info(
                f"Sending receipt email for transaction {created_transaction.TransactionId}",
                extra={"transaction_id": created_transaction.TransactionId, "email": transaction.DonorEmail}
            )            
            await send_transaction_receipt(created_transaction.TransactionId, session=session)

        logger.info(
            "Transaction created successfully",
            extra={
                "transaction_id": created_transaction.TransactionId,
                "company_id": created_transaction.CompanyId,
                "status": "completed"
            },
        )

        return TransactionResponse(
            item=created_transaction,
            status="completed",
            message="Transaction created successfully"
        )
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
        
    except Exception as e:
        logger.error(
            f"Error creating transaction: {str(e)}",
            extra={
                "error": str(e),
                "error_type": type(e).__name__,
                "company_id": transaction.CompanyId,
            },
            exc_info=True,
        )
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create transaction: {str(e)}"
        )    


@router.post(
    "/kiosk",
    response_model=TransactionResponse,
    status_code=http_status.HTTP_200_OK,
    summary="Create a new transaction payment flow for kiosk",
    description="""
    Create a new transaction with details.
    
    This endpoint accepts transaction information including:
    - Company and donor information
    - Transaction date and amount
    - Payment method and provider details
    - Transaction line items/details
    
    The transaction will be validated, processed, and stored in the database.
    """,
    responses={
        200: {
            "description": "Kiosk Payment Flow started successfully",
            "model": TransactionResponse,
        },
        400: {
            "description": "Invalid transaction data",
        },
        500: {
            "description": "Internal server error",
        },
    },
)
async def start_kiosk_payment_flow(
    transaction: TransactionModel,
    session: AsyncSession = Depends(get_session),
) -> TransactionResponse:
    """
    Start a kiosk payment flow by creating a payment intent and initiating terminal payment.
    
    This endpoint initiates the payment process on a Stripe Terminal reader. It creates
    a payment intent with the provided transaction details and instructs the terminal
    to collect payment. The actual transaction record is created later when payment completes.
    
    Args:
        transaction: Transaction data model with company, terminal, amount, and line items
        session: Database session (injected)
        
    Returns:
        TransactionResponse with payment intent details and pending status
        
    Raises:
        ValidationError: If transaction data is invalid
        NotFoundError: If company or terminal not found
        
    Example:
        POST /api/v1/transaction
        Request Body:
        {
            "transactionId": 0,
            "companyId": 1,
            "donorId": 123,
            "donorName": "John Doe",
            "transactionDate": "2025-12-18T10:30:00Z",
            "purposeId": 1,
            "amount": 100.00,
            "paymentMethod": "credit_card",
            "providerId": 1,
            "providerToken": "tok_1234567890",
            "status": "pending",
            "details": [
                {
                    "lineNumber": 1,
                    "description": "General Donation",
                    "donationTypeId": 5,
                    "amount": 100.00,
                    "feePercent": 2.9,
                    "feeAmount": 2.90
                }
            ]
        }
        
        Response 201:
        {
            "item": {
                "transactionId": 1001,
                "companyId": 1,
                "donorId": 123,
                "donorName": "John Doe",
                "transactionDate": "2025-12-18T10:30:00Z",
                "purposeId": 1,
                "amount": 100.00,
                "paymentMethod": "credit_card",
                "providerId": 1,
                "providerToken": "tok_1234567890",
                "status": "completed",
                "details": [...]
            },
            "status": "success"
        }
    """
    logger.info(
        "Kiosk payment flow started",
        extra={
            "company_id": transaction.CompanyId,
            "donor_id": transaction.DonorId,
            "amount": transaction.TotalAmount,
            "payment_method": transaction.PaymentMethod,
        },
    )
    
    try:
        # 1. Validate transaction data
        if not transaction.CompanyId:
            raise HTTPException(
                status_code=http_status.HTTP_400_BAD_REQUEST,
                detail="CompanyId is required"
            )
        
        company = await get_company_from_cache(transaction.CompanyId, session)
        if not company:
            raise HTTPException(
                status_code=http_status.HTTP_404_NOT_FOUND,
                detail=f"Company with ID {transaction.CompanyId} not found"
            )
        
        if transaction.TotalAmount <= 0:
            raise HTTPException(
                status_code=http_status.HTTP_400_BAD_REQUEST,
                detail="TotalAmount must be greater than 0"
            )
        
        if not transaction.PaymentMethod:
            raise HTTPException(
                status_code=http_status.HTTP_400_BAD_REQUEST,
                detail="PaymentMethod is required"
            )
        
        if not transaction.TerminalId:
            raise HTTPException(
                status_code=http_status.HTTP_400_BAD_REQUEST,
                detail="TerminalId is required for kiosk transactions"
            )
        
        # 2. Get Stripe payment provider (cached/singleton)
        logger.info("Getting Stripe provider")
        try:
            stripe_provider = await get_stripe_provider(
                session=session,
                company_id=transaction.CompanyId
            )
        except ValueError as e:
            raise HTTPException(
                status_code=http_status.HTTP_404_NOT_FOUND,
                detail=str(e)
            )
        
        logger.info(
            "Stripe provider obtained",
            extra={"merchant_id": stripe_provider.merchant_id}
        )
        
        # 4. Create Stripe payment intent and initiate terminal payment collection
        # Convert amount to cents for Stripe
        amount_cents = int(transaction.TotalAmount * 100)
        
        logger.info(
            "Creating Stripe payment intent for terminal",
            extra={
                "amount_cents": amount_cents,
                "currency": "usd"
            }
        )
        
        # Create payment intent for terminal with manual capture
        donor = DonorsModel(
            donorId=transaction.DonorId or 0,
            namePrefix=None,
            firstName=None,
            middleName=None,
            lastName=None,
            suffix=None,
            completeName=transaction.DonorName,
            companyName=None,
            taxReceiptName=None,
            addressLine1=None,
            addressLine2=None,
            city=None,
            state=None,
            postalCode=transaction.DonorBillingZip,
            countryCode=None,
            phoneNumber=transaction.DonorPhone,
            eMail=transaction.DonorEmail,
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
        transaction.Description = get_transaction_description(transaction=transaction)
        transaction.ProviderDescription = get_payment_description(
                company_short_name=company.ShortName or "Masjid",
                purpose=transaction.PurposeId or 1
            )
        payment_intent = await stripe_provider.create_payment_intent_terminal(
            amount=amount_cents,
            currency="usd",                        
            description=transaction.Description,
            statement_description=transaction.ProviderDescription,
            donor=donor
        )
        
        if not payment_intent:
            raise HTTPException(
                status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create payment intent with Stripe"
            )
        
        provider_token = payment_intent.get("id")
        payment_status = payment_intent.get("status", "pending")
        #print("Payment Intent:", payment_intent)

        reader = await stripe_provider.process_terminal_payment(
            payment_intent_id=provider_token or "", 
            reader_id=transaction.TerminalId or ""
        )            
        #print("Reader:", reader)
        transaction.ProviderId = provider_token
        transaction.Status = payment_status

        logger.info(
            "Kiosk Payment Flow started successfully",
            extra={
                "transaction_id": transaction.TransactionId,
                "company_id": transaction.CompanyId,
                "provider_token": provider_token,
                "status": payment_status
            },
        )

        return TransactionResponse(
            item=transaction,
            status=payment_status,
            message="Kiosk payment flow started successfully"
        )
        
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
        
    except Exception as e:
        logger.error(
            f"Error creating transaction: {str(e)}",
            extra={
                "error": str(e),
                "error_type": type(e).__name__,
                "company_id": transaction.CompanyId,
            },
            exc_info=True,
        )
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create transaction: {str(e)}"
        )

@router.post(
    "/online/checkout",
    response_model=TransactionResponse,
    status_code=http_status.HTTP_200_OK,
    summary="Create a new transaction payment flow for online checkout using stripe",
    description="""
        Create a new transaction with details.

        This endpoint accepts transaction information including:
        - Company and donor information
        - Transaction date and amount
    """,
    responses={
        200: {
            "description": "Online Checkout Payment Flow started successfully",
            "model": TransactionResponse,
        },
        400: {
            "description": "Invalid transaction data",
        },
        500: {
            "description": "Internal server error",
        },
    },
)
async def start_online_checkout_payment_flow(
    transaction: TransactionModel,
    current_user: User = Depends(get_current_user_optional),
    session: AsyncSession = Depends(get_session),
) -> TransactionResponse:
    """
    Start an online checkout payment flow by creating a payment intent.

    This endpoint initiates the payment process for online checkout using Stripe.
    It creates a payment intent with the provided transaction details.
    
    Args:
        transaction: Transaction data model with company, amount, and line items
        session: Database session (injected)
        current_user: The currently authenticated user (optional)
    """
    logger.info(
        "Online Checkout payment flow started",
        extra={
            "company_id": transaction.CompanyId,
            "donor_id": transaction.DonorId,
            "amount": transaction.TotalAmount,
        },
    )

    try:    
        current_logged_donor = None
        if current_user:
            current_logged_donor = await get_donor_by_user_id(session, current_user.id, active_only=True)

        # 1. Validate transaction data
        if not transaction.CompanyId:
            raise HTTPException(
                status_code=http_status.HTTP_400_BAD_REQUEST,
                detail="CompanyId is required"
            )
        company = await get_company_from_cache(transaction.CompanyId, session)
        if not company:
            raise HTTPException(
                status_code=http_status.HTTP_404_NOT_FOUND,
                detail=f"Company with ID {transaction.CompanyId} not found"
            )
        if transaction.TotalAmount <= 0:
            raise HTTPException(
                status_code=http_status.HTTP_400_BAD_REQUEST,
                detail="TotalAmount must be greater than 0"
            )
        # 2. Get Stripe payment provider (cached/singleton)
        logger.info("Getting Stripe provider")
        try:
            stripe_provider = await get_stripe_provider(
                session=session,
                company_id=transaction.CompanyId
            )
        except ValueError as e:
            raise HTTPException(
                status_code=http_status.HTTP_404_NOT_FOUND,
                detail=str(e)
            )
        
        logger.info("Stripe provider obtained")
        
        # 3. Create Stripe payment intent and initiate terminal payment collection
        # amount already in cents
        amount_cents = transaction.TotalAmount
        
        logger.info(
            "Creating Stripe checkout for online payment",
            extra={
                "amount_cents": amount_cents,
                "currency": "usd"
            }
        )
        
        donor = DonorsModel(
            donorId=transaction.DonorId or 0,
            namePrefix=None,
            firstName=None,
            middleName=None,
            lastName=None,
            suffix=None,
            completeName=transaction.DonorName,
            companyName=None,
            taxReceiptName=None,
            addressLine1=None,
            addressLine2=None,
            city=None,
            state=None,
            postalCode=transaction.DonorBillingZip,
            countryCode=None,
            phoneNumber=transaction.DonorPhone,
            eMail=transaction.DonorEmail,
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
        # get donor from email 
        if transaction.DonorEmail:
            donor_record = await find_donor_by_email(session, transaction.DonorEmail)
            if donor_record:
                donor = DonorsModel.model_validate(donor_record)

                #update transaction donor id
                transaction.DonorId = donor.DonorId
                transaction.DonorName = donor.CompleteName                
                transaction.DonorDetails = donor
        
            
        reference_id = uuid.uuid4().hex
        company_model = CompanyModel(
            companyId=company.CompanyId,
            companyName=company.CompanyName,
            shortName=company.ShortName,
            eMail=company.EMail,
            phoneNumber=company.PhoneNumber,
            addressLine1=company.AddressLine1,
            addressLine2=company.AddressLine2,
            city=company.City,
            stateCode=company.StateCode,
            postalCode=company.PostalCode,
            countryCode=company.CountryCode,
            taxId=company.TaxId,
            website=company.Website,
            companyLogo=company.CompanyLogo
        ) #type: ignore
         # Create checkout session
        checkout_session = await stripe_provider.create_checkout_session(
            reference_id=str(reference_id),
            transaction=transaction,
            donor=donor,
            company=company_model
        )
        transaction.Provider = "Stripe"
        transaction.PaymentMethodId = 4  # credit_card will update later with actual method
        transaction.ProviderName = reference_id
        transaction.ProviderToken = checkout_session.get("id")
        transaction.CheckoutURL = checkout_session.get("url")
        transaction.Status = "pending"
        transaction.StatusCode = 3  # pending

        created_transaction = await create_transaction_in_database(
            transaction=transaction,
            session=session,
            logged_in_user_id=current_logged_donor.DonorId if current_logged_donor else -1
        )

        return TransactionResponse(
            item=created_transaction,
            status="pending",
            message="Online checkout payment flow started successfully" 
        )
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
        
    except Exception as e:
        logger.error(
            f"Error creating transaction: {str(e)}",
            extra={
                "error": str(e),
                "error_type": type(e).__name__,
                "company_id": transaction.CompanyId,
            },
            exc_info=True,
        )
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create transaction: {str(e)}"
        )

@router.post(
    "/kiosk/payment-flow-status",
    response_model=TransactionResponse,
    status_code=http_status.HTTP_200_OK,
    summary="Get kiosk payment flow status",
    description="""
    Retrieve the status of an ongoing kiosk payment flow.
    If the payment has been completed successfully then transaction record is created and returned.
    """,
    responses={
        200: {
            "description": "Kiosk Payment Flow status retrieved successfully",
            "model": TransactionResponse,
        },
        400: {
            "description": "Invalid request data",
        },
        500: {
            "description": "Internal server error",
        },
    },
)
async def process_kiosk_payment_flow_status(
    transaction: TransactionModel,    
    session: AsyncSession = Depends(get_session),
) -> TransactionResponse:
    """
    Check the status of a kiosk payment flow and complete the transaction if payment succeeded.
    
    This endpoint polls the Stripe Terminal reader status. If payment collection has succeeded,
    it captures the payment intent and creates the transaction record in the database.
    
    Args:
        transaction: Transaction model with companyId, terminalId, and providerId (payment intent ID)
        session: Database session (injected)
        
    Returns:
        TransactionResponse with transaction details if payment completed, or pending status
        
    Raises:
        ValidationError: If request data is invalid
        NotFoundError: If company, provider configuration, or payment intent not found
        
    Example:
        POST /api/v1/transaction/kiosk/payment-flow-status
        Request Body:
        {
            "companyId": 1,
            "terminalId": "tmr_1234567890"
        }
        
        Response 200:
        {
            "item": {
                "transactionId": 1001,
                "companyId": 1,
                "donorId": 123,
                "donorName": "John Doe",
                "transactionDate": "2025-12-18T10:30:00Z",
                "purposeId": 1,
                "amount": 100.00,
                "paymentMethod": "credit_card",
                "providerId": 1,
                "providerToken": "pi_1234567890",
                "status": "completed",
                "details": [...]
            },
            "status": "success"
        }
    """
    logger.info(f"Processing kiosk payment flow status", extra={
        "company_id": transaction.CompanyId,
        "terminal_id": transaction.TerminalId,
    })

    try:
        # Validate input
        if not transaction.CompanyId:
            raise HTTPException(
                status_code=http_status.HTTP_400_BAD_REQUEST,
                detail="CompanyId is required"
            )
        
        if not transaction.TerminalId:
            raise HTTPException(
                status_code=http_status.HTTP_400_BAD_REQUEST,
                detail="TerminalId is required"
            )   
        
        company = await get_company_from_cache(transaction.CompanyId, session)
        if not company: 
            raise HTTPException(
                status_code=http_status.HTTP_404_NOT_FOUND,
                detail=f"Company with ID {transaction.CompanyId} not found"
            )   
        
        logger.info("Getting Stripe provider configuration")
        # Get Stripe payment provider (cached/singleton)
        try:
            stripe_provider = await get_stripe_provider(
                session=session,
                company_id=transaction.CompanyId                
            )
        except ValueError as e:
            raise HTTPException(
                status_code=http_status.HTTP_404_NOT_FOUND,
                detail=str(e)
            )
        
        logger.info(
            "Stripe provider obtained",
            extra={"merchant_id": stripe_provider.merchant_id}
        )
        
        if not transaction.ProviderId:
            raise HTTPException(
                status_code=http_status.HTTP_400_BAD_REQUEST,
                detail="ProviderId is required"
            )
        
        # Check terminal reader status to see if payment collection completed
        reader = await stripe_provider.get_reader_status(
                reader_id=transaction.TerminalId
            )
        
        #print("Reader Status:", reader)
        payment_status = "in_progress"
        message = "Payment is still pending on terminal reader."
        if not reader.action is None:
            if reader.action.status == "failed":
                logger.error(
                    "Payment collection failed on terminal reader",
                    extra={
                        "reader_id": reader.id,
                        "status": reader.action.status,
                        "failure_code": reader.action.failure_code,
                        "failure_message": reader.action.failure_message
                    }
                )
                payment_status = "failed"
                message = reader.action.failure_message
            elif reader.action.status == "succeeded":        
                logger.info(
                    "Payment method collected successfully on terminal reader",
                    extra={
                        "reader_id": reader.id,
                        "status": reader.action.status
                    }
                )
                # Capture the payment intent to complete the charge
                payment_intent = await stripe_provider.capture_payment_intent(
                    payment_intent_id=transaction.ProviderId
                )
                providerToken = transaction.ProviderId
                if payment_intent:
                    payment_method = await stripe_provider.get_payment_method(
                        payment_method_id=payment_intent.get("payment_method") # type: ignore
                    )
                    if payment_method:
                        providerToken = f"{payment_method.card_present.brand} ****{payment_method.card_present.last4}" # type: ignore
                        
                    
                #print("Captured Payment Intent:", payment_intent)
                transaction.Provider = "Stripe"                
                transaction.PaymentMethodId = 4  # credit_card
                transaction.ProviderToken = providerToken
                transaction.StatusCode = 2  # completed
                created_transaction = await create_transaction_in_database(
                    transaction=transaction,
                    session=session
                )
                transaction = created_transaction

                payment_status = "success"
                message = "Payment completed successfully."
        else:
            payment_status = "ready"
            message = "Reader is ready for payment, no pending actions."

        return TransactionResponse(
            item=transaction,
            status=payment_status,
            message=message
        )
        
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
        
    except Exception as e:
        logger.error(
            f"Error creating transaction: {str(e)}",
            extra={
                "error": str(e),
                "error_type": type(e).__name__,
                "company_id": transaction.CompanyId,
            },
            exc_info=True,
        )
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create transaction: {str(e)}"
        )

@router.post(
        "/kiosk/cancel-payment-flow",
        response_model=TransactionResponse,
        status_code=http_status.HTTP_200_OK,
        summary="Cancel kiosk payment flow",
        description="""
        Cancel an ongoing kiosk payment flow on a Stripe Terminal reader.
        """,
        responses={
            200: {
                "description": "Kiosk Payment Flow cancelled successfully",
                "model": TransactionResponse,
            },
            400: {
                "description": "Invalid request data",
            },
            500: {
                "description": "Internal server error",
            },
        },        
)
async def cancel_kiosk_payment_flow(
    transaction: TransactionModel,
    session: AsyncSession = Depends(get_session),
) -> TransactionResponse:
    """
    Cancel an ongoing kiosk payment flow on a Stripe Terminal reader.
    
    This endpoint instructs the Stripe Terminal reader to cancel the current payment
    collection process. It does not create a transaction record since payment was not completed.
    
    Args:
        transaction: Transaction model with companyId and terminalId
        session: Database session (injected)
        
    Returns:
        TransactionResponse with cancelled status
        
    Raises:
        ValidationError: If request data is invalid
        NotFoundError: If company or provider configuration not found
        
    Example:
        POST /api/v1/transaction/kiosk/cancel-payment-flow
        Request Body:
        {
            "companyId": 1,
            "terminalId": "tmr_1234567890"
        }
        
        Response 200:
        {
            "item": {
                "companyId": 1,
                "terminalId": "tmr_1234567890"
            },
            "status": "cancelled"
        }
    """
    logger.info(f"Cancelling kiosk payment flow", extra={
        "company_id": transaction.CompanyId,
        "terminal_id": transaction.TerminalId,
    })

    try:
        # Validate input
        if not transaction.CompanyId:
            raise HTTPException(
                status_code=http_status.HTTP_400_BAD_REQUEST,
                detail="CompanyId is required"
            )   
        if not transaction.TerminalId:
            raise HTTPException(
                status_code=http_status.HTTP_400_BAD_REQUEST,
                detail="TerminalId is required"
            )
        company = await get_company_from_cache(transaction.CompanyId, session)
        if not company: 
            raise HTTPException(
                status_code=http_status.HTTP_404_NOT_FOUND,
                detail=f"Company with ID {transaction.CompanyId} not found"
            )   
        
        logger.info("Getting Stripe provider configuration")
        # Get Stripe payment provider (cached/singleton)
        try:
            stripe_provider = await get_stripe_provider(
                session=session,
                company_id=transaction.CompanyId
            )
        except ValueError as e:
            raise HTTPException(
                status_code=http_status.HTTP_404_NOT_FOUND,
                detail=str(e)
            )

        logger.info(
            "Stripe provider obtained",  
            extra={"merchant_id": stripe_provider.merchant_id}
        )   
        await stripe_provider.cancel_reader_action(
            reader_id=transaction.TerminalId
        )
        logger.info(
            "Kiosk Payment Flow cancelled successfully",    
            extra={
                "company_id": transaction.CompanyId,
                "terminal_id": transaction.TerminalId,
            }
        )
        return TransactionResponse(
            item=transaction,
            status="cancelled",
            message="Kiosk payment flow cancelled successfully"
        )
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        logger.error(
            f"Error cancelling kiosk payment flow: {str(e)}",
            extra={
                "error": str(e),
                "error_type": type(e).__name__,
                "company_id": transaction.CompanyId,
            },
            exc_info=True,
        )
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to cancel kiosk payment flow: {str(e)}"
        )       

@router.post(
        "/online/verify-payment/{company_Id}/{session_id}",
        response_model=TransactionResponse,
        status_code=http_status.HTTP_200_OK,
        summary="Verify online payment status",
)
async def verify_online_payment(
    company_Id: int,
    session_id: str,
    current_user: User = Depends(get_current_user_optional),
    session: AsyncSession = Depends(get_session),
) -> TransactionResponse:
    """
    Verify the status of an online payment using Stripe Checkout Session.
    """
    try:
        logger.info(f"Verifying online payment for session ID: {session_id}")
        
        current_logged_donor = None
        if current_user:
            current_logged_donor = await get_donor_by_user_id(session, current_user.id, active_only=True)

        # Retrieve transaction by provider token using utility function
        # Note: Using company_id=0 as wildcard since provider_token should be unique
        transaction = await get_transaction_by_criteria(
            session=session,
            company_id=company_Id,
            provider_token=session_id
        )
        
        if not transaction:
            raise HTTPException(
                status_code=http_status.HTTP_404_NOT_FOUND,
                detail=f"Transaction with session ID {session_id} not found"
            )
        
        # Get Stripe payment provider (cached/singleton)
        try:
            stripe_provider = await get_stripe_provider(
                session=session,
                company_id=transaction.CompanyId
            )
            # stripe_http_provider = await get_stripe_http_provider(
            #     session=session,
            #     company_id=transaction.CompanyId
            # )
        except ValueError as e:
            raise HTTPException(
                status_code=http_status.HTTP_404_NOT_FOUND,
                detail=str(e)
            )
        
        # Retrieve checkout session from Stripe
        checkout_session = await stripe_provider.get_checkout_session(
            session_id=session_id
        )        
        #logger.info(checkout_session)
        
        payment_status = checkout_session.get("payment_status", "unpaid")
        if payment_status == "paid":
            subscription_id = None
            plan_id = None
            end_date = None
            payment_method = None
            payment_method_id = None
            customer_id = None
            payment_intent = checkout_session.get("payment_intent")
            #logger.info(f"Payment intent ID: {payment_intent}")
            if transaction.Recurring and transaction.NumberofMonths and transaction.NumberofMonths > 1:
                # get subscription id
                subscription_id = checkout_session.get("subscription")
                #logger.info(f"Subscription ID for recurring payment: {subscription_id}")
                if subscription_id:
                    # update subscription
                    subscription = await stripe_provider.update_subscription_cancel_date(subscription_id=subscription_id,
                                                                                         frequency=transaction.RecurringFrequency if transaction.RecurringFrequency else 1,
                                                                                         number_of_periods=transaction.NumberofMonths)

                    # get updated values from subscription
                    subscription_object = await stripe_provider.get_subscription(subscription_id=subscription_id, 
                                                                                 expand=["default_payment_method", "latest_invoice", "latest_invoice.payments"])
                    logger.info(f"Updated subscription object: {subscription_object}")

                    end_date = subscription_object.cancel_at_datetime
                    plan_id = subscription_object.latest_invoice_id
                    payment_intent = subscription_object.payment_intent_id if subscription_object.payment_intent_id else payment_intent
                    payment_method = subscription_object.payment_method_desc
                    customer_id = subscription_object.customer_id
                    payment_method_id = subscription_object.payment_method_id
            await update_transaction_status(transaction_id=transaction.TransactionId, provider_id=payment_intent or "",
                                            status_code=2, subscription_id=subscription_id, plan_id=plan_id, 
                                            end_date=end_date, payment_method=payment_method, session=session, 
                                            customer_id=customer_id, payment_method_id=payment_method_id,
                                            logged_in_user_id=current_logged_donor.DonorId if current_logged_donor else -1) # type: ignore
            
            # Send receipt email if requested and email is present
            if settings.SEND_EMAILS and transaction.DonorEmail:
                logger.info(
                    f"Sending receipt email for transaction {transaction.TransactionId}",
                    extra={"transaction_id": transaction.TransactionId, "email": transaction.DonorEmail}
                )            
                await send_transaction_receipt(transaction.TransactionId, session=session)

            return TransactionResponse(
                item=transaction,
                status="success",
                message="Online payment completed successfully"
            )
        else:
            return TransactionResponse(
                item=transaction,
                status="pending",
                message="Online payment is still pending"
            )
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
        
    except Exception as e:
        logger.error(
            f"Error verifying online payment: {str(e)}",
            extra={
                "error": str(e),
                "error_type": type(e).__name__,
                "session_id": session_id,
            },
            exc_info=True,
        )
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to verify online payment: {str(e)}"
        )


@router.post(
    "/test/present-payment-method",
    response_model=TestPaymentMethodResponse,
    status_code=http_status.HTTP_200_OK,
    summary="Simulate presenting a payment method (TEST MODE ONLY)",
    description="""
    Test helper endpoint to simulate presenting a payment method to a Stripe Terminal reader.
    
    This endpoint is for testing purposes only and uses Stripe's test helpers.
    It simulates a card being presented to a terminal reader without requiring
    physical hardware.
    
    **Note:** This only works with Stripe test mode API keys.
    """,
    responses={
        200: {
            "description": "Payment method presented successfully",
            "model": TestPaymentMethodResponse,
        },
        400: {
            "description": "Invalid request data",
        },
        500: {
            "description": "Stripe API error or internal server error",
        },
    },
)
async def test_present_payment_method(
    request: TestPaymentMethodRequest,
    session: AsyncSession = Depends(get_session),
) -> TestPaymentMethodResponse:
    """
    Simulate presenting a payment card to a Stripe Terminal reader (TEST MODE ONLY).
    
    This test helper endpoint uses Stripe's TestHelpers API to simulate a customer
    presenting a payment card to a terminal reader. This allows testing the complete
    payment flow without physical terminal hardware. Only works with test API keys.
    
    Args:
        request: Request with companyId, terminalId, and optional test cardNumber
        session: Database session (injected)
        
    Returns:
        TestPaymentMethodResponse with success status, message, and reader ID
        
    Example:
        POST /api/v1/transaction/test/present-payment-method
        Request Body:
        {
            "terminalId": "tmr_FakeReaderID123",
            "cardNumber": "4242424242424242"
        }
        
        Response 200:
        {
            "success": true,
            "message": "Payment method presented successfully to reader tmr_FakeReaderID123",
            "reader_id": "tmr_FakeReaderID123"
        }
    """
    logger.info(
        "Simulating payment method presentation",
        extra={
            "terminal_id": request.TerminalId,
            "card_number": request.CardNumber or "4242424242424242"
        }
    )
    
    try:
        # Validate terminal ID
        if not request.TerminalId:
            raise HTTPException(
                status_code=http_status.HTTP_400_BAD_REQUEST,
                detail="TerminalId is required"
            )
        
        # Get Stripe payment provider for test (cached/singleton)
        logger.info("Getting Stripe provider for test")
        try:
            stripe_provider = await get_stripe_provider(
                session=session,
                company_id=request.CompanyId
            )
        except ValueError as e:
            raise HTTPException(
                status_code=http_status.HTTP_404_NOT_FOUND,
                detail="Stripe provider configuration not found. Please configure Stripe first."
            )
        
        # Use default test card number if not provided
        card_number = request.CardNumber or "4242424242424242"
        
        # Simulate presenting payment method
        logger.info(
            f"Calling Stripe test helper to present payment method",
            extra={"reader_id": request.TerminalId, "card_number": card_number}
        )
        
        reader = await stripe_provider.test_present_payment_method(
            reader_id=request.TerminalId,
            card_number=card_number
        )
        
        logger.info(
            "Payment method presented successfully",
            extra={"reader_id": reader.id}
        )
        
        return TestPaymentMethodResponse(
            success=True,
            message=f"Payment method presented successfully to reader {request.TerminalId}",
            readerId=reader.id
        )
        
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
        
    except Exception as e:
        logger.error(
            f"Error simulating payment method presentation: {str(e)}",
            extra={
                "error": str(e),
                "error_type": type(e).__name__,
                "terminal_id": request.TerminalId,
            },
            exc_info=True,
        )
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to present payment method: {str(e)}"
        )


@router.post(
    "/{transaction_id}/send-receipt",
    status_code=http_status.HTTP_200_OK,
    summary="Send transaction receipt email",
    description="""
    Send a donation receipt or service payment receipt email for an existing transaction.
    
    This endpoint retrieves the transaction details from the database and sends an email
    receipt to the donor's email address. It uses the appropriate email template based on
    the transaction purpose (donation or service payment).
    
    The email will include:
    - Transaction details
    - Donor information
    - Itemized breakdown of donation/service types
    - Total amount
    - Receipt ID for tax purposes
    """,
    responses={
        200: {
            "description": "Email sent successfully",
        },
        400: {
            "description": "Invalid transaction ID or missing email",
        },
        404: {
            "description": "Transaction not found",
        },
        500: {
            "description": "Internal server error",
        },
    },
)
async def send_transaction_receipt(
    transaction_id: int,
    session: AsyncSession = Depends(get_session),
):
    """
    Send a receipt email for a completed transaction.
    
    Args:
        transaction_id: ID of the transaction to send receipt for
        session: Database session (injected)
        
    Returns:
        Success message confirming email was sent
        
    Raises:
        HTTPException: If transaction not found or email cannot be sent
        
    Example:
        POST /api/v1/transaction/12345/send-receipt
        Response 200:
        {
            "success": true,
            "message": "Receipt email sent successfully to donor@example.com",
            "transaction_id": 12345,
            "email": "donor@example.com"
        }
    """
    logger.info(
        f"Sending receipt email for transaction {transaction_id}",
        extra={"transaction_id": transaction_id}
    )
    
    try:
        # Retrieve transaction using utility function
        # Note: We use company_id=0 as a wildcard since we're searching by transaction_id
        transaction = await get_transaction_by_criteria(
            session=session,
            company_id=0,  # Wildcard - transaction_id is unique across all companies
            transaction_id=transaction_id
        )
        
        if not transaction:
            raise HTTPException(
                status_code=http_status.HTTP_404_NOT_FOUND,
                detail=f"Transaction {transaction_id} not found"
            )

        # Check if email address exists
        if not transaction.DonorEmail:
            raise HTTPException(
                status_code=http_status.HTTP_400_BAD_REQUEST,
                detail="No email address associated with this transaction"
            )
        
        # Get company details
        company = await get_company_from_cache(transaction.CompanyId, session)
        if not company:
            raise HTTPException(
                status_code=http_status.HTTP_404_NOT_FOUND,
                detail=f"Company {transaction.CompanyId} not found"
            )
        
        # Get email provider (cached/singleton)
        try:
            email_provider = await get_email_provider(
                session=session,
                company_id=transaction.CompanyId
            )
        except ValueError as e:
            raise HTTPException(
                status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Email provider not configured for this company"
            )
        
        # Generate receipt HTML
        html_content = await create_receipt_html(
            company=company, # type: ignore
            transaction=transaction
        )
        
        if not html_content:
            raise HTTPException(
                status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to generate receipt email content"
            )
        
        # Determine email subject based on purpose
        purpose_id = transaction.PurposeId or 1
        if purpose_id == 1:
            subject = f"Donation Receipt - {transaction_id} - {company.ShortName}"
        else:
            subject = f"Service Payment Receipt - {transaction_id} - {company.ShortName}"
        
        if settings.ENVIRONMENT != "production":
            subject = f"[TEST - TRANSACTION] {subject}"

        # Send email
        await email_provider.send_email(
            to_email=transaction.DonorEmail,
            to_name=transaction.DonorDetails.CompleteName if transaction.DonorDetails else transaction.DonorEmail,
            subject=subject,
            html_content=html_content,
            custom_args={
                "transaction_id": str(transaction_id),
                "company_id": str(transaction.CompanyId),
                "type": "receipt"
            }
        )
        
        logger.info(
            f"Receipt email sent successfully",
            extra={
                "transaction_id": transaction_id,
                "email": transaction.DonorEmail,
                "company_id": transaction.CompanyId
            }
        )
        
        return {
            "success": True,
            "message": f"Receipt email sent successfully to {transaction.DonorEmail}",
            "transaction_id": transaction_id,
            "email": transaction.DonorEmail
        }
        
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
        
    except Exception as e:
        logger.error(
            f"Error sending receipt email: {str(e)}",
            extra={
                "error": str(e),
                "error_type": type(e).__name__,
                "transaction_id": transaction_id,
            },
            exc_info=True,
        )
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to send receipt email: {str(e)}"
        )

