# PySentry WAF - API Documentation

## Overview

PySentry WAF provides a comprehensive REST API for managing web application firewall operations, including threat intelligence, IP blocking, request analysis, health monitoring, and metrics collection.

**Base URL**: `http://localhost:5000/api/v1`

**Authentication**: Bearer Token (JWT) or API Key

**Content-Type**: `application/json`

---

## Table of Contents

1. [Authentication](#authentication)
2. [Threat Management](#threat-management)
3. [IP Blocking](#ip-blocking)
4. [Request Analysis](#request-analysis)
5. [Health & Monitoring](#health--monitoring)
6. [Metrics](#metrics)
7. [Error Responses](#error-responses)
8. [Rate Limiting](#rate-limiting)

---

## Authentication

### JWT Authentication

**Endpoint**: `POST /api/v1/auth/login`

**Request**:
```json
{
  "username": "admin",
  "password": "secure_password"
}
```

**Response**:
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 3600
}
```

**Usage**:
```bash
curl -H "Authorization: Bearer YOUR_TOKEN" http://localhost:5000/api/v1/threats
```

### API Key Authentication

**Header**: `X-API-Key: your-api-key-here`

**Usage**:
```bash
curl -H "X-API-Key: YOUR_API_KEY" http://localhost:5000/api/v1/threats
```

---

## Threat Management

### List All Threats

**Endpoint**: `GET /api/v1/threats`

**Query Parameters**:
- `severity` (optional): Filter by severity (`critical`, `high`, `medium`, `low`)
- `type` (optional): Filter by threat type (`sqli`, `xss`, `cmdi`, `path-traversal`)
- `status` (optional): Filter by status (`active`, `mitigated`, `archived`)
- `page` (optional): Page number (default: 1)
- `per_page` (optional): Items per page (default: 50, max: 100)

**Response**:
```json
{
  "threats": [
    {
      "id": "threat_123",
      "type": "sqli",
      "severity": "critical",
      "description": "SQL injection attempt detected",
      "source_ip": "192.168.1.100",
      "target_url": "/api/users",
      "status": "active",
      "detected_at": "2024-10-01T12:34:56Z",
      "metadata": {
        "user_agent": "Mozilla/5.0...",
        "payload": "' OR '1'='1"
      }
    }
  ],
  "pagination": {
    "page": 1,
    "per_page": 50,
    "total": 150,
    "pages": 3
  }
}
```

### Get Single Threat

**Endpoint**: `GET /api/v1/threats/{threat_id}`

**Response**:
```json
{
  "id": "threat_123",
  "type": "sqli",
  "severity": "critical",
  "description": "SQL injection attempt detected",
  "source_ip": "192.168.1.100",
  "target_url": "/api/users",
  "status": "active",
  "detected_at": "2024-10-01T12:34:56Z",
  "updated_at": "2024-10-01T12:35:00Z",
  "metadata": {
    "user_agent": "Mozilla/5.0...",
    "payload": "' OR '1'='1",
    "confidence_score": 0.95
  }
}
```

### Create Threat

**Endpoint**: `POST /api/v1/threats`

**Request**:
```json
{
  "type": "xss",
  "severity": "high",
  "description": "Cross-site scripting attempt",
  "source_ip": "10.0.0.50",
  "target_url": "/comments",
  "metadata": {
    "payload": "<script>alert('XSS')</script>"
  }
}
```

**Response**: `201 Created`
```json
{
  "id": "threat_456",
  "type": "xss",
  "severity": "high",
  "status": "active",
  "created_at": "2024-10-01T13:00:00Z"
}
```

### Update Threat

**Endpoint**: `PATCH /api/v1/threats/{threat_id}`

**Request**:
```json
{
  "status": "mitigated",
  "severity": "medium"
}
```

**Response**: `200 OK`

### Delete Threat

**Endpoint**: `DELETE /api/v1/threats/{threat_id}`

**Response**: `204 No Content`

---

## IP Blocking

### List Blocked IPs

**Endpoint**: `GET /api/v1/blocked-ips`

**Query Parameters**:
- `page` (optional): Page number
- `per_page` (optional): Items per page

**Response**:
```json
{
  "blocked_ips": [
    {
      "ip_address": "192.168.1.100",
      "reason": "Multiple SQL injection attempts",
      "blocked_at": "2024-10-01T12:00:00Z",
      "expires_at": "2024-10-02T12:00:00Z",
      "is_subnet": false
    },
    {
      "ip_address": "10.0.0.0/24",
      "reason": "Malicious subnet",
      "blocked_at": "2024-10-01T10:00:00Z",
      "expires_at": null,
      "is_subnet": true
    }
  ],
  "pagination": {
    "page": 1,
    "per_page": 50,
    "total": 25
  }
}
```

### Block IP Address

**Endpoint**: `POST /api/v1/blocked-ips`

**Request**:
```json
{
  "ip_address": "192.168.1.200",
  "reason": "Brute force attack detected",
  "ttl": 86400
}
```

**Response**: `201 Created`
```json
{
  "ip_address": "192.168.1.200",
  "blocked_at": "2024-10-01T14:00:00Z",
  "expires_at": "2024-10-02T14:00:00Z"
}
```

### Check if IP is Blocked

**Endpoint**: `GET /api/v1/blocked-ips/{ip_address}`

**Response**:
```json
{
  "is_blocked": true,
  "ip_address": "192.168.1.100",
  "reason": "Multiple threats detected",
  "blocked_at": "2024-10-01T12:00:00Z"
}
```

### Unblock IP Address

**Endpoint**: `DELETE /api/v1/blocked-ips/{ip_address}`

**Response**: `204 No Content`

---

## Request Analysis

### Analyze Request

**Endpoint**: `POST /api/v1/analyze`

**Request**:
```json
{
  "method": "GET",
  "url": "/api/users?id=1' OR '1'='1",
  "headers": {
    "User-Agent": "Mozilla/5.0...",
    "X-Forwarded-For": "192.168.1.100"
  },
  "body": null
}
```

**Response**:
```json
{
  "request_id": "req_789",
  "is_threat": true,
  "threats_detected": [
    {
      "type": "sqli",
      "severity": "critical",
      "location": "query_parameter",
      "confidence": 0.98
    }
  ],
  "action_taken": "blocked",
  "source_ip": "192.168.1.100",
  "analyzed_at": "2024-10-01T15:00:00Z"
}
```

### Batch Analyze Requests

**Endpoint**: `POST /api/v1/analyze/batch`

**Request**:
```json
{
  "requests": [
    {
      "method": "GET",
      "url": "/api/users",
      "source_ip": "10.0.0.1"
    },
    {
      "method": "POST",
      "url": "/login",
      "source_ip": "10.0.0.2"
    }
  ]
}
```

**Response**:
```json
{
  "results": [
    {
      "request_id": "req_790",
      "is_threat": false
    },
    {
      "request_id": "req_791",
      "is_threat": false
    }
  ],
  "processed": 2,
  "threats_found": 0
}
```

---

## Health & Monitoring

### Health Check

**Endpoint**: `GET /api/v1/health`

**Response**:
```json
{
  "status": "healthy",
  "timestamp": "2024-10-01T16:00:00Z",
  "components": {
    "application": {
      "status": "ok",
      "message": "Application is running"
    },
    "database": {
      "status": "ok",
      "response_time_ms": 5,
      "message": "MongoDB connection healthy"
    },
    "redis": {
      "status": "ok",
      "response_time_ms": 1,
      "message": "Redis connection healthy"
    },
    "ml_model": {
      "status": "ok",
      "message": "Threat classifier loaded"
    }
  },
  "uptime_seconds": 86400
}
```

### Liveness Probe

**Endpoint**: `GET /api/v1/health/live`

**Response**: `200 OK` (if alive) or `503 Service Unavailable` (if down)

### Readiness Probe

**Endpoint**: `GET /api/v1/health/ready`

**Response**: `200 OK` (if ready) or `503 Service Unavailable` (if not ready)

---

## Metrics

### Get Prometheus Metrics

**Endpoint**: `GET /api/v1/metrics`

**Response**: Prometheus text format
```
# HELP waf_requests_total Total number of requests processed
# TYPE waf_requests_total counter
waf_requests_total{method="GET",status="200"} 1547

# HELP waf_threats_detected_total Total number of threats detected
# TYPE waf_threats_detected_total counter
waf_threats_detected_total{type="sqli",severity="critical"} 23
waf_threats_detected_total{type="xss",severity="high"} 15

# HELP waf_blocked_requests_total Total number of blocked requests
# TYPE waf_blocked_requests_total counter
waf_blocked_requests_total 38

# HELP waf_request_duration_seconds Request processing duration
# TYPE waf_request_duration_seconds histogram
waf_request_duration_seconds_bucket{le="0.005"} 1234
waf_request_duration_seconds_bucket{le="0.01"} 1456
waf_request_duration_seconds_sum 156.78
waf_request_duration_seconds_count 1547
```

### Get WAF Statistics

**Endpoint**: `GET /api/v1/stats`

**Response**:
```json
{
  "requests": {
    "total": 15470,
    "blocked": 385,
    "allowed": 15085,
    "block_rate": 0.0249
  },
  "threats": {
    "total": 423,
    "by_type": {
      "sqli": 156,
      "xss": 98,
      "cmdi": 45,
      "path_traversal": 124
    },
    "by_severity": {
      "critical": 89,
      "high": 167,
      "medium": 145,
      "low": 22
    }
  },
  "performance": {
    "avg_response_time_ms": 5.2,
    "p50_ms": 3.1,
    "p95_ms": 12.4,
    "p99_ms": 24.8
  },
  "period": {
    "start": "2024-10-01T00:00:00Z",
    "end": "2024-10-01T23:59:59Z"
  }
}
```

---

## Error Responses

### Standard Error Format

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Invalid request parameters",
    "details": {
      "field": "severity",
      "issue": "Must be one of: critical, high, medium, low"
    }
  },
  "request_id": "req_123",
  "timestamp": "2024-10-01T17:00:00Z"
}
```

### HTTP Status Codes

| Code | Meaning | Usage |
|------|---------|-------|
| 200 | OK | Successful GET, PATCH |
| 201 | Created | Successful POST |
| 204 | No Content | Successful DELETE |
| 400 | Bad Request | Invalid request parameters |
| 401 | Unauthorized | Missing or invalid authentication |
| 403 | Forbidden | Insufficient permissions |
| 404 | Not Found | Resource not found |
| 409 | Conflict | Resource already exists |
| 413 | Content Too Large | Request body too large |
| 429 | Too Many Requests | Rate limit exceeded |
| 500 | Internal Server Error | Server error |
| 503 | Service Unavailable | Service temporarily unavailable |

---

## Rate Limiting

All API endpoints are rate-limited to prevent abuse.

**Default Limits**:
- **Authenticated requests**: 100 requests per minute per user
- **Unauthenticated requests**: 20 requests per minute per IP
- **Batch operations**: 10 requests per minute per user

**Rate Limit Headers**:
```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 87
X-RateLimit-Reset: 1696176000
```

**Rate Limit Exceeded Response**: `429 Too Many Requests`
```json
{
  "error": {
    "code": "RATE_LIMIT_EXCEEDED",
    "message": "Too many requests. Please try again later.",
    "retry_after": 23
  }
}
```

---

## Examples

### Python Example

```python
import requests

# Authentication
response = requests.post(
    "http://localhost:5000/api/v1/auth/login",
    json={"username": "admin", "password": "secure_password"}
)
token = response.json()["access_token"]

# List threats
headers = {"Authorization": f"Bearer {token}"}
response = requests.get(
    "http://localhost:5000/api/v1/threats",
    headers=headers,
    params={"severity": "critical", "page": 1}
)
threats = response.json()["threats"]

# Analyze request
response = requests.post(
    "http://localhost:5000/api/v1/analyze",
    headers=headers,
    json={
        "method": "GET",
        "url": "/api/users?id=1",
        "source_ip": "10.0.0.1"
    }
)
result = response.json()
```

### cURL Examples

```bash
# Get health status
curl http://localhost:5000/api/v1/health

# List blocked IPs (with authentication)
curl -H "Authorization: Bearer YOUR_TOKEN" \
     http://localhost:5000/api/v1/blocked-ips

# Block an IP
curl -X POST \
     -H "Authorization: Bearer YOUR_TOKEN" \
     -H "Content-Type: application/json" \
     -d '{"ip_address":"192.168.1.100","reason":"Attack detected"}' \
     http://localhost:5000/api/v1/blocked-ips

# Get metrics
curl http://localhost:5000/api/v1/metrics
```

---

## WebSocket Support (Future)

Real-time threat notifications will be available via WebSocket in a future release:

```javascript
const ws = new WebSocket('ws://localhost:5000/api/v1/ws/threats');

ws.onmessage = (event) => {
  const threat = JSON.parse(event.data);
  console.log('New threat detected:', threat);
};
```

---

## API Versioning

The API uses URL-based versioning. The current version is `v1`.

Future versions will be available at:
- `/api/v2/...`
- `/api/v3/...`

Legacy versions will be supported for at least 12 months after a new version is released.

---

## OpenAPI Specification

The complete OpenAPI 3.0 specification is available at:

**Endpoint**: `GET /api/v1/openapi.json`

**Swagger UI**: `http://localhost:5000/docs`

**ReDoc**: `http://localhost:5000/redoc`

---

## Support

For API support, please contact:
- **Email**: support@pysentry-waf.io
- **Documentation**: https://docs.pysentry-waf.io
- **GitHub Issues**: https://github.com/r3tr056/pysentry-waf/issues

---

**Last Updated**: October 2024  
**API Version**: 1.0.0
