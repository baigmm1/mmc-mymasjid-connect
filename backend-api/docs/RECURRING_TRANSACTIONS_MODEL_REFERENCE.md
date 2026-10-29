# Recurring Transactions Data Model - Quick Reference

## Overview

The Recurring Transactions data model represents subscription-based recurring donations from payment providers like Stripe. The model consists of three related tables:

1. **RecurringTransactions** - Main transaction/subscription header
2. **RecurringTransactionDetails** - Line item details for each subscription
3. **RecurringTransactionPayments** - Payment history linking to actual donation receipts

## Database Schema

### RecurringTransactions Table

| Column         | Type                  | Nullable | Description                                   |
| -------------- | --------------------- | -------- | --------------------------------------------- |
| TransactionId  | INT IDENTITY(10001,1) | No       | Primary key, auto-increment starting at 10001 |
| CompanyId      | INT                   | No       | Reference to Company table                    |
| DonorId        | INT                   | Yes      | Reference to Donors table                     |
| ReviewDonorId  | INT                   | Yes      | Reference to ReviewDonors table               |
| StartDate      | DATETIME              | No       | Subscription start date                       |
| Frequency      | INT                   | No       | Frequency type (1=Monthly, 2=Yearly, etc.)    |
| FrequencyCount | INT                   | No       | Number of frequency units                     |
| EndDate        | DATETIME              | No       | Subscription end/cancellation date            |
| ProviderName   | NVARCHAR(50)          | Yes      | Payment provider (e.g., 'Stripe')             |
| SubscriptionId | NVARCHAR(100)         | Yes      | Provider's unique subscription ID             |
| PaymentMethod  | NVARCHAR(100)         | Yes      | Payment method ID or description              |
| TotalAmount    | MONEY                 | Yes      | Total subscription amount                     |
| Status         | INT                   | No       | Current status code                           |
| CreatedBy      | INT                   | Yes      | User who created the record                   |
| CreatedDate    | DATETIME              | Yes      | Creation timestamp                            |
| ModifiedBy     | INT                   | Yes      | User who last modified                        |
| ModifiedDate   | DATETIME              | Yes      | Last modification timestamp                   |

### RecurringTransactionDetails Table

| Column        | Type       | Nullable | Description                                         |
| ------------- | ---------- | -------- | --------------------------------------------------- |
| TransactionId | INT        | No       | Foreign key to RecurringTransactions (composite PK) |
| LineNumber    | INT        | No       | Line number within transaction (composite PK)       |
| CompanyId     | INT        | No       | Reference to Company                                |
| DonationType  | INT        | No       | Type of donation                                    |
| Amount        | MONEY      | Yes      | Line item amount                                    |
| Currency      | VARCHAR(3) | Yes      | Currency code (e.g., 'USD')                         |

### RecurringTransactionPayments Table

| Column            | Type | Nullable | Description                                         |
| ----------------- | ---- | -------- | --------------------------------------------------- |
| TransactionId     | INT  | No       | Foreign key to RecurringTransactions (composite PK) |
| LineNumber        | INT  | No       | Line number (composite PK)                          |
| DonationReceiptId | INT  | No       | Reference to DonationReceipts                       |

## Status Codes

| Code | Name               | Description                     |
| ---- | ------------------ | ------------------------------- |
| 0    | INCOMPLETE         | Incomplete/pending subscription |
| 1    | ACTIVE             | Active subscription             |
| 2    | CANCELED           | Canceled subscription           |
| 3    | INCOMPLETE_EXPIRED | Expired incomplete subscription |
| 4    | TRIALING           | Trial period                    |
| 5    | PAST_DUE           | Payment overdue                 |
| 6    | UNPAID             | Unpaid subscription             |
| 7    | PAUSED             | Paused subscription             |

## Frequency Types

| Code | Name      | Description         |
| ---- | --------- | ------------------- |
| 1    | MONTHLY   | Monthly recurring   |
| 2    | YEARLY    | Yearly recurring    |
| 3    | WEEKLY    | Weekly recurring    |
| 4    | QUARTERLY | Quarterly recurring |

## ORM Models (SQLAlchemy)

### Import Models

```python
from src.database.models import (
    RecurringTransactions,
    RecurringTransactionDetails,
    RecurringTransactionPayments
)
```

### Create a New Recurring Transaction

