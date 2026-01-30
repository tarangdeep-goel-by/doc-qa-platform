# Production Security Checklist - Doc-QA Platform

**Last Updated**: January 29, 2026
**Status**: ❌ NOT PRODUCTION READY

---

## 🔴 CRITICAL (Must Complete Before ANY Production Deployment)

### Authentication & Authorization

- [ ] **Implement authentication system**
  - [ ] Choose: JWT tokens, OAuth2, or API key based
  - [ ] Add user registration/login endpoints
  - [ ] Secure password hashing (bcrypt, argon2)
  - [ ] Add `@requires_auth` decorator to ALL endpoints

- [ ] **Add user isolation**
  - [ ] Documents belong to specific users
  - [ ] Chats belong to specific users
  - [ ] Users can only access their own data
  - [ ] Admin role for user management

- [ ] **Implement API key system** (if using API keys)
  - [ ] Generate unique API keys per user
  - [ ] Validate API key on every request
  - [ ] Rate limit per API key
  - [ ] Revocation mechanism

**Code Example**:
```python
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizational

security = HTTPBearer()

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials
    user = verify_jwt_token(token)  # Implement this
    if not user:
        raise HTTPException(status_code=401, detail="Invalid authentication")
    return user

@router.post("/upload")
async def upload_document(
    request: Request,
    file: UploadFile,
    user = Depends(get_current_user)  # ✅ Now protected!
):
    # user.id is authenticated user
    pass
```

### CORS Configuration

- [ ] **Restrict CORS origins**
  - [ ] Add `ALLOWED_ORIGINS` to `.env`
  - [ ] Set to specific domains only: `https://yourdomain.com,https://app.yourdomain.com`
  - [ ] Update `main.py` to use env variable
  - [ ] Test cross-origin requests

**Code Fix**:
```python
# .env
ALLOWED_ORIGINS=https://yourdomain.com,https://app.yourdomain.com

# main.py
import os

allowed_origins = os.getenv("ALLOWED_ORIGINS", "").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],  # Specific methods
    allow_headers=["Content-Type", "Authorization"],  # Specific headers
)
```

### File Upload Security

- [ ] **Add file size limits**
  - [ ] Set MAX_FILE_SIZE in .env (e.g., 50MB)
  - [ ] Reject files exceeding limit before reading
  - [ ] Return 413 Payload Too Large error

- [ ] **Validate MIME types**
  - [ ] Install `python-magic`: `pip install python-magic`
  - [ ] Check actual file content, not just extension
  - [ ] Reject non-PDF files

- [ ] **Sanitize filenames**
  - [ ] Use `os.path.basename()` to strip paths
  - [ ] Remove special characters
  - [ ] Generate unique IDs instead of using original names

**Code Fix**:
```python
import magic
import os
from pathlib import Path

MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB

@router.post("/upload")
async def upload_document(
    request: Request,
    file: UploadFile = File(...),
    user = Depends(get_current_user)
):
    # 1. Check size
    if file.size and file.size > MAX_FILE_SIZE:
        raise HTTPException(status_code=413, detail="File too large (max 50MB)")

    # 2. Validate MIME type
    content = await file.read(1024)
    mime = magic.from_buffer(content, mime=True)
    await file.seek(0)  # Reset file pointer

    if mime != 'application/pdf':
        raise HTTPException(status_code=400, detail=f"Invalid file type: {mime}")

    # 3. Sanitize filename
    safe_filename = os.path.basename(file.filename)
    safe_filename = "".join(c for c in safe_filename if c.isalnum() or c in '._- ')

    # 4. Use unique ID
    doc_id = str(uuid.uuid4())
    file_path = Path(upload_dir) / f"{doc_id}.pdf"

    # 5. Save with validated path
    with open(file_path, 'wb') as f:
        content = await file.read()
        f.write(content)
```

### Error Handling

- [ ] **Remove stack traces from API responses**
  - [ ] Implement structured logging
  - [ ] Log detailed errors server-side only
  - [ ] Return generic messages to clients

**Code Fix**:
```python
import logging

logger = logging.getLogger(__name__)

@router.post("/upload")
async def upload_document(...):
    try:
        # code
    except Exception as e:
        # Log internally with full details
        logger.error(f"Upload failed for user {user.id}: {str(e)}", exc_info=True)

        # Return generic message to client
        raise HTTPException(
            status_code=500,
            detail="An error occurred while processing your document. Please try again."
        )
```

---

## 🟠 HIGH PRIORITY (Complete within 1 week)

