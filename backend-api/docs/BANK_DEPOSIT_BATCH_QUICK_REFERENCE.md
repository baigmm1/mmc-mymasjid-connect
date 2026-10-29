# Bank Deposit Batch - Quick Reference Guide

## File Structure

```
backend-api/
├── src/
│   ├── api/v1/endpoints/
│   │   └── bank_deposit_batch.py          # API endpoints (6 endpoints)
│   ├── core/
│   │   └── bank_deposit_batch_utils.py    # Utility functions (7 functions)
│   ├── database/
│   │   └── models/
│   │       ├── bank_deposit_batch.py      # BankDepositBatch model
│   │       └── bank_deposit_batch_transactions.py  # Transactions model
│   ├── models/
│   │   └── bank_deposit_batch.py          # Pydantic schemas (10 models)
│   └── main.py                            # Updated to register endpoints
├── deployment/
│   └── STORED_PROCEDURES_STUBS.sql        # SQL procedure templates (7 stubs)
└── docs/
    └── BANK_DEPOSIT_BATCH_IMPLEMENTATION.md  # Full implementation guide
```

## Key Features Implemented

✅ **Authentication**: All endpoints require JWT via Auth0  
✅ **Atomic Operations**: Batch + transactions created together  
✅ **Stored Procedures**: All database ops use stored procs (stubs provided)  
✅ **Utility Functions**: Reusable functions for webhooks/processors  
✅ **Error Handling**: Comprehensive error responses  
✅ **Pagination**: List endpoint supports offset/limit  
✅ **Filtering**: Filter by company, status, date range  
✅ **Audit Fields**: CreatedBy/ModifiedBy tracking  
✅ **Documentation**: Full API docs in docstrings

## API Endpoints

### 1. List Batches

```
GET /api/v1/bank-deposit-batch
Query Parameters:
  - company_id (optional): Filter by company
  - batch_status (optional): Filter by status
  - from_date (optional): ISO 8601 start date
  - to_date (optional): ISO 8601 end date
  - limit (default 100, max 500)
  - offset (default 0)
Authorization: Required
```

### 2. Get Batch with Transactions

```
GET /api/v1/bank-deposit-batch/{batch_number}
Path Parameters:
  - batch_number: The batch number
Authorization: Required
Returns: Batch header + all transactions
```

### 3. Get Batch Transactions Only

```
GET /api/v1/bank-deposit-batch/{batch_number}/transactions
Path Parameters:
  - batch_number: The batch number
Authorization: Required
Returns: List of transactions only
```

### 4. Create Batch with Transactions

```
POST /api/v1/bank-deposit-batch
Body:
{
  "batchDate": "2024-02-14T10:00:00",
  "bankDepositDate": "2024-02-15T09:00:00" (optional),
  "batchStatus": 1 (default),
  "batchMethodType": "ACH|Check|Wire|...",
  "companyId": 123,
  "providerId": "stripe_xxx",
  "amount": 5000.00,
  "transactions": [
    {
      "donationReceiptId": 101,
      "providerId": "stripe_xxx",
      "transactionType": "donation",
      "amount": 2500.00
    }
  ]
}
Authorization: Required
Returns: {success: true, batchNumber: X}
```

### 5. Update Batch

```
PUT /api/v1/bank-deposit-batch/{batch_number}
Body (all fields optional):
{
  "batchDate": "2024-02-14T10:00:00",
  "bankDepositDate": "2024-02-15T09:00:00",
  "batchStatus": 2,
  "batchMethodType": "Check",
  "amount": 5500.00
}
Authorization: Required
Returns: {success: true, batchNumber: X}
```

### 6. Delete Batch

```
DELETE /api/v1/bank-deposit-batch/{batch_number}
Authorization: Required
Returns: {success: true, batchNumber: X}
```

## Utility Functions

### Import Location

```python
from src.core.bank_deposit_batch_utils import (
    create_bank_deposit_batch,
    get_bank_deposit_batch,
    get_bank_deposit_batches,
    update_bank_deposit_batch,
    delete_bank_deposit_batch,
    add_batch_transaction,
    get_batch_transactions,
)
```

### For Stripe Webhooks

```python
# Add transaction from webhook handler
from src.core.bank_deposit_batch_utils import add_batch_transaction
from decimal import Decimal

async def handle_stripe_webhook(session, batch_data):
    success = await add_batch_transaction(
        session=session,
        batch_number=123,              # existing batch
        company_id=1,
        donation_receipt_id=456,
        provider_id="stripe",
        transaction_type="invoice.paid",
        amount=Decimal("100.00"),
        created_by=789               # user ID
    )
    return success
```

## Database Setup Checklist

- [ ] Create BankDepositBatch table
- [ ] Create BankDepositBatchTransactions table
- [ ] Create foreign key constraint
- [ ] Implement `sp_CreateBankDepositBatch`
- [ ] Implement `sp_GetBankDepositBatch`
- [ ] Implement `sp_GetBankDepositBatches`
- [ ] Implement `sp_UpdateBankDepositBatch`
- [ ] Implement `sp_DeleteBankDepositBatch`
- [ ] Implement `sp_AddBankDepositBatchTransaction`
- [ ] Implement `sp_GetBankDepositBatchTransactions`
- [ ] Update procedure names in `bank_deposit_batch_utils.py` if different
- [ ] Test procedures with sample data

## Testing the Endpoints

### Using cURL

