"""
Example script to test the Stripe webhook endpoint locally.

This script simulates Stripe webhook events by sending POST requests
to the webhook endpoint with sample event payloads.

Usage:
    python test_webhook_example.py
"""

import asyncio
import json
from datetime import datetime
from typing import Dict, Any

import httpx


async def test_webhook_endpoint():
    """Test the webhook endpoint with sample events."""
    
    base_url = "http://localhost:8000"
    company_id = "test_company_123"
    
    # Sample webhook events
    test_events = [
        {
            "name": "invoice.paid",
            "payload": {
                "id": "evt_test_invoice_paid",
                "object": "event",
                "api_version": "2023-10-16",
                "created": int(datetime.now().timestamp()),
                "data": {
                    "object": {
                        "id": "in_test_invoice_123",
                        "customer": "cus_test_customer_456", 
                        "amount_paid": 2000,  # $20.00 in cents
                        "status": "paid",
                        "currency": "usd"
                    }
                },
                "livemode": False,
                "pending_webhooks": 1,
                "request": {
                    "id": "req_test_123",
                    "idempotency_key": "test_key"
                },
                "type": "invoice.paid"
            }
        },
        {
            "name": "payout.paid",
            "payload": {
                "id": "evt_test_payout_paid",
                "object": "event", 
                "api_version": "2023-10-16",
                "created": int(datetime.now().timestamp()),
                "data": {
                    "object": {
                        "id": "po_test_payout_123",
                        "amount": 50000,  # $500.00 in cents
                        "currency": "usd",
                        "arrival_date": int(datetime.now().timestamp()) + 86400,  # Tomorrow
                        "status": "paid"
                    }
                },
                "livemode": False,
                "pending_webhooks": 1,
                "request": None,
                "type": "payout.paid"
            }
        },
        {
            "name": "checkout.session.completed",
            "payload": {
                "id": "evt_test_checkout_completed",
                "object": "event",
                "api_version": "2023-10-16",
                "created": int(datetime.now().timestamp()),
                "data": {
                    "object": {
                        "id": "cs_test_session_123",
                        "customer": "cus_test_customer_789",
                        "payment_intent": "pi_test_intent_123", 
                        "amount_total": 3000,  # $30.00 in cents
                        "currency": "usd",
                        "status": "complete"
                    }
                },
                "livemode": False,
                "pending_webhooks": 1,
                "request": None,
                "type": "checkout.session.completed"
            }
        }
    ]
    
    async with httpx.AsyncClient() as client:
        print(f"Testing webhook endpoint: {base_url}/api/v1/webhooks/stripe/{company_id}")
        print("=" * 60)
        
        # Test status endpoint first
        try:
            status_response = await client.get(f"{base_url}/api/v1/webhooks/stripe/{company_id}/status")
            print(f"✓ Status endpoint: {status_response.status_code}")
            if status_response.status_code == 200:
                status_data = status_response.json()
                print(f"  Supported events: {status_data.get('supported_events', [])}")
            print()
        except Exception as e:
            print(f"✗ Status endpoint error: {e}")
            return
        
        # Test each webhook event
        for event in test_events:
            print(f"Testing {event['name']} event...")
            
            try:
                # Test normal processing
                response = await client.post(
                    f"{base_url}/api/v1/webhooks/stripe/{company_id}",
                    json={"webhook_data": event["payload"], "ignore": False}
                )
                
                print(f"  Status Code: {response.status_code}")
                
                if response.status_code == 200:
                    data = response.json()
                    print(f"  ✓ Success: {data.get('success', False)}")
                    print(f"  ✓ Processed: {data.get('processed', False)}")
                    print(f"  Event ID: {data.get('event_id')}")
                    print(f"  Message: {data.get('message')}")
                else:
                    print(f"  ✗ Failed: {response.text}")
                
                # Test with ignore=true
                ignore_response = await client.post(
                    f"{base_url}/api/v1/webhooks/stripe/{company_id}?ignore=true",
                    json={"webhook_data": event["payload"]}
                )
                
                if ignore_response.status_code == 200:
                    ignore_data = ignore_response.json()
                    print(f"  ✓ Ignore test: processed={ignore_data.get('processed', 'unknown')}")
                
            except Exception as e:
                print(f"  ✗ Error: {e}")
            
            print()
        
        # Test unsupported event type
        print("Testing unsupported event type...")
        unsupported_event = {
            "id": "evt_test_unsupported",
            "object": "event",
            "api_version": "2023-10-16", 
            "created": int(datetime.now().timestamp()),
            "data": {"object": {"id": "test_123"}},
            "livemode": False,
            "pending_webhooks": 1,
            "request": None,
            "type": "customer.created"  # Unsupported
        }
        
        try:
            response = await client.post(
                f"{base_url}/api/v1/webhooks/stripe/{company_id}",
                json={"webhook_data": unsupported_event}
            )
            
            if response.status_code == 200:
                data = response.json()
                print(f"  ✓ Handled unsupported event: processed={data.get('processed', False)}")
            
        except Exception as e:
            print(f"  ✗ Error: {e}")
        
        print()
        print("Test completed!")


if __name__ == "__main__":
    print("Stripe Webhook Endpoint Test")
    print("Make sure the API server is running on localhost:8000")
    print()
    
    try:
        asyncio.run(test_webhook_endpoint())
    except KeyboardInterrupt:
        print("\nTest interrupted by user")
    except Exception as e:
        print(f"\nTest failed: {e}")