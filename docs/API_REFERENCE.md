# PySentry WAF - API Reference

**Version**: 1.0.0  
**Last Updated**: October 2024

## Overview

The PySentry WAF REST API provides comprehensive endpoints for managing web application firewall operations, including threat intelligence, IP blocking, request analysis, and system monitoring.

**Base URL**: `http://localhost:5000/api/v1`

**Authentication**: JWT Bearer Token required for all endpoints (except `/health`)

---

## Table of Contents

- [Authentication](#authentication)
- [Threat Management](#threat-management)
- [IP Blocking](#ip-blocking)
- [Request Analysis](#request-analysis)
- [Monitoring & Metrics](#monitoring--metrics)
- [Error Handling](#error-handling)
- [Rate Limiting](#rate-limiting)

---

## Authentication

### POST /auth/login

Authenticate and receive JWT token.

**Request**:
```json
{
  "username": "admin",
  "password": "secure_password"
}
```

**Response** (200 OK):
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 3600
}
```

**Usage**:
```bash
curl -X POST http://localhost:5000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"secure_password"}'
```

### Token Usage

Include token in Authorization header:
```bash
curl -H "Authorization: Bearer YOUR_TOKEN" \
  http://localhost:5000/api/v1/threats
```

---

## Threat Management

### GET /threats

Retrieve all threats with optional filtering.

**Query Parameters**:
- `severity` (optional): Filter by severity (low, medium, high, critical)
- `type` (optional): Filter by threat type (sqli, xss, cmdi, path-traversal)
- `status` (optional): Filter by status (active, resolved, false-positive)
- `page` (optional): Page number (default: 1)
- `per_page` (optional): Items per page (default: 20, max: 100)

**Response** (200 OK):
```json
{
  "threats": [
    {
      "id": "507f1f77bcf86cd799439011",
      "type": "sqli",
      "severity": "high",
      "status": "active",
      "detected_at": "2024-10-01T10:30:00Z",
      "source_ip": "192.168.1.100",
      "details": {
        "pattern": "' OR '1'='1",
        "location": "query_param"
      }
    }
  ],
  "pagination": {
    "page": 1,
    "per_page": 20,
    "total": 45,
    "pages": 3
  }
}
```

**Example**:
```bash
curl -H "Authorization: Bearer TOKEN" \
  "http://localhost:5000/api/v1/threats?severity=high&page=1"
```

### GET /threats/{threat_id}

Retrieve specific threat by ID.

**Response** (200 OK):
```json
{
  "id": "507f1f77bcf86cd799439011",
  "type": "sqli",
  "severity": "high",
  "status": "active",
  "detected_at": "2024-10-01T10:30:00Z",
  "source_ip": "192.168.1.100",
  "details": {
    "pattern": "' OR '1'='1",
    "location": "query_param",
    "request_method": "POST",
    "endpoint": "/api/users"
  }
}
```

### POST /threats

Create new threat entry.

**Request**:
```json
{
  "type": "xss",
  "severity": "high",
  "source_ip": "10.0.0.50",
  "details": {
    "pattern": "<script>alert('XSS')</script>",
    "location": "body"
  }
}
```

**Response** (201 Created):
```json
{
  "id": "507f1f77bcf86cd799439012",
  "message": "Threat created successfully"
}
```

### PUT /threats/{threat_id}

Update threat information.

**Request**:
```json
{
  "status": "resolved",
  "notes": "False positive - legitimate query"
}
```

**Response** (200 OK):
```json
{
  "message": "Threat updated successfully"
}
```

### DELETE /threats/{threat_id}

Delete threat entry.

**Response** (200 OK):
```json
{
  "message": "Threat deleted successfully"
}
```

---

## IP Blocking

### GET /blocked-ips

List all blocked IP addresses.

**Query Parameters**:
- `page` (optional): Page number
- `per_page` (optional): Items per page

**Response** (200 OK):
```json
{
  "blocked_ips": [
    {
      "ip_address": "192.168.1.100",
      "reason": "Multiple SQL injection attempts",
      "blocked_at": "2024-10-01T09:00:00Z",
      "expires_at": "2024-10-02T09:00:00Z",
      "is_subnet": false
    }
  ],
  "pagination": {
    "page": 1,
    "per_page": 20,
    "total": 15
  }
}
```

### GET /blocked-ips/{ip_address}

Check if specific IP is blocked.

**Response** (200 OK):
```json
{
  "is_blocked": true,
  "ip_address": "192.168.1.100",
  "reason": "Multiple SQL injection attempts",
  "blocked_at": "2024-10-01T09:00:00Z",
  "expires_at": "2024-10-02T09:00:00Z"
}
```

### POST /blocked-ips

Block an IP address.

**Request**:
```json
{
  "ip_address": "10.0.0.50",
  "reason": "Brute force attack detected",
  "ttl": 86400
}
```

**Response** (201 Created):
```json
{
  "message": "IP address blocked successfully",
  "expires_at": "2024-10-02T09:00:00Z"
}
```

### POST /blocked-ips/subnet

Block IP subnet (CIDR notation).

**Request**:
```json
{
  "subnet": "192.168.1.0/24",
  "reason": "Malicious network range",
  "ttl": 604800
}
```

**Response** (201 Created):
```json
{
  "message": "Subnet blocked successfully",
  "affected_ips": "256 addresses"
}
```

### DELETE /blocked-ips/{ip_address}

Unblock an IP address.

**Response** (200 OK):
```json
{
  "message": "IP address unblocked successfully"
}
```

---

## Request Analysis

### POST /analyze

Analyze incoming request for threats.

**Request**:
```json
{
  "method": "POST",
  "url": "/api/users?id=1",
  "headers": {
    "User-Agent": "Mozilla/5.0",
    "Content-Type": "application/json"
  },
  "body": "{\"name\":\"test\"}",
  "source_ip": "192.168.1.50"
}
```

**Response** (200 OK):
```json
{
  "safe": true,
  "threats_detected": [],
  "risk_score": 0,
  "recommendation": "allow"
}
```

**Response with Threat** (200 OK):
```json
{
  "safe": false,
  "threats_detected": [
    {
      "type": "sqli",
      "severity": "high",
      "location": "query_param",
      "pattern": "' OR '1'='1"
    }
  ],
  "risk_score": 85,
  "recommendation": "block",
  "action_taken": "request_blocked"
}
```

---

## Monitoring & Metrics

### GET /health

Health check endpoint (no authentication required).

**Response** (200 OK):
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "components": {
    "database": "healthy",
    "redis": "healthy",
    "ml_model": "healthy"
  },
  "uptime": 86400
}
```

### GET /metrics

Prometheus metrics endpoint (no authentication required).

**Response** (200 OK):
```
# HELP waf_requests_total Total number of requests processed
# TYPE waf_requests_total counter
waf_requests_total{method="GET",status="200"} 12345

# HELP waf_threats_detected_total Total threats detected
# TYPE waf_threats_detected_total counter
waf_threats_detected_total{type="sqli",severity="high"} 45

# HELP waf_blocked_requests_total Total requests blocked
# TYPE waf_blocked_requests_total counter
waf_blocked_requests_total 127
```

### GET /stats

Real-time WAF statistics.

**Response** (200 OK):
```json
{
  "requests_processed": 125000,
  "threats_detected": 452,
  "requests_blocked": 127,
  "false_positives": 12,
  "performance": {
    "avg_response_time_ms": 2.5,
    "requests_per_second": 10000
  },
  "top_threats": [
    {"type": "sqli", "count": 245},
    {"type": "xss", "count": 187}
  ]
}
```

---

## Error Handling

All API errors follow this format:

```json
{
  "error": {
    "code": "THREAT_NOT_FOUND",
    "message": "Threat with ID 507f1f77bcf86cd799439011 not found",
    "details": {}
  }
}
```

### HTTP Status Codes

| Code | Meaning |
|------|---------|
| 200 | Success |
| 201 | Created |
| 400 | Bad Request - Invalid input |
| 401 | Unauthorized - Missing or invalid token |
| 403 | Forbidden - Insufficient permissions |
| 404 | Not Found |
| 409 | Conflict - Resource already exists |
| 429 | Too Many Requests - Rate limit exceeded |
| 500 | Internal Server Error |
| 503 | Service Unavailable |

### Common Error Codes

- `INVALID_INPUT`: Request validation failed
- `UNAUTHORIZED`: Authentication required
- `FORBIDDEN`: Insufficient permissions
- `NOT_FOUND`: Resource not found
- `ALREADY_EXISTS`: Resource already exists
- `RATE_LIMIT_EXCEEDED`: Too many requests
- `INTERNAL_ERROR`: Server error

---

## Rate Limiting

**Default Limits**:
- Anonymous: 100 requests per minute
- Authenticated: 1000 requests per minute
- Admin: 10000 requests per minute

**Rate Limit Headers**:
```
X-RateLimit-Limit: 1000
X-RateLimit-Remaining: 950
X-RateLimit-Reset: 1633075200
```

**Rate Limit Exceeded Response** (429):
```json
{
  "error": {
    "code": "RATE_LIMIT_EXCEEDED",
    "message": "Rate limit of 1000 requests per minute exceeded",
    "retry_after": 45
  }
}
```

---

## OpenAPI/Swagger

Interactive API documentation available at:
```
http://localhost:5000/docs
```

Download OpenAPI specification:
```
http://localhost:5000/openapi.json
```

---

## SDK Examples

### Python
```python
import requests

# Authentication
response = requests.post(
    "http://localhost:5000/api/v1/auth/login",
    json={"username": "admin", "password": "password"}
)
token = response.json()["access_token"]

# List threats
headers = {"Authorization": f"Bearer {token}"}
response = requests.get(
    "http://localhost:5000/api/v1/threats?severity=high",
    headers=headers
)
threats = response.json()["threats"]
```

### cURL
```bash
# Get token
TOKEN=$(curl -s -X POST http://localhost:5000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"password"}' \
  | jq -r '.access_token')

# List threats
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:5000/api/v1/threats
```

---

## Best Practices

1. **Always use HTTPS in production**
2. **Store tokens securely** - Never in code or logs
3. **Implement token refresh** for long-running applications
4. **Handle rate limits** with exponential backoff
5. **Validate responses** before processing
6. **Use pagination** for large datasets
7. **Monitor API health** regularly

---

## Support

For issues or questions:
- GitHub Issues: https://github.com/r3tr056/pysentry-waf/issues
- Email: dangerankur56@gmail.com
- Documentation: https://github.com/r3tr056/pysentry-waf/docs
