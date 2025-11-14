# SparzaFI API Documentation

## Overview

The SparzaFI API provides RESTful endpoints for fintech operations, marketplace functionality, and mobile app integration. All API endpoints are prefixed with `/api`.

## Base URL

```
http://localhost:5000/api  (Development)
https://your-domain.com/api (Production)
```

---

## Authentication

### JWT Token Authentication

Most API endpoints require authentication via JWT (JSON Web Token). Include the token in the Authorization header:

```
Authorization: Bearer YOUR_JWT_TOKEN
```

### Login

**POST** `/api/auth/login`

Authenticate user and receive JWT token.

**Request Body:**
```json
{
  "email": "user@example.com",
  "password": "yourpassword"
}
```

**Response (200 OK):**
```json
{
  "success": true,
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "user": {
    "id": 1,
    "email": "user@example.com",
    "user_type": "buyer",
    "kyc_completed": true,
    "is_verified": true
  }
}
```

**Error Responses:**
- `400` - Missing email or password
- `401` - Invalid credentials

---

### Verify Token

**GET** `/api/auth/verify`

Verify if current JWT token is valid.

**Headers:** Authorization required

**Response (200 OK):**
```json
{
  "success": true,
  "user_id": 1,
  "email": "user@example.com",
  "user_type": "buyer"
}
```

---

## Fintech Endpoints

### Get Token Balance

**GET** `/api/fintech/balance`

Get user's SPZ token balance and loyalty points.

**Headers:** Authorization required

**Response (200 OK):**
```json
{
  "success": true,
  "balance": {
    "spz": 1500.0,
    "zar_equivalent": 1500.0,
    "loyalty_points": 25.5
  },
  "token_symbol": "SPZ",
  "token_name": "Sparza Token",
  "exchange_rate": 1.0
}
```

---

### Transfer Tokens

**POST** `/api/fintech/transfer`

Transfer SPZ tokens to another user.

**Headers:** Authorization required

**Request Body:**
```json
{
  "recipient_email": "recipient@example.com",
  "amount": 100.0,
  "notes": "Payment for services"
}
```

**Response (200 OK):**
```json
{
  "success": true,
  "message": "Successfully transferred 100.0 SPZ to recipient@example.com",
  "transaction": {
    "reference_id": "TRF-20250110-A3B4C5",
    "amount": 100.0,
    "recipient": "recipient@example.com",
    "timestamp": "2025-01-10T14:30:00"
  }
}
```

**Error Responses:**
- `400` - Missing required fields or invalid amount
- `400` - Insufficient balance
- `404` - Recipient not found

---

### Deposit Tokens

**POST** `/api/fintech/deposit`

Deposit SPZ tokens via mock EFT top-up.

**Headers:** Authorization required

**Request Body:**
```json
{
  "amount": 500.0,
  "payment_reference": "EFT-CUSTOM-REF" // Optional
}
```

**Response (200 OK):**
```json
{
  "success": true,
  "message": "Successfully deposited 500.0 SPZ",
  "transaction": {
    "reference_id": "DEP-20250110-X7Y8Z9",
    "payment_reference": "EFT-CUSTOM-REF",
    "amount": 500.0,
    "timestamp": "2025-01-10T14:35:00"
  }
}
```

**Error Responses:**
- `400` - Invalid amount (must be positive and ≤ 10,000 SPZ)

---

### Withdraw Tokens

**POST** `/api/fintech/withdraw`

Request withdrawal of SPZ tokens to bank account.

**Headers:** Authorization required

**Request Body:**
```json
{
  "amount": 1000.0,
  "bank_name": "FNB",
  "account_number": "1234567890",
  "account_holder": "John Doe"
}
```

**Response (200 OK):**
```json
{
  "success": true,
  "message": "Withdrawal request submitted successfully",
  "request": {
    "request_id": 1,
    "reference_id": "WTH-20250110-M9N8P7",
    "amount_spz": 1000.0,
    "amount_zar": 1000.0,
    "status": "pending",
    "bank_name": "FNB",
    "processing_time": "1-3 business days"
  }
}
```

**Error Responses:**
- `400` - Missing required fields
- `400` - Amount must be ≥ 100 SPZ
- `400` - Insufficient balance

---

### Get Transaction History

**GET** `/api/fintech/transactions`

Get user's token transaction history.

**Headers:** Authorization required

**Query Parameters:**
- `limit` (int, default: 50) - Number of transactions to return
- `offset` (int, default: 0) - Pagination offset
- `type` (string, optional) - Filter by transaction type: `deposit`, `withdrawal`, `transfer`, `purchase`, `refund`, `reward`

**Example:**
```
GET /api/fintech/transactions?limit=20&offset=0&type=transfer
```

**Response (200 OK):**
```json
{
  "success": true,
  "transactions": [
    {
      "id": 1,
      "reference_id": "TRF-20250110-A3B4C5",
      "amount": 100.0,
      "type": "transfer",
      "status": "completed",
      "direction": "outgoing",
      "payment_reference": null,
      "notes": "Payment for services",
      "created_at": "2025-01-10T14:30:00",
      "completed_at": "2025-01-10T14:30:01"
    }
  ],
  "count": 1,
  "limit": 20,
  "offset": 0
}
```

---

## Marketplace Endpoints

### Get Products

**GET** `/api/marketplace/products`

Get list of marketplace products (public endpoint - no auth required).