### Path Traversal Protection

- [ ] **Validate file download paths**
  - [ ] Check file path is within upload directory
  - [ ] Use `Path.resolve()` to prevent `../` attacks
  - [ ] Verify file exists before returning

**Code Fix**:
```python
from pathlib import Path

@router.get("/documents/{doc_id}/file")
async def download_document(
    request: Request,
    doc_id: str,
    user = Depends(get_current_user)
):
    doc = document_store.get_document(doc_id)

    # Verify ownership
    if doc.owner_id != user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    # Validate path
    uploads_path = Path(app.state.upload_dir).resolve()
    file_path = Path(doc.file_path).resolve()

    # Ensure file is within uploads directory
    if not str(file_path).startswith(str(uploads_path)):
        logger.error(f"Path traversal attempt: {file_path}")
        raise HTTPException(status_code=403, detail="Access denied")

    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")

    return FileResponse(file_path, media_type='application/pdf', filename=doc.filename)
```

### Rate Limiting

- [ ] **Install slowapi**: `pip install slowapi`
- [ ] **Add rate limiters to all endpoints**
  - [ ] Upload: 10/hour per user
  - [ ] Query: 100/hour per user
  - [ ] Admin: 50/hour per user

**Code Fix**:
```python
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter

@router.post("/upload")
@limiter.limit("10/hour")
async def upload_document(request: Request, ...):
    pass

@router.post("/ask")
@limiter.limit("100/hour")
async def ask_question(request: Request, ...):
    pass
```

### HTTPS/SSL

- [ ] **Obtain SSL certificate**
  - [ ] Use Let's Encrypt (free)
  - [ ] Or purchase from CA

- [ ] **Set up reverse proxy (nginx)**
  - [ ] Terminate SSL at nginx
  - [ ] Redirect HTTP → HTTPS
  - [ ] Proxy to FastAPI backend

**nginx config**:
```nginx
server {
    listen 80;
    server_name yourdomain.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl;
    server_name yourdomain.com;

    ssl_certificate /etc/letsencrypt/live/yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/yourdomain.com/privkey.pem;

    location / {
        proxy_pass http://backend:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

### Security Headers

- [ ] **Add security headers middleware**

**Code Fix**:
```python
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    response.headers["Content-Security-Policy"] = "default-src 'self'"
    return response
```

---

## 🟡 MEDIUM PRIORITY (Complete within 1 month)

### Environment Configuration

- [ ] **Separate dev/prod configs**
  - [ ] `.env.development`
  - [ ] `.env.production`
  - [ ] Never commit real `.env` files

- [ ] **Disable debug mode in production**
  - [ ] Set `reload=False` in `run_api.py`
  - [ ] Set `log_level="warning"`
  - [ ] Remove verbose error messages

**Code Fix**:
```python
# run_api.py
import os

ENVIRONMENT = os.getenv("ENVIRONMENT", "development")

uvicorn.run(
    "api.main:app",
    host=host,
    port=port,
    reload=(ENVIRONMENT == "development"),
    log_level="warning" if ENVIRONMENT == "production" else "info"
)
```

### Database Security

- [ ] **Enable Qdrant authentication**
  - [ ] Set `QDRANT_API_KEY` in docker-compose
  - [ ] Update client to use API key

**docker-compose.yml**:
```yaml
qdrant:
  image: qdrant/qdrant:latest
  environment:
    - QDRANT__SERVICE__API_KEY=${QDRANT_API_KEY}
```

**Code**:
```python
from qdrant_client import QdrantClient

client = QdrantClient(
    host=qdrant_host,
    port=qdrant_port,
    api_key=os.getenv("QDRANT_API_KEY")
)
```

### Data Encryption

- [ ] **Encrypt sensitive data at rest**
  - [ ] Chat history
  - [ ] Document metadata
  - [ ] Use `cryptography` library

**Code Example**:
```python
from cryptography.fernet import Fernet

ENCRYPTION_KEY = os.getenv("ENCRYPTION_KEY")  # Store securely!
cipher = Fernet(ENCRYPTION_KEY)

# Encrypt before saving
encrypted = cipher.encrypt(json.dumps(data).encode())

# Decrypt when loading
decrypted = json.loads(cipher.decrypt(encrypted).decode())
```

### Docker Security

- [ ] **Run containers as non-root**

**Dockerfile**:
```dockerfile
FROM python:3.11-slim

# Create non-root user
RUN groupadd -r appuser && useradd -r -g appuser appuser

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .

# Switch to non-root
USER appuser

CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Input Validation

- [ ] **Validate all user inputs**
  - [ ] Chat names (no HTML/scripts)
  - [ ] Document IDs (UUID format)
  - [ ] Query parameters

**Code Example**:
```python
from pydantic import Field, field_validator

class CreateChatRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)

    @field_validator('name')
    def validate_name(cls, v):
        if any(c in v for c in ['<', '>', '"', "'", '&']):
            raise ValueError('Invalid characters in chat name')
        return v
```

### Request Size Limits

- [ ] **Limit request body size**

```python
from fastapi.middleware import Middleware
from starlette.middleware.base import BaseHTTPMiddleware

MAX_REQUEST_SIZE = 100 * 1024 * 1024  # 100MB

class RequestSizeLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        if request.headers.get("content-length"):
            content_length = int(request.headers["content-length"])
            if content_length > MAX_REQUEST_SIZE:
                raise HTTPException(status_code=413, detail="Request too large")
        return await call_next(request)

app.add_middleware(RequestSizeLimitMiddleware)
```

---

## ⚪ LOW PRIORITY (Good to have)

### Dependency Management

- [ ] **Pin dependency versions**

```txt
# requirements.txt
fastapi>=0.104.0,<1.0.0
qdrant-client>=1.7.0,<2.0.0
google-generativeai>=0.3.0,<1.0.0
```

- [ ] **Regular security audits**
  - [ ] `pip-audit` for vulnerabilities
  - [ ] Dependabot alerts on GitHub

### Monitoring & Logging

- [ ] **Structured logging**
  - [ ] JSON format for easy parsing
  - [ ] Include request IDs for tracing

- [ ] **Security event logging**
  - [ ] Failed auth attempts
  - [ ] Rate limit violations
  - [ ] Suspicious file uploads

- [ ] **Set up monitoring**
  - [ ] Prometheus + Grafana
  - [ ] Alert on anomalies

### Backup & Disaster Recovery

- [ ] **Automated backups**
  - [ ] Qdrant data daily
  - [ ] Document metadata daily
  - [ ] Test restore procedures

- [ ] **Cloud storage**
  - [ ] S3/GCS for uploaded files
  - [ ] Versioning enabled

---

## 📊 PROGRESS TRACKER

### Critical Issues
- [ ] 0/4 Authentication system
- [ ] 0/1 CORS restrictions
- [ ] 0/3 File upload validation
- [ ] 0/1 Error handling

**Status**: 0% complete (0/9 items)

### High Priority
- [ ] 0/1 Path traversal protection
- [ ] 0/1 Rate limiting
- [ ] 0/1 HTTPS/SSL
- [ ] 0/1 Security headers

**Status**: 0% complete (0/4 items)

### Medium Priority
- [ ] 0/6 Environment config, database security, encryption, Docker, input validation, request limits

**Status**: 0% complete (0/6 items)

---

## 🚀 DEPLOYMENT TIMELINE

### Week 1: Critical Fixes
- Days 1-2: Implement authentication
- Days 3-4: Fix CORS, file upload validation
- Day 5: Error handling, testing

### Week 2: High Priority
- Days 1-2: Path traversal protection
- Day 3: Rate limiting
- Days 4-5: HTTPS setup

### Week 3: Medium Priority & Testing
- Days 1-3: Database security, encryption
- Days 4-5: Full security testing

### Week 4: Hardening & Launch
- Days 1-2: Final audits
- Day 3: Staging deployment test
- Day 4: Production deployment
- Day 5: Monitoring & incident response setup

---

## ✅ SIGN-OFF CRITERIA

Before production deployment, ALL of these must be TRUE:

- [x] Authentication implemented and tested
- [x] CORS restricted to specific domains
- [x] File uploads validated (size, MIME, filename)
- [x] Error messages do not expose internals
- [x] Path traversal protections in place
- [x] Rate limiting active
- [x] HTTPS enforced
- [x] Security headers configured
- [x] No `.env` files in git history
- [x] All secrets in environment variables
- [x] Database access restricted
- [x] Full security test completed
- [x] Incident response plan documented
- [x] Backup & restore tested

**Sign-off**: _________________ Date: _________

---

## 📞 EMERGENCY CONTACTS

- **Security Lead**: [Your name/team]
- **DevOps**: [Team contact]
- **On-call**: [Rotation schedule]

**Incident Response**: If security breach detected, immediately:
1. Revoke all API keys
2. Take system offline
3. Notify security team
4. Preserve logs for forensics
5. Follow incident response playbook
