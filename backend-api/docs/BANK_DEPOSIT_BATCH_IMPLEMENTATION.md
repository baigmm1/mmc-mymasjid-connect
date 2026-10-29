# Bank Deposit Batch Endpoints - Implementation Guide

## Overview

This implementation provides a complete API for managing bank deposit batches and their associated transactions. The system supports:

- Creating batches with multiple transactions atomically
- Retrieving batch details with all transactions
- Listing batches with filtering and pagination
- Updating batch information
- Deleting batches (cascades to transactions)
- Adding individual transactions (for webhook integration)

All endpoints require JWT authentication via Auth0.

## Files Created

### 1. Database Models

- **Location**: `src/database/models/bank_deposit_batch.py`
- **Model**: `BankDepositBatch` - Represents batch header records
- **Features**:
  - Decimals for money fields (18,2 precision)
  - Audit fields (CreatedBy, CreatedDate, ModifiedBy, ModifiedDate)
  - Status tracking and method type

- **Location**: `src/database/models/bank_deposit_batch_transactions.py`
- **Model**: `BankDepositBatchTransactions` - Represents transaction line items
- **Features**:
  - Foreign key to BankDepositBatch
  - Links to donation receipts
  - Individual transaction tracking

### 2. Pydantic Models (API Schemas)

- **Location**: `src/models/bank_deposit_batch.py`
- **Models**:
  - `BankDepositBatchTransactionModel` - Response model for transactions
  - `BankDepositBatchTransactionCreateModel` - Request model for creating transactions
  - `BankDepositBatchModel` - Response model for batch header
  - `BankDepositBatchDetailModel` - Response model combining batch + transactions
  - `BankDepositBatchCreateModel` - Request model for creating batch with transactions
  - `BankDepositBatchUpdateModel` - Request model for updating batch
  - `BankDepositBatchListResponse` - List response with count
  - `BankDepositBatchResponse` - Single item response
  - `BankDepositBatchDetailResponse` - Detailed response with transactions
  - `OperationResponse` - Generic response for create/update/delete operations

### 3. Utility Functions

- **Location**: `src/core/bank_deposit_batch_utils.py`
- **Functions**:
  - `create_bank_deposit_batch()` - Create batch with transactions (atomic)
  - `get_bank_deposit_batch()` - Get batch with all transactions
  - `get_bank_deposit_batches()` - List batches with filtering and pagination
  - `update_bank_deposit_batch()` - Update batch details
  - `delete_bank_deposit_batch()` - Delete batch and transactions
  - `add_batch_transaction()` - Add transaction to existing batch (for webhooks)
  - `get_batch_transactions()` - Get transactions for a batch

### 4. API Endpoints

- **Location**: `src/api/v1/endpoints/bank_deposit_batch.py`
- **Endpoints**:

  | Method | Path                                                     | Authentication | Purpose                   |
  | ------ | -------------------------------------------------------- | -------------- | ------------------------- |
  | GET    | `/api/v1/bank-deposit-batch`                             | Required       | List batches with filters |
  | GET    | `/api/v1/bank-deposit-batch/{batch_number}`              | Required       | Get batch details         |
  | GET    | `/api/v1/bank-deposit-batch/{batch_number}/transactions` | Required       | Get batch transactions    |
  | POST   | `/api/v1/bank-deposit-batch`                             | Required       | Create new batch          |
  | PUT    | `/api/v1/bank-deposit-batch/{batch_number}`              | Required       | Update batch              |
  | DELETE | `/api/v1/bank-deposit-batch/{batch_number}`              | Required       | Delete batch              |

### 5. Stored Procedure Stubs

- **Location**: `deployment/STORED_PROCEDURES_STUBS.sql`
- **Procedures** (stubs - implement these with your actual logic):
  - `sp_CreateBankDepositBatch`
  - `sp_GetBankDepositBatch`
  - `sp_GetBankDepositBatches`
  - `sp_UpdateBankDepositBatch`
  - `sp_DeleteBankDepositBatch`
  - `sp_AddBankDepositBatchTransaction`
  - `sp_GetBankDepositBatchTransactions`

## Setup Instructions

### Step 1: Create Database Tables

