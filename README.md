# KYC/AML Compliance Service (Module E)

## Overview
Handles Know Your Customer (KYC) and Anti-Money Laundering (AML) verification and monitoring.

## Features
- Document verification
- AML risk assessment
- User verification status tracking
- Compliance monitoring
- Reverse cascade updates to Auth Service

## Dependencies
- **Direct**: Auth Service (A), Payment Service (C)
- **Reverse Cascade**: Updates Auth Service kyc_status field

## Cascade Impact - REVERSE CASCADE

This service is UNIQUE in that it:
1. Depends on Auth Service (A) for user validation
2. Depends on Payment Service (C) for transaction monitoring
3. **UPDATES Auth Service** with KYC verification status

When user completes KYC:
```
User submits documents to KYC Service (E)
    ↓
KYC Service verifies documents
    ↓
KYC Service UPDATES Auth Service kyc_status → "verified"
    ↓
Wallet Service sees kyc_status = "verified" → allows wallet creation
    ↓
Payment Service sees kyc_status = "verified" → allows payments
```

## Tech Stack
- Python 3.11+
- FastAPI
- httpx (service communication)

## Installation

```bash
pip install -r requirements.txt
```

## Configuration
Update `.env`:
- AUTH_SERVICE_URL
- PAYMENT_SERVICE_URL

## Running the Service

### Option 1: Direct Python
```bash
python main.py
```

### Option 2: Docker Compose
```bash
docker-compose up -d
```

Runs on port 8005.

## API Endpoints

### KYC Operations
- `POST /api/kyc/submit` - Submit KYC documents
- `GET /api/kyc/status/{user_id}` - Get KYC status
- `POST /api/kyc/reject` - Reject KYC submission

### AML Operations
- `GET /api/aml/check/{user_id}` - Check AML status

### Health Check
- `GET /health` - Service health + dependency status

## Database Schema

### kyc_documents (in-memory for demo)
- user_id (FK to Auth Service)
- document_type
- document_url
- status (submitted/verified/rejected)
- submitted_at

## Critical Cascade: Reverse Update

When KYC is verified:
```python
# KYC Service calls Auth Service
PUT /api/auth/user/{user_id}
{
  "kyc_status": "verified"
}
```

This triggers:
1. **Wallet Service** (B) - Now allows wallet creation
2. **Payment Service** (C) - Now allows payments
3. **Reporting Service** (F) - Updates compliance reports

## Testing

```bash
# Submit KYC documents
curl -X POST http://localhost:8005/api/kyc/submit \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": 1,
    "document_type": "passport",
    "document_url": "https://example.com/passport.pdf"
  }'

# Check KYC status
curl -X GET http://localhost:8005/api/kyc/status/1 \
  -H "Authorization: Bearer <token>"
```

## Monitoring
- Health endpoint shows Auth and Payment service status
- Track KYC submission and verification rates
- Monitor AML check performance
- Alert on Auth Service unavailability (reverse cascade impact)

## Key Characteristics

### Unique Reverse Cascade
Unlike other services that consume upstream data, this service:
- Takes user input (documents)
- Verifies independently
- **Updates upstream Auth Service**
- Triggers downstream cascades (Wallet, Payment)

### Dependency Chain After Verification
```
KYC Service → Auth Service (reverse cascade)
                    ↓
            Wallet Service (validates KYC)
                    ↓
            Payment Service (checks KYC)
                    ↓
            Reporting Service (includes KYC data)
```

This demonstrates how a service can be both a consumer and producer of cascading changes!