```python
from datetime import datetime
from decimal import Decimal
from src.database.session import get_session

async with get_session() as session:
    new_transaction = RecurringTransactions(
        CompanyId=10001,
        DonorId=12345,
        StartDate=datetime.utcnow(),
        Frequency=1,  # Monthly
        FrequencyCount=1,
        EndDate=datetime(2027, 12, 31),
        ProviderName="Stripe",
        SubscriptionId="sub_1234567890",
        PaymentMethod="pm_card_visa",
        TotalAmount=Decimal("25.00"),
        Status=1,  # Active
        CreatedBy=1001,
        CreatedDate=datetime.utcnow()
    )
    session.add(new_transaction)
    await session.commit()
    await session.refresh(new_transaction)

    print(f"Created transaction ID: {new_transaction.TransactionId}")
```

### Query Recurring Transactions

```python
from sqlalchemy import select
from src.database.models import RecurringTransactions

async with get_session() as session:
    # Get all active subscriptions for a company
    stmt = select(RecurringTransactions).where(
        RecurringTransactions.CompanyId == 10001,
        RecurringTransactions.Status == 1  # Active
    )
    result = await session.execute(stmt)
    transactions = result.scalars().all()

    for tx in transactions:
        print(f"Transaction {tx.TransactionId}: {tx.SubscriptionId}")
```

### Update Transaction Status

```python
from sqlalchemy import select

async with get_session() as session:
    # Cancel a subscription
    stmt = select(RecurringTransactions).where(
        RecurringTransactions.SubscriptionId == "sub_1234567890"
    )
    result = await session.execute(stmt)
    transaction = result.scalar_one_or_none()

    if transaction:
        transaction.Status = 2  # Canceled
        transaction.EndDate = datetime.utcnow()
        transaction.ModifiedBy = 1001
        transaction.ModifiedDate = datetime.utcnow()
        await session.commit()
```

## Pydantic Schemas

### Import Schemas

```python
from src.models.recurring_transactions import (
    RecurringTransactionModel,
    RecurringTransactionCreateModel,
    RecurringTransactionUpdateModel,
    RecurringTransactionDetailModel,
    RecurringTransactionDetailsModel,
    RecurringTransactionStatusEnum,
    RecurringFrequencyEnum
)
```

### Create Request Example

```python
# Request body for creating a new recurring transaction
create_request = RecurringTransactionCreateModel(
    companyId=10001,
    donorId=12345,
    startDate=datetime.utcnow(),
    frequency=RecurringFrequencyEnum.MONTHLY,
    frequencyCount=1,
    providerName="Stripe",
    subscriptionId="sub_1234567890",
    paymentMethod="pm_card_visa",
    totalAmount=Decimal("25.00"),
    status=RecurringTransactionStatusEnum.ACTIVE,
    details=[
        RecurringTransactionDetailsCreateModel(
            donationType=101,
            amount=Decimal("25.00"),
            currency="USD"
        )
    ]
)
```

### Update Request Example

```python
# Request body for updating an existing transaction
update_request = RecurringTransactionUpdateModel(
    status=RecurringTransactionStatusEnum.CANCELED,
    endDate=datetime.utcnow()
)
```

### Response Example

```python
# Response structure for a single transaction
{
    "item": {
        "transactionId": 10001,
        "companyId": 10001,
        "donorId": 12345,
        "startDate": "2024-01-15T10:30:00Z",
        "frequency": 1,
        "frequencyCount": 1,
        "endDate": "2027-12-31T23:59:59Z",
        "providerName": "Stripe",
        "subscriptionId": "sub_1234567890",
        "paymentMethod": "pm_card_visa",
        "totalAmount": 25.00,
        "status": 1,
        "createdBy": 1001,
        "createdDate": "2024-01-15T10:30:00Z"
    },
    "status": "success"
}
```

## Common Use Cases

### 1. Sync Stripe Subscriptions

See the [Stripe Subscription Sync Guide](./STRIPE_SUBSCRIPTION_SYNC_GUIDE.md) for details on using the sync script.

```bash
python -m src.scripts.sync_stripe_subscriptions --company-id 10001 --dry-run
```

### 2. List Active Subscriptions for Dashboard

```python
from sqlalchemy import select, and_
from src.database.models import RecurringTransactions

async def get_active_subscriptions(company_id: int):
    """Get all active subscriptions for a company."""
    async with get_session() as session:
        stmt = select(RecurringTransactions).where(
            and_(
                RecurringTransactions.CompanyId == company_id,
                RecurringTransactions.Status == 1,  # Active
                RecurringTransactions.EndDate >= datetime.utcnow()
            )
        ).order_by(RecurringTransactions.StartDate.desc())

        result = await session.execute(stmt)
        return result.scalars().all()
```

