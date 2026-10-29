import json
from typing import Any, Dict, Optional
from fastapi import params
import stripe
from stripe import ListObject, error as stripe_error

from src.core.logging import get_logger
from src.config import settings
#from src.core.provider_config_utils import get_provider_config
from src.models.donors import DonorsModel
from src.models.transaction import TransactionModel
from src.models.company import CompanyModel
from datetime import datetime, timezone, timedelta
from src.models.stripe.subscription import SubscriptionModel
from src.core.payment_utils import get_payment_description, get_statement_descriptor_suffix, get_transaction_description

logger = get_logger(__name__, level=settings.LOG_LEVEL)

class StripePaymentProvider:
    """Stripe payment provider integration."""

    def __init__(self, api_key: str, merchant_id: str):
        """Initialize Stripe with the provided API key."""
        self.api_key = api_key
        self.merchant_id = merchant_id
        
        stripe.api_key = self.api_key
        self.client = stripe.StripeClient(self.api_key)
        
        logger.debug("StripePaymentProvider initialized with provided API key.")

    async def get_customer(self, email: str) -> Optional[stripe.Customer]:
        """
        Retrieve a Stripe customer by email.

        Args:
            email: Customer's email address

        Returns:
            stripe.Customer object if found, else None
        """
        try:
            customers = await stripe.Customer.list_async(email=email, limit=10)
            if customers.data:                
                logger.info(f"Customer found with email: {email}")
                customers.data.sort(key=lambda c: c.created, reverse=True)  # Sort by creation date, newest first
                return customers.data[0]
            else:
                logger.info(f"No customer found with email: {email}")
                return None
        except stripe_error.StripeError as e:
            logger.error(f"Stripe error occurred: {e.user_message}", exc_info=True)
            raise
        except Exception as e:
            logger.error(f"Unexpected error occurred while retrieving customer: {e}", exc_info=True)
            raise   

    async def get_customers_by_email(self, email: str) -> list[stripe.Customer]:
        """
        Retrieve all Stripe customers matching the given email.

        Args:
            email: Customer's email address

        Returns:
            List of stripe.Customer objects matching the email
        """
        try:
            customers = await stripe.Customer.list_async(email=email, limit=100)
            customers.data.sort(key=lambda c: c.created, reverse=True)  # Sort by creation date, newest first
            logger.info(f"Retrieved {len(customers.data)} customers with email: {email}")
            return customers.data
        except stripe_error.StripeError as e:
            logger.error(f"Stripe error occurred: {e.user_message}", exc_info=True)
            raise
        except Exception as e:
            logger.error(f"Unexpected error occurred while retrieving customers: {e}", exc_info=True)
            raise    
    
    async def create_customer(self, donor: DonorsModel) -> stripe.Customer:
        """
        Create a new Stripe customer.

        Args:
            donor: DonorsModel object containing donor information

        Returns:
            stripe.Customer object representing the created customer
        """
        try:
            customer = await stripe.Customer.create_async(
                name=donor.CompleteName or "",
                email=donor.EMail or "",
                address={
                    "line1": donor.AddressLine1,
                    "line2": donor.AddressLine2,
                    "city": donor.City,
                    "state": donor.State,
                    "postal_code": donor.PostalCode,
                    "country": donor.CountryCode,
                } if donor.AddressLine1 else None, # type: ignore
                phone=donor.PhoneNumber or "",
                business_name=donor.CompanyName or "",
            )
            logger.info(f"Customer created successfully: {customer.id}")
            return customer
        except stripe_error.StripeError as e:
            logger.error(f"Stripe error occurred: {e.user_message}", exc_info=True)
            raise
        except Exception as e:
            logger.error(f"Unexpected error occurred while creating customer: {e}", exc_info=True)
            raise
    async def create_payment_intent_terminal(self, amount: int, currency: str, description: str, statement_description:str, donor: DonorsModel|None = None) -> stripe.PaymentIntent:
        """
        Create a payment intent using Stripe Terminal.

        Args:
            amount: Amount to charge in smallest currency unit (e.g., cents)
            currency: Currency code (e.g., 'usd')
            donor: DonorsModel object containing donor information (optional)
        Returns:
            stripe.PaymentIntent object representing the created payment intent
        """
        try:
            customer = await self.get_customer(donor.EMail) if donor and donor.EMail else None
            if donor and donor.EMail and not customer:                
                customer =  await self.create_customer(donor)

            intent_params = {
                'amount': amount,
                'currency': currency,
                'payment_method_types': ['card_present'],
                'capture_method': 'manual',
                'description': description if description else "In-Person Payment",
                'statement_descriptor': statement_description if statement_description else "In-Person Payment",
            }
            
            if customer:
                intent_params['customer'] = customer.id
            
            if donor and donor.EMail:
                intent_params['receipt_email'] = donor.EMail
            
            intent = await stripe.PaymentIntent.create_async(**intent_params)
            logger.info(f"PaymentIntent created successfully: {intent.id}")
            return intent
        except stripe_error.StripeError as e:
            logger.error(f"Stripe error occurred: {e.user_message}", exc_info=True)
            raise
        except Exception as e:
            logger.error(f"Unexpected error occurred while creating PaymentIntent: {e}", exc_info=True)
            raise

    async def process_terminal_payment(self, payment_intent_id: str, reader_id: str) -> stripe.terminal.Reader:
        """
        Process a payment using Stripe Terminal.

        Args:
            payment_intent_id: ID of the PaymentIntent to process
            reader_id: ID of the Stripe Terminal reader

        Returns:
            stripe.terminal.Reader object representing the processed payment intent
        """
        try:
            reader = await stripe.terminal.Reader.process_payment_intent_async(
                reader=reader_id,
                payment_intent=payment_intent_id,
            )
            return reader
        except stripe_error.StripeError as e:
            logger.error(f"Stripe error occurred: {e.user_message}", exc_info=True)
            raise
        except Exception as e:
            logger.error(f"Unexpected error occurred while processing PaymentIntent: {e}", exc_info=True)
            raise

    async def capture_payment_intent(self, payment_intent_id: str) -> stripe.PaymentIntent:
        """
        Capture a previously created PaymentIntent.

        Args:
            payment_intent_id: ID of the PaymentIntent to capture

        Returns:
            stripe.PaymentIntent object representing the captured payment intent
        """
        try:
            intent = await stripe.PaymentIntent.capture_async(payment_intent_id)
            logger.info(f"PaymentIntent captured successfully: {intent.id}")
            return intent
        except stripe_error.StripeError as e:
            logger.error(f"Stripe error occurred: {e.user_message}", exc_info=True)
            raise
        except Exception as e:
            logger.error(f"Unexpected error occurred while capturing PaymentIntent: {e}", exc_info=True)
            raise

    async def get_payment_method(self, payment_method_id: str) -> stripe.PaymentMethod:
        """
        Retrieve a Stripe PaymentMethod by ID.

        Args:
            payment_method_id: ID of the PaymentMethod to retrieve

        Returns:
            stripe.PaymentMethod object
        """
        try:
            payment_method = await stripe.PaymentMethod.retrieve_async(payment_method_id)
            logger.info(f"PaymentMethod retrieved successfully: {payment_method.id}")
            return payment_method
        except stripe_error.StripeError as e:
            logger.error(f"Stripe error occurred: {e.user_message}", exc_info=True)
            raise
        except Exception as e:
            logger.error(f"Unexpected error occurred while retrieving PaymentMethod: {e}", exc_info=True)
            raise
        
    async def get_reader_status(self, reader_id: str) -> stripe.terminal.Reader:
        """
        Retrieve the status of a Stripe Terminal reader.

        Args:
            reader_id: ID of the Stripe Terminal reader

        Returns:
            stripe.terminal.Reader object with the reader status
        """
        try:
            reader = await stripe.terminal.Reader.retrieve_async(reader_id)
            logger.info(f"Retrieved reader status successfully: {reader.id}")
            return reader
        except stripe_error.StripeError as e:
            logger.error(f"Stripe error occurred: {e.user_message}", exc_info=True)
            raise
        except Exception as e:
            logger.error(f"Unexpected error occurred while retrieving reader status: {e}", exc_info=True)
            raise

    async def cancel_reader_action(self, reader_id: str) -> stripe.terminal.Reader:
        """
        Cancel the current action on a Stripe Terminal reader.

        Args:
            reader_id: ID of the Stripe Terminal reader

        Returns:
            stripe.terminal.Reader object with the updated reader status
        """
        try:
            reader = await stripe.terminal.Reader.cancel_action_async(reader_id)
            logger.info(f"Cancelled reader action successfully: {reader.id}")
            return reader
        except stripe_error.StripeError as e:
            logger.error(f"Stripe error occurred: {e.user_message}", exc_info=True)
            raise
        except Exception as e:
            logger.error(f"Unexpected error occurred while cancelling reader action: {e}", exc_info=True)
            raise

    async def test_present_payment_method(self, reader_id: str, card_number: str = "4242424242424242") -> stripe.terminal.Reader:
        """
        Simulate presenting a payment method to a Stripe Terminal reader (TEST MODE ONLY).

        This uses Stripe's test helpers to simulate card presentation without
        physical hardware. Only works with test mode API keys.

        Args:
            reader_id: ID of the Stripe Terminal reader
            card_number: Test card number to simulate (default: 4242424242424242)

        Returns:
            stripe.terminal.Reader object with the simulated payment method

        Raises:
            stripe.error.StripeError: If Stripe API call fails
        """
        try:
            reader = await stripe.terminal.Reader.TestHelpers.present_payment_method_async(
                reader_id,
                card_present={"number": card_number},
                type="card_present",
            )
            logger.info(f"Test payment method presented successfully to reader: {reader_id}")
            return reader
        except stripe_error.StripeError as e:
            logger.error(f"Stripe error occurred during test payment method presentation: {e.user_message}", exc_info=True)
            raise
        except Exception as e:
            logger.error(f"Unexpected error occurred while presenting test payment method: {e}", exc_info=True)
            raise

    async def create_checkout_session(self, reference_id: str, transaction: TransactionModel, 
                                      donor: DonorsModel|None = None, company: CompanyModel|None = None ) -> stripe.checkout.Session:
        """
        Create a Stripe Checkout Session for online payments.

        Args:
            amount: Amount to charge in smallest currency unit (e.g., cents)
            currency: Currency code (e.g., 'usd')
            success_url: URL to redirect to upon successful payment
            cancel_url: URL to redirect to if the payment is canceled
            donor: DonorsModel object containing donor information (optional)
            company: CompanyModel object containing company information (optional)
        Returns:
            stripe.checkout.Session object representing the created checkout session
        """
        try:
            customer = await self.get_customer(donor.EMail) if donor and donor.EMail else None
            if donor and donor.EMail and not customer:                
                customer =  await self.create_customer(donor)
            
            #description = f"Donation from {transaction.DonorName}" if transaction.PurposeId == 1 else f"Service Payment from {transaction.DonorName} "
            if transaction.Description:
                description = transaction.Description
            else:
                description = get_transaction_description(transaction=transaction)

            # use the transaction details to generate line items
            line_items = []
            if transaction.Details:
                for item in transaction.Details:
                    product = await self.search_product(item.DonationTypeId, item.Description)
                    if not product:
                        product = await self.create_product(item.DonationTypeId, item.Description or f"Donation {item.DonationTypeId}")

                    price_data = {
                        'product': product.id,
                        'currency': transaction.Currency,
                        'unit_amount': int(item.Amount * 100),
                    }
                    if transaction.Recurring:
                        # Determine interval based on RecurringFrequency
                        # 1 = Monthly (default), 2 = Yearly, 3 = Daily
                        frequency = transaction.RecurringFrequency or 1
                        if frequency == 2:  # Yearly
                            interval = 'year'
                        elif frequency == 3:  # Daily
                            interval = 'day'
                        else:  # Monthly (default)
                            interval = 'month'
                        
                        price_data['recurring'] = {
                            'interval': interval,
                            'interval_count': 1,
                    }
                    
                    line_item = {
                        'price_data': price_data,
                        'quantity': 1,
                    }
                    line_items.append(line_item)
            else:
                line_items.append({
                    'price_data': {
                        'currency': transaction.Currency,
                        'product_data': {
                            'name': description if description else "Donation",
                        },
                        'unit_amount': int(transaction.TotalAmount * 100),
                    },
                    'quantity': 1,
                })
                        
            session_params = {
                'client_reference_id': reference_id,
                'success_url': transaction.SuccessURL,
                'cancel_url': transaction.CancelURL,
                'mode': 'subscription' if transaction.Recurring else 'payment',
                'line_items': line_items,
                'ui_mode': 'hosted',                
            }            

            if customer:
                session_params['customer'] = customer.id
            elif donor and donor.EMail:
                session_params['customer_create'] = 'if_required'
                session_params['customer_email'] = donor.EMail

            if not transaction.Recurring:
                session_params['payment_intent_data'] = {
                    'description': description if description else "Online Payment",
                    'statement_descriptor': get_payment_description(company_short_name=company.ShortName if company and company.ShortName else "Masjid", purpose=transaction.PurposeId or 1),
                    'statement_descriptor_suffix': get_statement_descriptor_suffix(transaction)
                }
            if transaction.Recurring and transaction.NumberofMonths and transaction.NumberofMonths > 1:
                # Map frequency to readable format for metadata
                frequency_map = {1: 'Monthly', 2: 'Yearly', 3: 'Daily'}
                frequency = transaction.RecurringFrequency or 1
                frequency_label = frequency_map.get(frequency, 'Monthly')
                
                session_params['subscription_data'] = {
                    'description': description if description else "Online Subscription",
                    'metadata': {
                        'numberofMonths': str(transaction.NumberofMonths),
                        'recurringFrequency': str(frequency),
                        'frequencyLabel': frequency_label,
                    }
                }
            session = await stripe.checkout.Session.create_async(**session_params)
            logger.info(f"Checkout Session created successfully: {session.id}")
            return session

        except stripe_error.StripeError as e:
            logger.error(f"Stripe error occurred: {e.user_message}", exc_info=True)
            raise
        except Exception as e:
            logger.error(f"Unexpected error occurred while creating PaymentIntent: {e}", exc_info=True)
            raise

    async def get_checkout_session(self, session_id: str, expand: list[str] | None = None) -> stripe.checkout.Session:
        """
        Retrieve a Stripe Checkout Session by ID.

        Args:
            session_id: ID of the Checkout Session to retrieve

        Returns:
            stripe.checkout.Session object
        """
        try:
            if expand is None:
                session = await stripe.checkout.Session.retrieve_async(session_id)
            else:
                session = await stripe.checkout.Session.retrieve_async(session_id, expand=expand)
            logger.info(f"Checkout Session retrieved successfully: {session.id}")
            return session
        except stripe_error.StripeError as e:
            logger.error(f"Stripe error occurred: {e.user_message}", exc_info=True)
            raise
        except Exception as e:
            logger.error(f"Unexpected error occurred while retrieving Checkout Session: {e}", exc_info=True)
            raise
        
    async def search_product(self, donationType: int, description: str | None = None) -> stripe.Product|None:
        """
          Search for a Stripe product by donation type.

          Args:
              donationType: Donation type identifier
            Returns:
              stripe.Product object if found, else None
        """
        try:
            query = "active: '{}' AND metadata[\"donationType\"]:'{}'".format('true', donationType)
            products = await stripe.Product.search_async(
                query=query,
                limit=1,
            )
            if not products.data:
                # check if the description matches
                logger.info(f"No products found matching query: {query}. Checking for products matching description: {description}")
                if description:
                    query = "active: '{}' AND name~'{}'".format('true', description)
                    products = await stripe.Product.search_async(
                        query=query,
                        limit=1,
                    )
                    if not products.data:
                        logger.info(f"No products found matching query: {query}")
                        return None
                else:
                    logger.info(f"No products found matching query: {query}")
                    return None
            
            return products.data[0]
            
        except stripe_error.StripeError as e:
            logger.error(f"Stripe error occurred: {e.user_message}", exc_info=True)
            raise

    async def get_product_by_id(self, product_id: str) -> stripe.Product:
        """
        Retrieve a Stripe product by ID.

        Args:
            product_id: ID of the product to retrieve

        Returns:
            stripe.Product object representing the retrieved product
        """
        try:
            product = await stripe.Product.retrieve_async(product_id)
            logger.info(f"Product retrieved successfully: {product.id}")
            return product
        except stripe_error.StripeError as e:
            logger.error(f"Stripe error occurred: {e.user_message}", exc_info=True)
            raise
        except Exception as e:
            logger.error(f"Unexpected error occurred while retrieving product: {e}", exc_info=True)
            raise
        
    async def create_product(self, donationType: int, description: str) -> stripe.Product:
        """
        Create a new Stripe product.

        Args:
            donationType: Donation type identifier
            description: Description of the product

        Returns:
            stripe.Product object representing the created product
        """
        try:
            product = await stripe.Product.create_async(
                name=description,
                description=description,
                active=True,
                metadata={
                    'donationType': str(donationType),
                }
            )
            logger.info(f"Product created successfully: {product.id}")
            return product
        except stripe_error.StripeError as e:
            logger.error(f"Stripe error occurred: {e.user_message}", exc_info=True)
            raise
        except Exception as e:
            logger.error(f"Unexpected error occurred while creating product: {e}", exc_info=True)
            raise

    async def get_subscription(self, subscription_id: str, expand: list[str] | None = None) -> SubscriptionModel:
        """
        Retrieve a Stripe Subscription by ID.

        Args:
            subscription_id: ID of the Subscription to retrieve
            expand: List of fields to expand in the response (optional)
        Returns:
            SubscriptionModel object
        """
        try:
            if expand is None:
                subscription = await stripe.Subscription.retrieve_async(subscription_id)
            else:
                subscription = await stripe.Subscription.retrieve_async(subscription_id, expand=expand)                
            logger.info(f"Subscription retrieved successfully: {subscription.id}")
            # extract relevant fields into SubscriptionModel
            invoice_data = subscription.latest_invoice if hasattr(subscription, "latest_invoice") else None
            payment_method_data = subscription.get("default_payment_method")

            subscription_model = SubscriptionModel(
                id=subscription.id,
                customer_id=subscription.get("customer"), # type: ignore
                created=subscription.get("created"), # type: ignore
                created_datetime=datetime.fromtimestamp(subscription.get("created")) if subscription.get("created") else None, # type: ignore
                cancel_at=subscription.get("cancel_at"), # type: ignore
                cancel_at_datetime=datetime.fromtimestamp(subscription.get("cancel_at")) if subscription.get("cancel_at") else None, # type: ignore
                latest_invoice_id = self.extract_latest_invoice_id(invoice_data),  # type: ignore
                payment_method_id=payment_method_data.get("id") if isinstance(payment_method_data, dict) else None, # type: ignore
                payment_method_desc = self.extract_payment_method_desc(payment_method_data),
                payment_intent_id = self.extract_payment_intent_id(invoice_data), # type: ignore
            )     

            return subscription_model   
        except stripe_error.StripeError as e:
            logger.error(f"Stripe error occurred: {e.user_message}", exc_info=True)
            raise
        except Exception as e:
            logger.error(f"Unexpected error occurred while retrieving Subscription: {e}", exc_info=True)
            raise

    async def update_subscription_cancel_date(self, subscription_id: str, frequency: int, number_of_periods: int) -> stripe.Subscription:
        """
        Update the cancellation date of a Stripe Subscription.

        Args:
            subscription_id: ID of the Subscription to update
            frequency: Frequency of the subscription (1 = Monthly, 2 = Yearly, 3 = Daily)
            number_of_months: Number of months to extend the cancellation date

        Returns:
            stripe.Subscription object representing the updated subscription
        """
        try:
            # calculate cancel_at timestamp   
            if frequency == 1:  # Monthly
                cancel_at = int((datetime.now(timezone.utc) + timedelta(days=30 * number_of_periods)).timestamp())
            elif frequency == 2:  # Yearly
                cancel_at = int((datetime.now(timezone.utc) + timedelta(days=365 * number_of_periods)).timestamp())
            elif frequency == 3:  # Daily
                cancel_at = int((datetime.now(timezone.utc) + timedelta(days=number_of_periods)).timestamp())                     

            subscription = await stripe.Subscription.modify_async(
                subscription_id,
                cancel_at=cancel_at,
            )

            # retrieve subscription again with expanded latest invoice to get payment intent
            subscription = await stripe.Subscription.retrieve_async(subscription_id, expand=['latest_invoice', 'default_payment_method'])
            logger.info(f"Subscription updated successfully: {subscription.id}")
            return subscription
        except stripe_error.StripeError as e:
            logger.error(f"Stripe error occurred: {e.user_message}", exc_info=True)
            raise
        except Exception as e:
            logger.error(f"Unexpected error occurred while updating Subscription: {e}", exc_info=True)
            raise

    async def get_invoice(self, invoice_id: str, expand: list[str] | None = None) -> stripe.Invoice:
        """
        Retrieve a Stripe Invoice by ID.

        Args:
            invoice_id: ID of the Invoice to retrieve

        Returns:
            stripe.Invoice object
        """
        try:
            if expand is None:
                invoice = await stripe.Invoice.retrieve_async(invoice_id)
            else:
                invoice = await stripe.Invoice.retrieve_async(invoice_id, expand=expand)
            logger.info(f"Invoice retrieved successfully: {invoice.id}")
            return invoice
        except stripe_error.StripeError as e:
            logger.error(f"Stripe error occurred: {e.user_message}", exc_info=True)
            raise
        except Exception as e:
            logger.error(f"Unexpected error occurred while retrieving Invoice: {e}", exc_info=True)
            raise   
        
    async def get_subscriptions(self, email: str | None = None, status: str | None = None, expand: list[str] | None = None) -> list[stripe.Subscription]:
        """
        Retrieve all Stripe Subscriptions for a customer by email.

        Args:
            email: Customer's email address 
            status: Filter by subscription status - 'active', 'canceled', 'all', etc.
        Returns:
            List of stripe.Subscription objects
        """
        try:
            subscriptions = []
            params = {
                "limit": '100',
            }

            if email:
                customer = await self.get_customer(email)
                if customer:
                    params['customer'] = customer.id

            if status:
                params['status'] = status
            
            if expand:
                params['expand'] = expand   # type: ignore

            more_data = True
            while more_data:
                subscriptions_list = await stripe.Subscription.list_async(**params) # type: ignore
                subscriptions.extend(subscriptions_list.data)
                if subscriptions_list.has_more:
                    params['starting_after'] = subscriptions_list.data[-1].id
                else:
                    more_data = False

            # we may have the same subscriptions for the same customer registered under different customers in Stripe if they used different emails or if there were duplicates. To ensure we get all subscriptions, we first retrieve all customers with the given email and then retrieve subscriptions for each customer.
            # customers = await stripe.Customer.list_async(email=email, limit=100, expand=['data.subscriptions'])
            # if not customers:
            #     logger.info(f"No customers found with email: {email}")
            #     return []
            # for customer in customers.data:
            #     if customer.subscriptions and customer.subscriptions.data:
            #         subscriptions.extend(customer.subscriptions.data)

            # logger.info(f"Retrieved {len(subscriptions)} subscriptions for customers with email: {email}")
            return subscriptions
        except stripe_error.StripeError as e:
            logger.error(f"Stripe error occurred: {e.user_message}", exc_info=True)
            raise
        except Exception as e:
            logger.error(f"Unexpected error occurred while retrieving Subscriptions: {e}", exc_info=True)
            raise
    
    async def get_balance_transactions(self, payout_id: str, expand: list[str] | None = None, starting_after: str | None = None) -> ListObject[stripe.BalanceTransaction]:
        """
        Retrieve all Stripe Balance Transactions for a given payout ID.

        Args:
            payout_id: Stripe payout ID
        Returns:
            List of stripe.BalanceTransaction objects
        """

        try:
            balance_transactions = []
            # we can retrieve balance transactions related to a payout by filtering on the payout ID in the Stripe API
            params = {
                'payout': payout_id,
                'limit': 100,
            }
            if expand:
                params['expand'] = expand

            if starting_after:
                params['starting_after'] = starting_after

            transactions = await stripe.BalanceTransaction.list_async(**params)
            return transactions
        except stripe_error.StripeError as e:
            logger.error(f"Stripe error occurred: {e.user_message}", exc_info=True)
            raise
        except Exception as e:
            logger.error(f"Unexpected error occurred while retrieving Balance Transactions: {e}", exc_info=True)
            raise

    def extract_payment_method_desc(self, payment_method_data: Dict[str, Any] | None) -> Optional[str]:
        """Extract payment method description from subscription data."""
        payment_method_desc = None
        
        if isinstance(payment_method_data, str):
            payment_method_desc = payment_method_data
        elif isinstance(payment_method_data, dict):
            if payment_method_data.get("type") == "card":
                card_details = payment_method_data.get("card", {})
                payment_method_desc = f"{card_details.get('brand')} ****{card_details.get('last4')}"  # type: ignore
            elif payment_method_data.get("type") == "us_bank_account":
                bank_details = payment_method_data.get("us_bank_account", {})
                payment_method_desc = f"{bank_details.get('bank_name')} ****{bank_details.get('last4')}"  # type: ignore
            else:
                payment_method_desc = f"Type {payment_method_data.get('type')}"  # type: ignore
            
        return payment_method_desc
    
    def extract_latest_invoice_id(self, invoice_data: Dict[str, Any] | None) -> Optional[str]:
        """Extract latest invoice ID from subscription data."""
        if isinstance(invoice_data, str):
            return invoice_data
        elif isinstance(invoice_data, dict):
            return invoice_data.get("id")
        return None
    
    def extract_payment_intent_id(self, invoice_data: Dict[str, Any] | None) -> Optional[str]:
        """Extract payment intent ID from subscription data."""
        #logger.info(f"Extracting payment intent ID from invoice data: {invoice_data}")
        if isinstance(invoice_data, dict):
            payment_intent = invoice_data.get("payment_intent")
            if payment_intent:
                if isinstance(payment_intent, str):
                    return payment_intent
                elif isinstance(payment_intent, dict):
                    return payment_intent.get("id")
            else:
                payments = invoice_data.get("payments", {})
                #logger.info(f"Extracting payment intent ID from invoice payments data 1: {payments}")
                if payments:                    
                    payment_list = payments.get("data", [])
                    if len(payment_list) > 0:
                        invoice_payment = payment_list[0].get("payment")
                        #logger.info(f"Extracting payment intent ID from invoice payment data 2: {invoice_payment}")
                        pi = invoice_payment.get("payment_intent")
                        return pi                    
        return None
    async def get_charge(self, charge_id: str, expand: list[str] | None = None) -> stripe.Charge:
        """
        Retrieve a Stripe Charge by ID.

        Args:
            charge_id: ID of the Charge to retrieve

        Returns:
            stripe.Charge object
        """
        try:
            if expand is None:
                charge = await stripe.Charge.retrieve_async(charge_id)
            else:           
                charge = await stripe.Charge.retrieve_async(charge_id, expand=expand)

            logger.info(f"Charge retrieved successfully: {charge.id}")
            return charge
        except stripe_error.StripeError as e:
            logger.error(f"Stripe error occurred: {e.user_message}", exc_info=True)
            raise
        except Exception as e:
            logger.error(f"Unexpected error occurred while retrieving Charge: {e}", exc_info=True)
            raise
    async def get_payment_intent_lineitems(self, payment_intent_id: str) -> ListObject[stripe.PaymentIntentAmountDetailsLineItem]:
        """
        Retrieve line items for a Stripe PaymentIntent.

        Args:
            payment_intent_id: ID of the PaymentIntent to retrieve line items for
        Returns:
            List of stripe.PaymentIntentAmountDetailsLineItem objects associated with the PaymentIntent
        """ 
        try:
            line_items = await self.client.v1.payment_intents.amount_details_line_items.list_async(
                intent=payment_intent_id,
            )
            logger.info(f"Retrieved {len(line_items.data)} line items for PaymentIntent: {payment_intent_id}")
            return line_items
        except stripe_error.StripeError as e:
            logger.error(f"Stripe error occurred: {e.user_message}", exc_info=True)
            raise
        except Exception as e:
            logger.error(f"Unexpected error occurred while retrieving line items for PaymentIntent: {e}", exc_info=True)
            raise

    # async def create_charge(self, amount: int, currency: str, source: str, description: str) -> stripe.Charge:
    #     """
    #     Create a charge using Stripe.

    #     Args:
    #         amount: Amount to charge in smallest currency unit (e.g., cents)
    #         currency: Currency code (e.g., 'usd')
    #         source: Payment source token
    #         description: Description of the charge

    #     Returns:
    #         stripe.Charge object representing the created charge
    #     """
    #     try:
    #         charge = stripe.Charge.create(
    #             amount=amount,
    #             currency=currency,
    #             source=source,
    #             description=description,
    #         )
    #         logger.info(f"Charge created successfully: {charge.id}")
    #         return charge
    #     except stripe.error.StripeError as e:
    #         logger.error(f"Stripe error occurred: {e.user_message}", exc_info=True)
    #         raise
    #     except Exception as e:
    #         logger.error(f"Unexpected error occurred while creating charge: {e}", exc_info=True)
    #         raise