# Plaid Integration Guide

Complete guide for Plaid bank account integration in the Wumbo application.

## Overview

The Plaid integration enables users to:
- Connect bank accounts securely via Plaid Link
- Automatically sync transactions daily
- Receive real-time updates via webhooks
- Manage multiple bank accounts and credit cards

## Architecture

```
┌─────────────┐
│  Frontend   │
│  (Web/Mobile)│
└──────┬──────┘
       │ 1. Request Link Token
       ▼
┌─────────────┐
│  Backend    │◄──────── 4. Webhook Events
│   FastAPI   │
└──────┬──────┘
       │ 2. Create Link Token
       │ 3. Exchange Public Token
       │ 5. Sync Transactions
       ▼
┌─────────────┐
│    Plaid    │
│     API     │
└─────────────┘
```

## Setup

### 1. Get Plaid Credentials

1. Sign up at [Plaid Dashboard](https://dashboard.plaid.com/)
2. Get your `client_id` and `secret` (sandbox or development)
3. Add to `.env` file:

```bash
PLAID_CLIENT_ID=your_client_id
PLAID_SECRET=your_secret_key
PLAID_ENVIRONMENT=sandbox  # sandbox, development, or production
```

### 2. Database Models

Three new models support Plaid integration:

**BankAccount** - Connected bank accounts
- Stores Plaid access token (encrypted in production)
- Tracks sync status and cursor
- Links to household and user

**Transaction** - Bank transactions
- Synced from Plaid
- Supports manual transactions
- Categorization and notes

**Category** - Transaction categories
- System and user-defined
- Hierarchical structure
- Income/expense types

## Integration Flow

### Step 1: Create Link Token

**Endpoint:** `POST /api/v1/plaid/link/token`

**Request:**
```json
{
  "products": ["transactions"],
  "webhook": "https://your-api.com/api/v1/plaid/webhook"
}
```

**Response:**
```json
{
  "link_token": "link-sandbox-abc123...",
  "expiration": "2025-12-23T12:00:00Z"
}
```

**Frontend Usage:**
```javascript
// Web (React)
import { usePlaidLink } from 'react-plaid-link';

const { open, ready } = usePlaidLink({
  token: linkToken,
  onSuccess: (public_token, metadata) => {
    // Send public_token to backend
    exchangeToken(public_token);
  },
});

// Mobile (React Native)
import { PlaidLink } from 'react-native-plaid-link-sdk';

<PlaidLink
  tokenConfig={{ token: linkToken }}
  onSuccess={({ publicToken }) => {
    exchangeToken(publicToken);
  }}
/>
```

### Step 2: Exchange Public Token

After user completes Plaid Link flow, exchange the public token for an access token.

**Endpoint:** `POST /api/v1/plaid/link/exchange`

**Request:**
```json
{
  "public_token": "public-sandbox-abc123...",
  "household_id": "uuid-of-household"
}
```

**Response:**
```json
{
  "accounts_added": 2,
  "item_id": "item-sandbox-xyz789"
}
```

**What Happens:**
1. Backend exchanges public token with Plaid
2. Retrieves connected accounts
3. Saves accounts to database
4. Queues initial transaction sync (background task)

### Step 3: Sync Transactions

Transactions are synced automatically via:
- **Daily Schedule**: 2 AM via Celery Beat
- **Webhooks**: Real-time when new transactions available
- **Manual Trigger**: User-initiated sync

**Manual Sync Endpoint:** `POST /api/v1/plaid/accounts/{account_id}/sync`

**Response:**
```json
{
  "transactions_added": 15,
  "transactions_modified": 2,
  "transactions_removed": 0,
  "last_synced_at": "2025-12-23T14:30:00Z"
}
```

### Step 4: List Bank Accounts

**Endpoint:** `GET /api/v1/plaid/accounts?household_id={uuid}`

**Response:**
```json
[
  {
    "id": "uuid",
    "household_id": "uuid",
    "name": "Chase Checking",
    "mask": "1234",
    "account_type": "depository",
    "account_subtype": "checking",
    "current_balance": 5250.00,
    "available_balance": 5150.00,
    "currency_code": "USD",
    "include_in_budget": true,
    "is_active": true,
    "last_synced_at": "2025-12-23T14:30:00Z"
  }
]
```

## Webhook Handling

Plaid sends webhooks for various events. The backend handles them automatically.

**Webhook Endpoint:** `POST /api/v1/plaid/webhook`

**Supported Events:**

### TRANSACTIONS Webhooks

```json
{
  "webhook_type": "TRANSACTIONS",
  "webhook_code": "DEFAULT_UPDATE",
  "item_id": "item-sandbox-xyz789"
}
```

**Actions:**
- `DEFAULT_UPDATE`: Queue transaction sync for all accounts
- `INITIAL_UPDATE`: Initial historical transactions available
- `HISTORICAL_UPDATE`: Historical update complete

### ITEM Webhooks

```json
{
  "webhook_type": "ITEM",
  "webhook_code": "ERROR",
  "item_id": "item-sandbox-xyz789",
  "error": {
    "error_code": "ITEM_LOGIN_REQUIRED"
  }
}
```

**Actions:**
- `ERROR`: Mark accounts as requiring re-authentication
- `PENDING_EXPIRATION`: Access token expiring soon

## Transaction Sync Logic

### Sync Process

1. **Get Account**: Retrieve BankAccount with access token and cursor
2. **Call Plaid Sync**: Use `/transactions/sync` endpoint with cursor
3. **Process Changes**:
   - **Added**: Create new Transaction records
   - **Modified**: Update existing transactions
   - **Removed**: Delete transactions
4. **Update Cursor**: Save next cursor for incremental sync
5. **Update Timestamp**: Set last_synced_at

### Cursor Management

Plaid uses cursors for incremental syncing:
- Initial sync: cursor = null (gets all historical)
- Subsequent syncs: Use saved cursor (only changes)
- Cursor stored in `bank_accounts.plaid_cursor`

### Transaction Deduplication

- Uses `plaid_transaction_id` (unique index)
- Prevents duplicate transactions
- Handles transaction updates

## Background Tasks (Celery)

### Daily Sync Task

**Task:** `app.tasks.plaid_tasks.sync_all_accounts`

**Schedule:** Daily at 2:00 AM

**Process:**
1. Get all active bank accounts
2. Queue individual sync task for each
3. Log results

### Individual Account Sync

**Task:** `app.tasks.plaid_tasks.sync_account_transactions`

**Triggered By:**
- Daily schedule
- Webhooks
- Manual user request

**Retries:** 3 attempts with 5-minute backoff

### Webhook Processing

**Task:** `app.tasks.plaid_tasks.handle_plaid_webhook`

**Process:**
- Parse webhook type and code
- Take appropriate action
- Queue syncs or mark errors

## Error Handling

### Common Errors

**ITEM_LOGIN_REQUIRED**
- User needs to re-authenticate
- Mark account `is_active = false`
- Set `sync_error` message
- Notify user

**RATE_LIMIT_EXCEEDED**
- Retry with exponential backoff
- Celery handles retries automatically

**INVALID_ACCESS_TOKEN**
- Access token revoked
- Mark account inactive
- Require re-connection

### Error Recovery

```python
try:
    result = PlaidService.sync_account_transactions(db, account_id)
except Exception as e:
    # Log error
    logger.error(f"Sync failed: {str(e)}")

    # Mark account
    account.sync_error = str(e)
    account.is_active = False
    db.commit()

    # Notify user
    send_notification(user, "Bank sync error", ...)
```

## Testing

### Sandbox Mode

Use Plaid Sandbox for development:

**Test Credentials:**
- Username: `user_good`
- Password: `pass_good`

**Test Scenarios:**
```bash
# Good account (normal flow)
username: user_good
password: pass_good

# Multi-factor auth
username: user_good
password: pass_good
# Then enter: 1234

# Account locked
username: user_locked
password: pass_good

# Connection error
username: user_custom
password: pass_good
```

### Testing Webhooks

**Local Testing:**
1. Use ngrok to expose local server:
   ```bash
   ngrok http 8000
   ```

2. Update webhook URL in Plaid Dashboard

3. Trigger webhook manually in sandbox:
   ```bash
   curl -X POST https://sandbox.plaid.com/sandbox/item/fire_webhook
   ```

### Manual Testing

```bash
# 1. Create link token
curl -X POST http://localhost:8000/api/v1/plaid/link/token \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"products": ["transactions"]}'

# 2. Use Plaid Link (web/mobile)
# 3. Exchange public token
curl -X POST http://localhost:8000/api/v1/plaid/link/exchange \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "public_token": "public-sandbox-...",
    "household_id": "uuid"
  }'

# 4. List accounts
curl http://localhost:8000/api/v1/plaid/accounts \
  -H "Authorization: Bearer $TOKEN"

# 5. Manual sync
curl -X POST http://localhost:8000/api/v1/plaid/accounts/{id}/sync \
  -H "Authorization: Bearer $TOKEN"
```

## Production Considerations

### Security

1. **Encrypt Access Tokens**
   ```python
   from cryptography.fernet import Fernet

   # Encrypt before saving
   encrypted_token = encrypt(access_token)
   account.plaid_access_token = encrypted_token

   # Decrypt before using
   access_token = decrypt(account.plaid_access_token)
   ```

2. **Webhook Verification**
   - Verify webhook signatures
   - Use HTTPS only
   - Validate item_id exists

3. **Rate Limiting**
   - Respect Plaid rate limits
   - Implement exponential backoff
   - Cache responses where possible

### Monitoring

Track these metrics:
- Sync success rate
- Average sync time
- Failed authentications
- Webhook processing time
- Transaction counts

### Scaling

- Use Redis for rate limiting
- Queue syncs during off-peak hours
- Batch process webhooks
- Monitor Plaid API costs

## API Reference

### Plaid Client Methods

```python
from app.integrations.plaid_client import plaid_client

# Create link token
plaid_client.create_link_token(user_id, products=["transactions"])

# Exchange token
plaid_client.exchange_public_token(public_token)

# Get accounts
plaid_client.get_accounts(access_token)

# Sync transactions
plaid_client.sync_transactions(access_token, cursor)

# Remove item
plaid_client.remove_item(access_token)
```

### Service Layer

```python
from app.services.plaid_service import PlaidService

# Create link token
PlaidService.create_link_token(db, user, webhook)

# Exchange and save
PlaidService.exchange_public_token_and_save_accounts(
    db, user, household_id, public_token
)

# Sync account
PlaidService.sync_account_transactions(db, account_id)

# Remove account
PlaidService.remove_account(db, account_id)
```

## Resources

- [Plaid Documentation](https://plaid.com/docs/)
- [Plaid Quickstart](https://github.com/plaid/quickstart)
- [Plaid API Reference](https://plaid.com/docs/api/)
- [React Plaid Link](https://github.com/plaid/react-plaid-link)
- [React Native Plaid Link](https://github.com/plaid/react-native-plaid-link-sdk)

## Troubleshooting

### Sync Not Working

1. Check Plaid credentials in `.env`
2. Verify account is active
3. Check celery worker logs
4. Test Plaid API connectivity

### Transactions Missing

1. Check sync cursor is updating
2. Verify webhook is configured
3. Look for sync errors in account
4. Check Plaid transaction history

### Webhook Not Received

1. Verify webhook URL is accessible
2. Check firewall/security groups
3. Test with ngrok locally
4. Validate webhook in Plaid Dashboard

## Status: ✅ Production Ready

The Plaid integration is fully implemented and tested with sandbox credentials. Ready for production with proper Plaid production credentials and access token encryption.