### 3. Cancel Subscription When Stripe Webhook Received

```python
async def cancel_subscription(subscription_id: str, modified_by: int):
    """Cancel a subscription by Stripe subscription ID."""
    async with get_session() as session:
        stmt = select(RecurringTransactions).where(
            RecurringTransactions.SubscriptionId == subscription_id
        )
        result = await session.execute(stmt)
        transaction = result.scalar_one_or_none()

        if transaction:
            transaction.Status = 2  # Canceled
            transaction.EndDate = datetime.utcnow()
            transaction.ModifiedBy = modified_by
            transaction.ModifiedDate = datetime.utcnow()
            await session.commit()
            return True
        return False
```

### 4. Track Payment History

```python
from src.database.models import RecurringTransactionPayments

async def add_payment_record(transaction_id: int, donation_receipt_id: int):
    """Link a donation receipt to a recurring transaction."""
    async with get_session() as session:
        # Get the next line number
        stmt = select(RecurringTransactionPayments).where(
            RecurringTransactionPayments.TransactionId == transaction_id
        )
        result = await session.execute(stmt)
        payments = result.scalars().all()
        next_line_number = len(payments) + 1

        # Create payment record
        payment = RecurringTransactionPayments(
            TransactionId=transaction_id,
            LineNumber=next_line_number,
            DonationReceiptId=donation_receipt_id
        )
        session.add(payment)
        await session.commit()
```

### 5. Get Transaction with Details and Payments

```python
from sqlalchemy.orm import selectinload

async def get_transaction_with_details(transaction_id: int):
    """Get transaction header with all details and payment history."""
    async with get_session() as session:
        # Get main transaction
        stmt_tx = select(RecurringTransactions).where(
            RecurringTransactions.TransactionId == transaction_id
        )
        result_tx = await session.execute(stmt_tx)
        transaction = result_tx.scalar_one_or_none()

        if not transaction:
            return None

        # Get details
        stmt_details = select(RecurringTransactionDetails).where(
            RecurringTransactionDetails.TransactionId == transaction_id
        )
        result_details = await session.execute(stmt_details)
        details = result_details.scalars().all()

        # Get payments
        stmt_payments = select(RecurringTransactionPayments).where(
            RecurringTransactionPayments.TransactionId == transaction_id
        )
        result_payments = await session.execute(stmt_payments)
        payments = result_payments.scalars().all()

        return {
            "transaction": transaction,
            "details": details,
            "payments": payments
        }
```

## Database Relationships

```
RecurringTransactions (1) ----< (N) RecurringTransactionDetails
       |
       |
       +----< (N) RecurringTransactionPayments
```

- One RecurringTransaction can have multiple RecurringTransactionDetails (line items)
- One RecurringTransaction can have multiple RecurringTransactionPayments (payment history)

## Testing

### Unit Test Example

```python
import pytest
from datetime import datetime
from decimal import Decimal
from src.database.models import RecurringTransactions

def test_recurring_transaction_creation():
    """Test creating a RecurringTransaction instance."""
    transaction = RecurringTransactions(
        CompanyId=10001,
        StartDate=datetime.utcnow(),
        Frequency=1,
        FrequencyCount=1,
        EndDate=datetime(2027, 12, 31),
        ProviderName="Stripe",
        SubscriptionId="sub_test_123",
        TotalAmount=Decimal("25.00"),
        Status=1
    )

    assert transaction.CompanyId == 10001
    assert transaction.Frequency == 1
    assert transaction.SubscriptionId == "sub_test_123"
    assert transaction.Status == 1
```

## Related Documentation

- [Stripe Subscription Sync Guide](./STRIPE_SUBSCRIPTION_SYNC_GUIDE.md)
- [Database Schema](./DATABASE.md)
- [API Endpoints](./API.md)
- [Provider Manager](./PROVIDER_MANAGER_README.md)

## Notes

- The `TransactionId` field uses `IDENTITY(10001,1)`, starting at 10001
- The `EndDate` field is `NOT NULL` in the database but can be set to a far future date for ongoing subscriptions
- Use stored procedures for all create/update operations in production
- Always update `ModifiedBy` and `ModifiedDate` when making changes
- The `SubscriptionId` should be unique per provider to prevent duplicates
