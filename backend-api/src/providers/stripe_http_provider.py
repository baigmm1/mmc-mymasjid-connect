"""
Stripe HTTP API Provider for direct API calls without SDK limitations.

This provider makes direct HTTP requests to the Stripe API endpoints,
giving full control over request/response data and avoiding any SDK limitations
that might filter or transform the response data.

Usage:
    Use this provider when you need complete access to Stripe API responses
    or when the Python SDK is not returning all the data you need.
"""

import base64
from typing import Any, Dict, List, Optional
import httpx
from datetime import datetime

from src.config import settings
from src.core.logging import get_logger
from src.models.stripe.subscription import SubscriptionModel

logger = get_logger(__name__, level=settings.LOG_LEVEL)


class StripeHTTPProvider:
    """Direct HTTP API provider for Stripe operations."""
    
    def __init__(self, api_key: str):
        """
        Initialize the Stripe HTTP provider.
        
        Args:
            api_key: Stripe secret API key
        """
        self.api_key = api_key
        self.base_url = settings.STRIPE_API_BASE_URL
        self.api_version = settings.STRIPE_API_VERSION
        
        # Create HTTP client with default headers
        self.client = httpx.AsyncClient(
            headers={
                "Authorization": f"Bearer {api_key}",
                "Stripe-Version": self.api_version,
                "Content-Type": "application/x-www-form-urlencoded",
                "User-Agent": f"MasjidConnect/{settings.API_VERSION} StripeHTTP/1.0"
            },
            timeout=30.0
        )
        
        logger.info(f"StripeHTTPProvider initialized with API version {self.api_version}")
    
    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()
    
    async def __aenter__(self):
        """Async context manager entry."""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()
    
    def _handle_stripe_error(self, response: httpx.Response, operation: str) -> None:
        """
        Handle Stripe API error responses.
        
        Args:
            response: HTTP response object
            operation: Description of the operation that failed
            
        Raises:
            Exception: With appropriate error message
        """
        try:
            error_data = response.json()
            error_details = error_data.get("error", {})
            error_message = error_details.get("message", "Unknown Stripe API error")
            error_type = error_details.get("type", "api_error")
            error_code = error_details.get("code")
            
            logger.error(
                f"Stripe API error during {operation}",
                extra={
                    "status_code": response.status_code,
                    "error_type": error_type,
                    "error_code": error_code,
                    "error_message": error_message,
                    "operation": operation
                }
            )
            
            raise Exception(f"Stripe {operation} failed: {error_message} (Type: {error_type}, Code: {error_code})")
            
        except Exception as e:
            if "Stripe" in str(e):
                raise e
            logger.error(f"Failed to parse Stripe error response for {operation}: {e}")
            raise Exception(f"Stripe {operation} failed with status {response.status_code}: {response.text}")
    
    async def get_subscription(
        self, 
        subscription_id: str, 
        expand: Optional[List[str]] = None
    ) -> Dict[str, Any]: # type: ignore
        """
        Retrieve a subscription from Stripe API.
        
        Args:
            subscription_id: ID of the subscription to retrieve
            expand: List of fields to expand in the response
            
        Returns:
            Dict containing the full Stripe subscription object
            
        Raises:
            Exception: If the API request fails
        """
        url = f"{self.base_url}/subscriptions/{subscription_id}"
        
        # Build query parameters
        params = {}
        if expand:
            params["expand[]"] = expand
        
        logger.info(
            f"Fetching subscription via HTTP API: {subscription_id}",
            extra={
                "subscription_id": subscription_id,
                "expand": expand,
                "url": url
            }
        )
        
        try:
            response = await self.client.get(url, params=params)
            
            if response.status_code == 200:
                subscription_data = response.json()
                logger.info(
                    f"Successfully retrieved subscription: {subscription_id}",
                    extra={
                        "subscription_id": subscription_id,
                        "status": subscription_data.get("status"),
                        "customer": subscription_data.get("customer"),
                        "data_size_bytes": len(response.content)
                    }
                )
                return subscription_data
            else:
                self._handle_stripe_error(response, "subscription retrieval")
                
        except httpx.RequestError as e:
            logger.error(
                f"Network error during subscription retrieval: {e}",
                extra={"subscription_id": subscription_id}
            )
            raise Exception(f"Network error retrieving subscription {subscription_id}: {e}")
        except Exception as e:
            logger.error(
                f"Unexpected error during subscription retrieval: {e}",
                extra={"subscription_id": subscription_id}
            )
            raise
    
    async def get_subscription_as_model(
        self, 
        subscription_id: str, 
        expand: Optional[List[str]] = None
    ) -> SubscriptionModel:
        """
        Retrieve a subscription and convert to SubscriptionModel.
        
        Args:
            subscription_id: ID of the subscription to retrieve
            expand: List of fields to expand in the response
            
        Returns:
            SubscriptionModel object
        """
        subscription_data = await self.get_subscription(subscription_id, expand)
        
        # Convert to SubscriptionModel with proper datetime formatting
        created_timestamp = subscription_data.get("created")
        cancel_at_timestamp = subscription_data.get("cancel_at")
        
        subscription_model = SubscriptionModel(
            id=subscription_data["id"],
            customer_id=subscription_data["customer"],
            created=created_timestamp, # type: ignore
            created_datetime=datetime.fromtimestamp(created_timestamp) if created_timestamp else None,
            cancel_at=cancel_at_timestamp,
            cancel_at_datetime=datetime.fromtimestamp(cancel_at_timestamp) if cancel_at_timestamp else None,
            payment_method_id=subscription_data.get("default_payment_method", {}).get("id") if isinstance(subscription_data.get("default_payment_method"), dict) else None  ,
            payment_method_desc=self._extract_payment_method_desc(subscription_data),
            latest_invoice_id=self._extract_latest_invoice_id(subscription_data),
            payment_intent_id=self._extract_payment_intent_id(subscription_data)
        )
        
        logger.info(
            f"Converted subscription to model: {subscription_id}",
            extra={
                "subscription_id": subscription_id,
                "customer_id": subscription_model.customer_id,
                "created_datetime": subscription_model.created_datetime,
                "cancel_at_datetime": subscription_model.cancel_at_datetime
            }
        )
        
        return subscription_model
    
    def _extract_payment_method_desc(self, subscription_data: Dict[str, Any]) -> Optional[str]:
        """Extract payment method description from subscription data."""
        payment_method_desc = None
        payment_method_object = subscription_data.get("default_payment_method")
        if isinstance(payment_method_object, str):
            payment_method_desc = payment_method_object
        elif isinstance(payment_method_object, dict):
            if payment_method_object.get("type") == "card":
                card_details = payment_method_object.get("card", {})
                payment_method_desc = f"{card_details.get("brand")} ****{card_details.get("last4")}"  # type: ignore    
            elif payment_method_object.get("type") == "us_bank_account":
                bank_details = payment_method_object.get("us_bank_account", {})
                payment_method_desc = f"{bank_details.get("bank_name")} ****{bank_details.get("last4")}"  # type: ignore
            else:
                payment_method_desc = f"Type {payment_method_object.get("type")}"  # type: ignore
            
        return payment_method_desc
    
    def _extract_latest_invoice_id(self, subscription_data: Dict[str, Any]) -> Optional[str]:
        """Extract latest invoice ID from subscription data."""
        latest_invoice = subscription_data.get("latest_invoice")
        if isinstance(latest_invoice, str):
            return latest_invoice
        elif isinstance(latest_invoice, dict):
            return latest_invoice.get("id")
        return None
    
    def _extract_payment_intent_id(self, subscription_data: Dict[str, Any]) -> Optional[str]:
        """Extract payment intent ID from subscription data."""
        # Try to get from expanded latest_invoice
        latest_invoice = subscription_data.get("latest_invoice")
        if isinstance(latest_invoice, dict):
            payment_intent = latest_invoice.get("payment_intent")
            if isinstance(payment_intent, str):
                return payment_intent
            elif isinstance(payment_intent, dict):
                return payment_intent.get("id")
        return None
    
    async def get_customer(self, customer_id: str) -> Dict[str, Any]:
        """
        Retrieve a customer from Stripe API.
        
        Args:
            customer_id: ID of the customer to retrieve
            
        Returns:
            Dict containing the full Stripe customer object
        """
        url = f"{self.base_url}/customers/{customer_id}"
        
        logger.info(f"Fetching customer via HTTP API: {customer_id}")
        
        try:
            response = await self.client.get(url)
            
            if response.status_code == 200:
                customer_data = response.json()
                logger.info(f"Successfully retrieved customer: {customer_id}")
                return customer_data
            else:
                self._handle_stripe_error(response, "customer retrieval")
                
        except httpx.RequestError as e:
            logger.error(f"Network error during customer retrieval: {e}")
            raise Exception(f"Network error retrieving customer {customer_id}: {e}")
    
    async def get_invoice(self, invoice_id: str, expand: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Retrieve an invoice from Stripe API.
        
        Args:
            invoice_id: ID of the invoice to retrieve
            expand: List of fields to expand in the response
            
        Returns:
            Dict containing the full Stripe invoice object
        """
        url = f"{self.base_url}/invoices/{invoice_id}"
        
        # Build query parameters
        params = {}
        if expand:
            params["expand[]"] = expand
        
        logger.info(f"Fetching invoice via HTTP API: {invoice_id}")
        
        try:
            response = await self.client.get(url, params=params)
            
            if response.status_code == 200:
                invoice_data = response.json()
                logger.info(f"Successfully retrieved invoice: {invoice_id}")
                return invoice_data
            else:
                self._handle_stripe_error(response, "invoice retrieval")
                
        except httpx.RequestError as e:
            logger.error(f"Network error during invoice retrieval: {e}")
            raise Exception(f"Network error retrieving invoice {invoice_id}: {e}")


# Global instance factory
def create_stripe_http_provider(api_key: str) -> StripeHTTPProvider:
    """
    Factory function to create a StripeHTTPProvider instance.
    
    Args:
        api_key: Stripe secret API key
        
    Returns:
        StripeHTTPProvider instance
    """
    return StripeHTTPProvider(api_key)