Execute the following SQL to create the database tables:

```sql
-- BankDepositBatch Table
CREATE TABLE [dbo].[BankDepositBatch] (
    [BatchNumber] INT PRIMARY KEY IDENTITY(1,1),
    [BatchDate] DATETIME NOT NULL,
    [BankDepositDate] DATETIME NULL,
    [BatchStatus] INT NOT NULL,
    [CreatedBy] VARCHAR(25) NOT NULL,
    [CreatedDate] DATETIME NOT NULL,
    [ModifiedBy] VARCHAR(25) NULL,
    [ModifiedDate] DATETIME NULL,
    [BatchMethodType] NVARCHAR(20) NOT NULL,
    [CompanyId] INT NOT NULL,
    [ProviderId] VARCHAR(50) NOT NULL,
    [Amount] MONEY NOT NULL
);

-- BankDepositBatchTransactions Table
CREATE TABLE [dbo].[BankDepositBatchTransactions] (
    [CompanyId] INT NOT NULL,
    [BatchNumber] INT NOT NULL,
    [LineNumber] INT NOT NULL,
    [DonationReceiptId] INT NOT NULL,
    [ProviderId] VARCHAR(50) NOT NULL,
    [TransactionType] VARCHAR(100) NOT NULL,
    [Amount] MONEY NOT NULL,
    [CreatedBy] INT NOT NULL,
    [CreatedDate] DATETIME NOT NULL,
    [ModifiedBy] INT NULL,
    [ModifiedDate] DATETIME NULL,
    PRIMARY KEY ([BatchNumber], [LineNumber]),
    FOREIGN KEY ([BatchNumber]) REFERENCES [dbo].[BankDepositBatch]([BatchNumber])
);
```

### Step 2: Implement Stored Procedures

Use the stub templates in `deployment/STORED_PROCEDURES_STUBS.sql` as a starting point. Implement each procedure with your actual business logic.

Key considerations:

- `sp_CreateBankDepositBatch` should handle atomic creation of batch + transactions
- All procedures should use proper transaction handling
- Parameters are passed by the utility functions in the expected format

### Step 3: Update Stored Procedure Names

If your procedure names differ from the defaults in the utility functions, update them in `src/core/bank_deposit_batch_utils.py`:

```python
# Update these lines with your actual procedure names:
procedure_name="[dbo].[sp_CreateBankDepositBatch]",  # Change this
procedure_name="[dbo].[sp_GetBankDepositBatch]",     # Change this
# ... etc
```

### Step 4: Application is Ready

The endpoints are already registered in `src/main.py` and will be available once the application starts.

## API Usage Examples

### 1. Create a Bank Deposit Batch

```bash
curl -X POST "http://localhost:8000/api/v1/bank-deposit-batch" \
  -H "Authorization: Bearer {jwt_token}" \
  -H "Content-Type: application/json" \
  -d '{
    "batchDate": "2024-02-14T10:00:00",
    "batchMethodType": "ACH",
    "companyId": 1,
    "providerId": "stripe_12345",
    "amount": 5000.00,
    "transactions": [
      {
        "donationReceiptId": 101,
        "providerId": "stripe_12345",
        "transactionType": "donation",
        "amount": 2500.00
      },
      {
        "donationReceiptId": 102,
        "providerId": "stripe_12345",
        "transactionType": "donation",
        "amount": 2500.00
      }
    ]
  }'
```

**Response:**

```json
{
  "success": true,
  "message": "Bank deposit batch created successfully",
  "batchNumber": 1
}
```

### 2. Get Batch Details with Transactions

```bash
curl -X GET "http://localhost:8000/api/v1/bank-deposit-batch/1" \
  -H "Authorization: Bearer {jwt_token}"
```

**Response:**

```json
{
  "item": {
    "batch": {
      "batchNumber": 1,
      "batchDate": "2024-02-14T10:00:00",
      "batchStatus": 1,
      "batchMethodType": "ACH",
      "companyId": 1,
      "providerId": "stripe_12345",
      "amount": 5000.0,
      "createdBy": "user@example.com",
      "createdDate": "2024-02-14T10:05:00"
    },
    "transactions": [
      {
        "lineNumber": 1,
        "donationReceiptId": 101,
        "amount": 2500.0,
        "transactionType": "donation"
      },
      {
        "lineNumber": 2,
        "donationReceiptId": 102,
        "amount": 2500.0,
        "transactionType": "donation"
      }
    ]
  },
  "status": "success"
}
```

