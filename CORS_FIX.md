# CORS Network Error - FIXED ✅

## Problem
Frontend was showing "Network error. Please check your connection." when trying to upload files, even though the backend was running.

**Root Cause**: CORS (Cross-Origin Resource Sharing) was configured to only allow `http://localhost:3000`, but the development frontend runs on port `5173` or `5174`.

## Solution
Updated `backend/app.py` to allow the development server ports in CORS configuration:

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",      # Original port (kept for compatibility)
        "http://localhost:5173",      # Vite dev server
        "http://localhost:5174",      # Alternative port
        "http://127.0.0.1:5173",      # Loopback variant
        "http://127.0.0.1:5174",      # Loopback variant
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

## Verification ✅

### CORS Headers Present
```bash
curl -i http://127.0.0.1:8000/api/health -H "Origin: http://localhost:5173"
```

Response includes:
```
HTTP/1.1 200 OK
access-control-allow-origin: http://localhost:5173
access-control-allow-credentials: true
```

### Preflight Request Works
```bash
curl -i -X OPTIONS http://127.0.0.1:8000/api/datasets/upload \
  -H "Origin: http://localhost:5173" \
  -H "Access-Control-Request-Method: POST" \
  -H "Access-Control-Request-Headers: Content-Type"
```

Response:
```
HTTP/1.1 200 OK
access-control-allow-origin: http://localhost:5173
access-control-allow-methods: DELETE, GET, HEAD, OPTIONS, PATCH, POST, PUT
access-control-allow-headers: Content-Type
```

## How to Use

### 1. Backend Auto-Reload
The backend was running with `--reload`, so it automatically picked up the changes when `app.py` was modified.

### 2. Frontend - Hard Refresh Browser
To clear cached CORS decisions and old HTTP calls:
- **Windows/Linux**: `Ctrl+Shift+R`
- **Mac**: `Cmd+Shift+R`

Or open DevTools and disable cache:
1. Open Developer Tools (F12)
2. Go to Settings (gear icon)
3. Check "Disable cache (while DevTools is open)"

### 3. Test Upload
1. Go to http://localhost:5173/upload (or your frontend port)
2. Try uploading a CSV/Excel file
3. The "Network error" should be gone
4. File should be accepted and show in preview

## Files Modified
- `backend/app.py` - Updated CORS middleware configuration

## Related Issues Resolved
- ✅ "Network error. Please check your connection." message
- ✅ File upload endpoint unreachable from frontend
- ✅ Browser console CORS errors (if any were present)

## Notes for Production
In production, update the CORS origins to match your actual domain:
```python
allow_origins=[
    "https://yourdomain.com",
    "https://www.yourdomain.com",
]
```

For development with Docker or different setup, adjust as needed.

## Git Commit
```
commit f45ecf0
Author: Copilot
Date:   2026-04-20

    fix: Enable CORS for frontend dev server ports 5173/5174
    
    Added ports 5173/5174 to allowed origins for frontend development
    Fixes 'Network error' in frontend when uploading files
```
