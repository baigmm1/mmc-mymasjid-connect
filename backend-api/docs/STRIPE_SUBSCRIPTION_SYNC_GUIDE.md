# Stripe Subscription Sync Script Guide

## Overview

The `sync_stripe_subscriptions.py` script synchronizes Stripe subscriptions with the local `RecurringTransactions` database table. It retrieves active/canceled subscriptions from Stripe and creates or updates corresponding records in the database.

## Prerequisites

1. **Database Setup**: Ensure the following stored procedures exist:
   - `sp_GetRecurringTransactionsByCompany` - Get existing recurring transactions
   - `sp_CreateRecurringTransaction` - Create new recurring transaction
   - `sp_UpdateRecurringTransaction` - Update existing recurring transaction

2. **Stripe Configuration**:
   - Stripe API keys configured in environment variables
   - Company-specific Stripe account setup

3. **Database Tables**:
   - `RecurringTransactions` - Main transaction records
   - `RecurringTransactionDetails` - Line item details (optional)
   - `RecurringTransactionPayments` - Payment tracking (optional)

## Usage

### Basic Syntax

```bash
python -m src.scripts.sync_stripe_subscriptions --company-id <COMPANY_ID> [OPTIONS]
python -m src.scripts.sync_stripe_subscriptions --company-id 10001 --status active
```

### Required Arguments

- `--company-id <ID>`: The CompanyId to sync subscriptions for (e.g., 10001)

### Optional Arguments

- `--dry-run`: Preview changes without writing to database
- `--status <STATUS>`: Filter by subscription status
  - `active` - Only active subscriptions (default)
  - `canceled` - Only canceled subscriptions
  - `all` - All subscriptions

## Examples

### 1. Sync Active Subscriptions (Dry Run)

Preview what would be synced without making changes:

```bash
python -m src.scripts.sync_stripe_subscriptions --company-id 10001 --dry-run
```

**Output:**

```
Starting Stripe subscription sync for company 10001...
DRY RUN MODE - No changes will be made to the database
Retrieving Stripe subscriptions (status: active)...
Retrieving existing recurring transactions from database...

Processing subscriptions...
[DRY RUN] Would create new recurring transaction:
  Subscription ID: sub_1234567890
  Amount: $25.00
  Frequency: Monthly
  Status: Active (1)

[DRY RUN] Would update recurring transaction (ID: 42):
  Changes: Status changed from 1 to 2

Sync Summary:
Total Stripe subscriptions: 10
Existing records: 8
New records: 2
Updated records: 3
Skipped (no changes): 5
Errors: 0
```

### 2. Sync Active Subscriptions (Live)

Actually write changes to the database:

```bash
python -m src.scripts.sync_stripe_subscriptions --company-id 10001
```

### 3. Sync All Subscriptions (Active + Canceled)

```bash
python -m src.scripts.sync_stripe_subscriptions --company-id 10001 --status all
```

### 4. Sync Only Canceled Subscriptions

```bash
python -m src.scripts.sync_stripe_subscriptions --company-id 10001 --status canceled
```

## Status Mapping

The script maps Stripe subscription statuses to database integer codes:

| Stripe Status        | Database Code | Description           |
| -------------------- | ------------- | --------------------- |
| `active`             | 1             | Active subscription   |
| `canceled`           | 2             | Canceled subscription |
| `incomplete`         | 0             | Incomplete/pending    |
| `incomplete_expired` | 3             | Expired incomplete    |
| `trialing`           | 4             | Trial period          |
| `past_due`           | 5             | Payment overdue       |
| `unpaid`             | 6             | Unpaid                |
| `paused`             | 7             | Paused subscription   |

## Sync Logic

### Create New Record

A new `RecurringTransaction` record is created when:

- Subscription exists in Stripe but not in database (by `SubscriptionId`)

### Update Existing Record

An existing record is updated when changes are detected in:

- **Status**: Stripe status differs from database status
- **End Date**: Subscription canceled in Stripe (sets `EndDate` to cancellation date)
- **Total Amount**: Subscription amount changed
- **Payment Method**: Payment method updated

### Skip Record

A record is skipped when:

- No changes detected between Stripe and database
- Subscription already exists with matching data

## Implementation TODOs