### 3. List Batches with Filtering

```bash
curl -X GET "http://localhost:8000/api/v1/bank-deposit-batch?company_id=1&batch_status=1&limit=10&offset=0" \
  -H "Authorization: Bearer {jwt_token}"
```

### 4. Update Batch

```bash
curl -X PUT "http://localhost:8000/api/v1/bank-deposit-batch/1" \
  -H "Authorization: Bearer {jwt_token}" \
  -H "Content-Type: application/json" \
  -d '{
    "batchStatus": 2,
    "bankDepositDate": "2024-02-15T09:00:00"
  }'
```

### 5. Delete Batch

```bash
curl -X DELETE "http://localhost:8000/api/v1/bank-deposit-batch/1" \
  -H "Authorization: Bearer {jwt_token}"
```

## Integration with Stripe Webhooks

The utility function `add_batch_transaction()` is designed for webhook integration:

```python
from src.core.bank_deposit_batch_utils import add_batch_transaction
from src.database import get_session

async def handle_stripe_webhook(event_data):
    """Handle Stripe payment webhook and add transaction to batch"""

    async with get_session() as session:
        success = await add_batch_transaction(
            session=session,
            batch_number=existing_batch_number,
            company_id=company_id,
            donation_receipt_id=receipt_id,
            provider_id="stripe",
            transaction_type="invoice.paid",
            amount=Decimal(event_data["amount"]) / 100,  # Convert cents to dollars
            created_by=webhook_user_id
        )

        if success:
            await session.commit()
        else:
            await session.rollback()
            raise Exception("Failed to add transaction to batch")
```

## Database Relationships

```
BankDepositBatch (1) ─── (n) BankDepositBatchTransactions
     |
     ├─ BatchNumber (PK)
     ├─ CompanyId (FK to Company)
     ├─ Amount
     └─ BatchStatus

BankDepositBatchTransactions
     |
     ├─ BatchNumber (FK to BankDepositBatch)
     ├─ LineNumber
     ├─ DonationReceiptId (FK to donations)
     └─ Amount
```

## Important Notes

1. **Atomic Operations**: Batch creation with transactions is atomic - either all succeed or all rollback
2. **Authentication**: All endpoints require valid JWT token in Authorization header
3. **User Tracking**: CreatedBy/ModifiedBy fields are automatically set from authenticated user
4. **Pagination**: List endpoints support limit/offset for pagination
5. **Filtering**: List endpoint supports company_id, batch_status, and date range filters
6. **Error Handling**: Comprehensive error responses with HTTP status codes

## Stored Procedure Parameter Notes

### sp_CreateBankDepositBatch Parameters

- `@Transactions`: Passed as JSON string of transaction objects
- Returns: BatchNumber from the new batch

### sp_GetBankDepositBatch / sp_GetBankDepositBatches

- Expected to return rows with matched field names (case-insensitive)
- TotalCount field used for cursor paging

### sp_UpdateBankDepositBatch

- Only non-NULL parameters are used for update
- ModifiedDate is set automatically in stored procedure

### sp_DeleteBankDepositBatch

- Must handle cascade deletion of transactions atomically
- No dependent records should remain after deletion

## Troubleshooting

### Stored Procedure Not Found

- Verify procedure names in `bank_deposit_batch_utils.py` match your database
- Check procedure is in correct schema (`[dbo]`)

### Parameter Type Errors

- Stored procedures receive parameters as strings/numbers
- Dates are sent in ISO 8601 format
- Decimals are sent as float values

### Transaction Rollback

- Check database transaction logs for details
- Verify foreign key constraints if adding transactions to batch

## Future Enhancements

Consider these additions:

- Batch validation/reconciliation endpoints
- Transaction approval workflow
- Reconciliation with bank feed data
- Reporting endpoints (summary by date range, provider, etc.)
- Batch status state machine enforcement
- Webhook event logging and retry logic