```bash
# Create batch
curl -X POST "http://localhost:8000/api/v1/bank-deposit-batch" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "batchDate": "2024-02-14T10:00:00",
    "batchMethodType": "ACH",
    "companyId": 1,
    "providerId": "stripe",
    "amount": 1000,
    "transactions": [
      {
        "donationReceiptId": 1,
        "providerId": "stripe",
        "transactionType": "donation",
        "amount": 1000
      }
    ]
  }'

# Get batch
curl -X GET "http://localhost:8000/api/v1/bank-deposit-batch/1" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"

# List batches
curl -X GET "http://localhost:8000/api/v1/bank-deposit-batch?company_id=1&limit=10" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"

# Update batch
curl -X PUT "http://localhost:8000/api/v1/bank-deposit-batch/1" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"batchStatus": 2}'

# Delete batch
curl -X DELETE "http://localhost:8000/api/v1/bank-deposit-batch/1" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

### Using Python Requests

```python
import requests
from datetime import datetime

BASE_URL = "http://localhost:8000/api/v1"
TOKEN = "your_jwt_token"
HEADERS = {"Authorization": f"Bearer {TOKEN}"}

# Create batch
batch_data = {
    "batchDate": datetime.now().isoformat(),
    "batchMethodType": "ACH",
    "companyId": 1,
    "providerId": "stripe",
    "amount": 1000.00,
    "transactions": [
        {
            "donationReceiptId": 1,
            "providerId": "stripe",
            "transactionType": "donation",
            "amount": 1000.00
        }
    ]
}

response = requests.post(
    f"{BASE_URL}/bank-deposit-batch",
    json=batch_data,
    headers=HEADERS
)
print(response.json())  # {success: true, batchNumber: X}

# Get batch
batch_num = response.json()["batchNumber"]
response = requests.get(
    f"{BASE_URL}/bank-deposit-batch/{batch_num}",
    headers=HEADERS
)
print(response.json())
```

## Stored Procedure Names to Update

These are the default names used in the utility functions. Update if your names are different:

1. `[dbo].[sp_CreateBankDepositBatch]`
2. `[dbo].[sp_GetBankDepositBatch]`
3. `[dbo].[sp_GetBankDepositBatches]`
4. `[dbo].[sp_UpdateBankDepositBatch]`
5. `[dbo].[sp_DeleteBankDepositBatch]`
6. `[dbo].[sp_AddBankDepositBatchTransaction]`
7. `[dbo].[sp_GetBankDepositBatchTransactions]`

**Update Location**: `src/core/bank_deposit_batch_utils.py` (search for `procedure_name=`)

## Error Responses

All errors follow the standard format:

```json
{
  "detail": "Error message",
  "error_code": "ERROR_CODE",
  "timestamp": "2024-02-14T10:00:00",
  "correlation_id": "correlation-id-123",
  "errors": []
}
```

### Common Status Codes

- `200`: Success (GET, PUT, DELETE)
- `201`: Created (POST)
- `400`: Bad request (validation error)
- `401`: Unauthorized (missing/invalid token)
- `404`: Not found (batch not found)
- `500`: Server error (database error)

## Next Steps

1. ✅ Files created - ready to extend
2. ⏳ Create database tables
3. ⏳ Implement 7 stored procedures
4. ⏳ Update procedure names if needed
5. ⏳ Test endpoints with JWT token
6. ⏳ Integrate with Stripe webhooks (use `add_batch_transaction()`)

## Architecture

```
┌─────────────────────────────────────────┐
│          FastAPI Endpoints             │
│   (bank_deposit_batch.py)               │
└────────────┬────────────────────────────┘
             │
             ├─── Authentication (JWT)
             │
             ▼
┌─────────────────────────────────────────┐
│     Utility Functions                   │
│   (bank_deposit_batch_utils.py)         │
└────────────┬────────────────────────────┘
             │
             ├─── Database Session
             │
             ▼
┌─────────────────────────────────────────┐
│    Stored Procedures                    │
│   (SQL Server database)                 │
└────────────┬────────────────────────────┘
             │
             ├─── Returns dict/list of rows
             │
             ▼
┌─────────────────────────────────────────┐
│    Pydantic Models                      │
│   (Validation & Response)               │
└─────────────────────────────────────────┘
```

## Support & Troubleshooting

### Issue: 401 Unauthorized

- Verify JWT token is valid
- Check Authorization header format: `Bearer {token}`
- Verify Auth0 configuration in settings

### Issue: Stored procedure not found

- Check procedure names match in database
- Verify schema is `[dbo]`
- Check procedure exists: `SELECT * FROM INFORMATION_SCHEMA.ROUTINES WHERE ROUTINE_NAME LIKE '%sp_Create%'`

### Issue: Foreign key constraint

- Ensure BankDepositBatch table has primary key on BatchNumber
- Ensure BankDepositBatchTransactions has FK to BankDepositBatch

### Issue: Parameter type errors

- Check stored procedure parameter types match expected formats
- Dates should accept ISO 8601 strings
- Decimals should be numeric values

## References

- Full docs: `docs/BANK_DEPOSIT_BATCH_IMPLEMENTATION.md`
- Stored proc stubs: `deployment/STORED_PROCEDURES_STUBS.sql`
- API endpoint code: `src/api/v1/endpoints/bank_deposit_batch.py`
- Utility functions: `src/core/bank_deposit_batch_utils.py`
- Models: `src/database/models/bank_deposit_batch*.py` and `src/models/bank_deposit_batch.py`