**Query Parameters:**
- `limit` (int, default: 20) - Number of products to return
- `offset` (int, default: 0) - Pagination offset
- `category` (string, optional) - Filter by category
- `search` (string, optional) - Search in product name/description

**Example:**
```
GET /api/marketplace/products?limit=10&category=Electronics&search=phone
```

**Response (200 OK):**
```json
{
  "success": true,
  "products": [
    {
      "id": 1,
      "name": "Samsung Galaxy A54",
      "description": "5G smartphone with 128GB storage",
      "category": "Electronics",
      "price": 5999.0,
      "original_price": 6999.0,
      "stock_count": 15,
      "images": [
        "/static/uploads/product1_img1.jpg",
        "/static/uploads/product1_img2.jpg"
      ],
      "rating": 4.5,
      "reviews_count": 23,
      "seller": {
        "id": 1,
        "name": "Thandi's Tech Store",
        "handle": "thandistech",
        "is_subscribed": true,
        "is_verified": true
      }
    }
  ],
  "count": 1,
  "limit": 10,
  "offset": 0
}
```

---

### Get Product Detail

**GET** `/api/marketplace/product/<product_id>`

Get detailed information about a specific product (public endpoint).

**Example:**
```
GET /api/marketplace/product/1
```

**Response (200 OK):**
```json
{
  "success": true,
  "product": {
    "id": 1,
    "name": "Samsung Galaxy A54",
    "description": "5G smartphone with 128GB storage, 50MP camera",
    "category": "Electronics",
    "price": 5999.0,
    "original_price": 6999.0,
    "stock_count": 15,
    "sku": "TECH-SG-A54-128",
    "images": [
      "/static/uploads/product1_img1.jpg",
      "/static/uploads/product1_img2.jpg"
    ],
    "rating": 4.5,
    "reviews_count": 23,
    "seller": {
      "id": 1,
      "name": "Thandi's Tech Store",
      "handle": "thandistech",
      "location": "Soweto, Johannesburg",
      "rating": 4.7,
      "is_verified": true
    }
  }
}
```

**Error Responses:**
- `404` - Product not found

---

## Error Handling

All API endpoints follow consistent error response format:

```json
{
  "error": "Error message description",
  "code": "ERROR_CODE"
}
```

### Common Error Codes

- `NO_TOKEN` - Authorization token not provided
- `INVALID_TOKEN` - Token is invalid or expired
- `NOT_FOUND` - Resource not found
- `INTERNAL_ERROR` - Server error

### HTTP Status Codes

- `200` - Success
- `400` - Bad Request (invalid input)
- `401` - Unauthorized (authentication required)
- `404` - Not Found
- `500` - Internal Server Error

---

## Rate Limiting

*(To be implemented)*

Future versions will implement rate limiting to prevent abuse:
- Public endpoints: 100 requests per minute
- Authenticated endpoints: 300 requests per minute

---

## Example Usage

### Using cURL

**Login:**
```bash
curl -X POST http://localhost:5000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"buyer1@test.com","password":"buyerpass"}'
```

**Get Balance:**
```bash
curl -X GET http://localhost:5000/api/fintech/balance \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

**Transfer Tokens:**
```bash
curl -X POST http://localhost:5000/api/fintech/transfer \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "recipient_email": "thandi@sparzafi.com",
    "amount": 50.0,
    "notes": "Payment for order"
  }'
```

### Using Python (requests)

```python
import requests

# Login
response = requests.post('http://localhost:5000/api/auth/login', json={
    'email': 'buyer1@test.com',
    'password': 'buyerpass'
})
data = response.json()
token = data['token']

# Get balance
headers = {'Authorization': f'Bearer {token}'}
response = requests.get('http://localhost:5000/api/fintech/balance', headers=headers)
balance = response.json()
print(f"SPZ Balance: {balance['balance']['spz']}")

# Transfer tokens
response = requests.post(
    'http://localhost:5000/api/fintech/transfer',
    headers=headers,
    json={
        'recipient_email': 'thandi@sparzafi.com',
        'amount': 50.0,
        'notes': 'Payment for order'
    }
)
print(response.json())
```

### Using JavaScript (fetch)

```javascript
// Login
const loginResponse = await fetch('http://localhost:5000/api/auth/login', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    email: 'buyer1@test.com',
    password: 'buyerpass'
  })
});
const { token } = await loginResponse.json();

// Get balance
const balanceResponse = await fetch('http://localhost:5000/api/fintech/balance', {
  headers: { 'Authorization': `Bearer ${token}` }
});
const balance = await balanceResponse.json();
console.log('SPZ Balance:', balance.balance.spz);

// Transfer tokens
const transferResponse = await fetch('http://localhost:5000/api/fintech/transfer', {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    recipient_email: 'thandi@sparzafi.com',
    amount: 50.0,
    notes: 'Payment for order'
  })
});
const result = await transferResponse.json();
console.log(result);
```

---

## Testing Credentials

Use these accounts for testing (created during database seeding):

| Role | Email | Password |
|------|-------|----------|
| Admin | admin@sparzafi.com | adminpass |
| Seller | thandi@sparzafi.com | sellerpass |
| Deliverer | sipho.driver@sparzafi.com | driverpass |
| Buyer | buyer1@test.com | buyerpass |

All test accounts start with:
- **1,500 SPZ** token balance
- **KYC verified** status

---

## Support

For API support or questions:
- GitHub Issues: [Create an issue](https://github.com/your-repo/sparzafi/issues)
- Email: support@sparzafi.com

---

**SparzaFI API v1.0** - Last updated: January 2025