Before using this script in production, complete these tasks:

### 1. Implement Stripe Subscription Retrieval

In `src/scripts/sync_stripe_subscriptions.py`, update the `get_stripe_subscriptions()` method:

```python
async def get_stripe_subscriptions(self, status: str = "active") -> List[Dict]:
    """
    Retrieve subscriptions from Stripe for the company.

    TODO: Implement your company-specific customer retrieval logic
    Options:
    1. Store Stripe customer IDs in company table
    2. Use metadata to tag customers by company
    3. Maintain mapping table (CompanyId -> Stripe CustomerId)
    """
    stripe_provider = await get_stripe_provider()
    subscriptions = []

    # EXAMPLE: If you have customer IDs stored in database
    customer_ids = await self._get_company_stripe_customers(self.company_id)

    for customer_id in customer_ids:
        customer_subs = await stripe_provider.client.subscriptions.list_async(
            customer=customer_id,
            status=status,
            limit=100
        )
        subscriptions.extend(customer_subs.data)

    return subscriptions
```

### 2. Implement Donor Lookup

Add donor lookup logic to map Stripe customer emails to database `DonorId`:

```python
async def _get_donor_id_by_email(self, email: str) -> Optional[int]:
    """Map Stripe customer email to database DonorId"""
    async with get_session() as session:
        result = await session.execute(
            text("SELECT DonorId FROM Donors WHERE Email = :email"),
            {"email": email}
        )
        row = result.first()
        return row[0] if row else None
```

Then in `sync_subscriptions()`, lookup the donor:

```python
# Get customer email from Stripe
customer = await stripe_provider.client.customers.retrieve_async(
    subscription.customer
)
donor_id = await self._get_donor_id_by_email(customer.email)
```

### 3. Create Stored Procedures

Execute the SQL file to create the required stored procedures:

```bash
sqlcmd -S your_server -d your_database -i deployment/RECURRING_TRANSACTION_STORED_PROCEDURES.sql
```

Or use Azure Data Studio / SQL Server Management Studio to run:

- `deployment/RECURRING_TRANSACTION_STORED_PROCEDURES.sql`

## Database Schema

### RecurringTransactions Table

```sql
CREATE TABLE RecurringTransactions (
    TransactionId INT IDENTITY(1,1) PRIMARY KEY,
    CompanyId INT NOT NULL,
    DonorId INT NULL,
    StartDate DATETIME NOT NULL,
    Frequency INT NOT NULL,
    FrequencyCount INT NOT NULL,
    EndDate DATETIME NULL,
    ProviderName NVARCHAR(50) NOT NULL,
    SubscriptionId NVARCHAR(100) NOT NULL,
    PaymentMethod NVARCHAR(100) NULL,
    TotalAmount MONEY NOT NULL,
    Status INT NOT NULL,
    CreatedBy INT NOT NULL,
    CreatedDate DATETIME NOT NULL,
    ModifiedBy INT NULL,
    ModifiedDate DATETIME NULL
)
```

### Field Descriptions

- **TransactionId**: Auto-incrementing primary key
- **CompanyId**: Company identifier
- **DonorId**: Reference to Donors table (nullable)
- **StartDate**: Subscription start date from Stripe
- **Frequency**: Recurring frequency type (1=Monthly, 2=Yearly, etc.)
- **FrequencyCount**: Number of frequency units (e.g., 1 for monthly, 12 for yearly)
- **EndDate**: Subscription end/cancellation date (NULL if active)
- **ProviderName**: Payment provider (e.g., 'Stripe')
- **SubscriptionId**: Stripe subscription ID (unique identifier)
- **PaymentMethod**: Stripe payment method ID or description
- **TotalAmount**: Subscription amount
- **Status**: Current status (see Status Mapping table above)

## Error Handling

The script includes comprehensive error handling:

### Database Connection Errors

- Automatically logs and reports connection failures
- Safe to retry after fixing database connectivity

### Stripe API Errors

- Handles rate limiting (429)
- Logs API errors with subscription context
- Continues processing remaining subscriptions

### Data Validation Errors

- Validates required fields before database operations
- Logs validation failures with details
- Skips invalid records but continues processing

## Logging

The script logs all operations to `backend-api/logs/sync_stripe_subscriptions.log`:

```
2024-01-15 10:30:00 - INFO - Starting sync for company 10001
2024-01-15 10:30:01 - INFO - Retrieved 15 subscriptions from Stripe
2024-01-15 10:30:02 - INFO - Found 12 existing records in database
2024-01-15 10:30:03 - INFO - Created new transaction (ID: 123) for subscription sub_abc123
2024-01-15 10:30:04 - INFO - Updated transaction (ID: 42): status changed to 2
2024-01-15 10:30:05 - ERROR - Failed to create transaction for sub_xyz789: [error details]
```

## Scheduling

### Windows Task Scheduler

Create a scheduled task to run daily:

```powershell
$action = New-ScheduledTaskAction -Execute 'python' -Argument '-m src.scripts.sync_stripe_subscriptions --company-id 10001'
$trigger = New-ScheduledTaskTrigger -Daily -At 2am
Register-ScheduledTask -TaskName "SyncStripeSubscriptions" -Action $action -Trigger $trigger
```

### Linux Cron

Add to crontab for daily execution:

```bash
# Run at 2 AM daily
0 2 * * * cd /path/to/backend-api && python -m src.scripts.sync_stripe_subscriptions --company-id 10001 >> /var/log/stripe_sync.log 2>&1
```

### Azure Functions (Timer Trigger)

For cloud deployment, create a Timer Trigger function:

```python
import azure.functions as func
import subprocess

def main(mytimer: func.TimerRequest) -> None:
    subprocess.run([
        "python", "-m", "src.scripts.sync_stripe_subscriptions",
        "--company-id", "10001"
    ])
```

## Testing

### 1. Test with Dry Run

Always test with `--dry-run` first:

```bash
python -m src.scripts.sync_stripe_subscriptions --company-id 10001 --dry-run
```

Review the output to ensure expected behavior.

### 2. Test with Single Subscription

Modify the script temporarily to process only 1 subscription:

```python
# In get_stripe_subscriptions()
return subscriptions[:1]  # Only first subscription
```

### 3. Verify Database Changes

After running without `--dry-run`, check the database:

```sql
-- View recently created/updated transactions
SELECT TOP 10 *
FROM RecurringTransactions
WHERE CompanyId = 10001
ORDER BY ModifiedDate DESC
```

## Troubleshooting

### "No subscriptions found in Stripe"

**Cause**: The `get_stripe_subscriptions()` method is not implemented or returns no data.

**Solution**: Implement customer lookup logic in `get_stripe_subscriptions()`.

### "Failed to execute stored procedure"

**Cause**: Stored procedures not created or have incorrect parameters.

**Solution**:

1. Verify stored procedures exist in database
2. Check parameter names and types match expectations
3. Review stored procedure error messages in logs

### "DonorId is NULL"

**Cause**: Donor lookup logic not implemented.

**Solution**: Implement `_get_donor_id_by_email()` or handle NULL donors appropriately.

### Duplicate SubscriptionId Errors

**Cause**: Attempting to create record when SubscriptionId already exists.

**Solution**:

1. Ensure `get_existing_recurring_transactions()` retrieves all records
2. Check for duplicate SubscriptionIds in Stripe
3. Verify update logic triggers correctly

## Best Practices

1. **Always test with --dry-run first** before making database changes
2. **Review logs** after each sync to identify issues
3. **Monitor sync frequency** - daily syncs are typically sufficient
4. **Handle errors gracefully** - script continues on individual errors
5. **Keep subscription data fresh** - schedule regular syncs
6. **Backup before first run** - take database backup before initial sync
7. **Test cancellation flow** - verify canceled subscriptions update correctly

## Support

For issues or questions:

1. Check logs in `backend-api/logs/sync_stripe_subscriptions.log`
2. Review stored procedure output for database errors
3. Verify Stripe API connectivity and credentials
4. Consult Stripe API documentation for subscription schema changes

## Related Documentation

- [Stripe Subscription API](https://stripe.com/docs/api/subscriptions)
- [Database Schema](./DATABASE.md)
- [Stored Procedures](../deployment/RECURRING_TRANSACTION_STORED_PROCEDURES.sql)
- [Provider Manager](./PROVIDER_MANAGER_README.md)
