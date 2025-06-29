# Bulk Transfer API

A FastAPI-based service for processing bulk credit transfers with asynchronous processing, designed for Qonto's banking platform.

## Overview

This API enables customers to submit multiple credit transfers in a single request, addressing the pain point of processing hundreds of individual transfers (e.g., monthly salary payments). 
The system validates requests synchronously and processes transfers asynchronously.

## Architecture

### Applicative stack

1. FastAPI framework
2. SQLite database
3. In-memory queue using Python `deque` for async processing to simulate a message broker (suitable for MVP, production would use Kafka/RabbitMQ for instance)

### Processing Flow

```
1. POST /transfers/bulk: Synchronous validation
2. Store bulk request in database and eserve account funds
3. Queue individual transfers for sync processing
4. Process each transfer and each one queues a job to update bulk request progress
5. Complete bulk request status and update account balance on last successful transfer job or first failing transfer job and update final status
6. (Not implemented) Send a webhook status to a callbak url when the bulk request is completed (failure or success).
7. (Not implemented) When a bulk request final job can not be processed, queue a reconciliation job to revert the inserted transactions for this bulk request.
```

### Database Schema

- bank_accounts: account information with balance and ongoing operations tracking
- bulk_requests: bulk operation metadata and status
- transactions: individual transfer records with bulk linkage
- (Not implemented): audit log table

## Current implementation status

### Implemented features

- Bulk Transfer API: `POST /transfers/bulk` with comprehensive validation and asynchronous transfers processing.
- Idempotency: duplicate request prevention using UUIDs
- Domain rules: qmount format, account existence, balance checking  
- Account management: balance reservation and atomic updates
- Error handling: proper HTTP status codes and comprehensive error messages
- Testing: comprehensive test suite with pytest and mocking
- Database migrations: simple migration system ensuring to run all migrations on server startup

### Missing features (not exhaustive list)

- Webhooks: No webhook delivery system for completion notifications
- Bulk request status endpoint: No `GET /transfers/bulk/{bulk_id}/status` polling endpoint (to be returned in the API response)
- Input data validation: only basic length checks for BIC/IBAN, no format validation, no call to an external validator service

### Production readiness

There are several missing requirements to be implemented for production:
- Authentication: No JWT or API key authentication implemented
- Retry logic: no retry with exponential backoff for failed transfers for instance (to be implemented on top of a production compatible message broker)
- Monitoring (e.g. Prometheus)
- Alerting (e.g. Prometheus)
- Observability (eg. Sentry)
- Required more structured logging for production (JSON based for production tools like Grafana, distributed log files with a universal correlator ID, etc.)
- Rate limiting: no organization-level rate limiting for instance
- Production config: no environment variable management
  
## Installation & Setup

### Prerequisites

- Python 3.12+
- pip

### Installation (Linux)

```bash
# Clone the repository
git clone <repository-url>
cd bulk-transfer-api

# Create virtual environment
python -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### Database Setup

The application automatically runs migrations on startup. The SQLite database will be created at `qonto_accounts.sqlite`.

## Running the Application

### Start the API Server

```bash
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

The API documentation will be available at:
- OpenAPI Docs: http://127.0.0.1:8000/docs
- ReDoc: http://127.0.0.1:8000/redoc
- Openapi spec: http://127.0.0.1:8000/openapi.json

> NB: you can send requests from the documentation page.

### Running Tests

```bash
source venv/bin/activate
 
# Run all tests
pytest

# Run specific test file
pytest tests/test_bulk_transfers.py
```

## API Usage

### Create Bulk Transfer

```bash
curl -X POST "http://127.0.0.1:8000/transfers/bulk" \
  -H "Content-Type: application/json" \
  -d '{
    "request_id": "123e4567-e89b-12d3-a456-426614174000",
    "organization_bic": "OIVUSCLQXXX",
    "organization_iban": "FR10474608000002006107XXXXX",
    "credit_transfers": [
      {
        "amount": "100.00",
        "currency": "EUR",
        "counterparty_name": "John Doe",
        "counterparty_bic": "DEUTDEFFXXX",
        "counterparty_iban": "DE89370400440532013000",
        "description": "Salary payment for June 2024"
      }
    ]
      }'
  ```

### Process queued transfers operations (internal endpoints)

Using Postman, or curl:

```bash
# Process a single transfer from queue
curl -X GET "http://127.0.0.1:8000/internal/jobs/transfer"

# Process bulk completion from queue  
curl -X GET "http://127.0.0.1:8000/internal/jobs/bulk"
```

## Testing Strategy

CI pipeline using GitHub Actions. 

### Test Coverage

- Request validation scenarios
- Business logic edge cases
- Error handling paths
- Amount conversion utilities

## Known issues & limitations

### Security Issues

1. No authentication: API is completely open - critical for production
2. No authorization: no access control
3. No rate limiting: vulnerable to abuse
4. HTTPS enforcement

### Functional Limitations

1. No message broker (in-memory queue): transfers must be manually processed via internal endpoints
2. No webhooks: no automatic completion notifications
3. Basic validation: IBAN/BIC validation is minimal

### Technical Debt

1. No message broker (in-memory queue): not suitable for production (easily changed in the code).
2. SQLite database: not suitable for concurrent production load
3. No retry logic: failed transfers aren't automatically retried (but are already idempotent)
4. Logging: basic logging, needs structured logging for production

### Infrastructure requirements

- Database: PostgreSQL or MySQL
- Message queue: Kafka or RabbitMQ for reliable job processing (FIFO
- Load balancer: for horizontal scaling
- Monitoring & observability: application and infrastructure monitoring


