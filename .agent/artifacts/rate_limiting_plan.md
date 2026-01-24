# Implementation Plan: Rate Limiting for Expensive Endpoints

## Overview

This plan implements rate limiting for the expensive `/api/dag/generate` and `/api/dag/preview` endpoints using **slowapi**, a rate limiting library designed for FastAPI/Starlette applications.

## Architecture Decision

- **Library**: slowapi (built on top of `limits` library)
- **Backend**: In-memory storage (suitable for single-instance deployment; can be upgraded to Redis for distributed systems)
- **Key Function**: Remote address (IP-based rate limiting)
- **Rate Limits**:
  - `/generate`: 10 requests per minute per IP
  - `/preview`: 30 requests per minute per IP (more lenient as it's for quick previews)

## Implementation Steps

### 1. Install slowapi dependency
Add `slowapi>=0.1.9` to `requirements.txt`

### 2. Create rate limiter configuration module
Create `backend/app/core/rate_limiter.py` with:
- Limiter instance with `get_remote_address` as key function
- Rate limit exception handler

### 3. Integrate into FastAPI application
Update `backend/app/main.py`:
- Import limiter and exception handler
- Add limiter to app state
- Register exception handler for `RateLimitExceeded`

### 4. Apply rate limits to endpoints
Update `backend/app/api/routes/dag.py`:
- Import limiter
- Add `@limiter.limit()` decorator to `/generate` endpoint
- Add `@limiter.limit()` decorator to `/preview` endpoint
- Ensure `request: Request` parameter is present in both endpoints

### 5. Testing
- Create tests to verify rate limiting works correctly
- Ensure other endpoints remain unaffected

## Rate Limit Format

slowapi uses the `limits` library format:
- `10/minute` - 10 requests per minute
- `5/second` - 5 requests per second
- `100/hour` - 100 requests per hour

## Error Response

When rate limit is exceeded, the API returns:
- HTTP 429 Too Many Requests
- Headers indicating retry time

## Files to Modify/Create

1. `backend/requirements.txt` - Add slowapi dependency
2. `backend/app/core/rate_limiter.py` - New file for limiter configuration
3. `backend/app/main.py` - Register limiter with app
4. `backend/app/api/routes/dag.py` - Apply rate limits to endpoints
5. `backend/tests/test_rate_limiting.py` - Tests for rate limiting
