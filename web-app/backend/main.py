#!/usr/bin/env python3
"""
FastAPI Backend for University Attendance Tracking System

Complete implementation with:
- JWT authentication (1-hour expiry)
- Role-based access control (admin/faculty/student)
- 11 REST endpoint groups
- WebSocket real-time attendance feed
- Audit logging
- Rate limiting on auth endpoints
- AES-256-GCM template encryption
"""

import os
import sys
import json
import time
import logging
import psycopg2
from psycopg2 import pool
from psycopg2 import sql
import redis
import jwt
import bcrypt
import base64
import hashlib
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, List, Any, Set
from functools import wraps

from fastapi import FastAPI, HTTPException, Request, Depends, WebSocket, Query, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, JSONResponse
import uvicorn
from pydantic import BaseModel, Field
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.backends import default_backend

# Migration helper (run on existing DBs before 2027 data is inserted)
# 1) Add unique key for template sync upserts:
#    CREATE UNIQUE INDEX IF NOT EXISTS uq_device_sync_log_device_template
#    ON device_sync_log (device_id, template_id);
# 2) Add missing attendance partitions for 2027:
#    CREATE TABLE IF NOT EXISTS attendance_records_2027_01 PARTITION OF attendance_records FOR VALUES FROM ('2027-01-01') TO ('2027-02-01');
#    CREATE TABLE IF NOT EXISTS attendance_records_2027_02 PARTITION OF attendance_records FOR VALUES FROM ('2027-02-01') TO ('2027-03-01');
#    CREATE TABLE IF NOT EXISTS attendance_records_2027_03 PARTITION OF attendance_records FOR VALUES FROM ('2027-03-01') TO ('2027-04-01');
#    CREATE TABLE IF NOT EXISTS attendance_records_2027_04 PARTITION OF attendance_records FOR VALUES FROM ('2027-04-01') TO ('2027-05-01');
#    CREATE TABLE IF NOT EXISTS attendance_records_2027_05 PARTITION OF attendance_records FOR VALUES FROM ('2027-05-01') TO ('2027-06-01');
#    CREATE TABLE IF NOT EXISTS attendance_records_2027_06 PARTITION OF attendance_records FOR VALUES FROM ('2027-06-01') TO ('2027-07-01');
#    CREATE TABLE IF NOT EXISTS attendance_records_2027_07 PARTITION OF attendance_records FOR VALUES FROM ('2027-07-01') TO ('2027-08-01');
#    CREATE TABLE IF NOT EXISTS attendance_records_2027_08 PARTITION OF attendance_records FOR VALUES FROM ('2027-08-01') TO ('2027-09-01');
#    CREATE TABLE IF NOT EXISTS attendance_records_2027_09 PARTITION OF attendance_records FOR VALUES FROM ('2027-09-01') TO ('2027-10-01');
#    CREATE TABLE IF NOT EXISTS attendance_records_2027_10 PARTITION OF attendance_records FOR VALUES FROM ('2027-10-01') TO ('2027-11-01');
#    CREATE TABLE IF NOT EXISTS attendance_records_2027_11 PARTITION OF attendance_records FOR VALUES FROM ('2027-11-01') TO ('2027-12-01');
#    CREATE TABLE IF NOT EXISTS attendance_records_2027_12 PARTITION OF attendance_records FOR VALUES FROM ('2027-12-01') TO ('2028-01-01');

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] [%(name)s] %(levelname)s: %(message)s'
)
logger = logging.getLogger('FastAPI')

# Environment variables
POSTGRES_HOST = os.getenv('POSTGRES_HOST', 'localhost')
POSTGRES_PORT = int(os.getenv('POSTGRES_PORT', 5432))
POSTGRES_DB = os.getenv('POSTGRES_DB', 'attendance_db')
POSTGRES_USER = os.getenv('POSTGRES_USER', 'attendance_user')
POSTGRES_PASSWORD = os.getenv('POSTGRES_PASSWORD', 'SecurePass123!')
REDIS_HOST = os.getenv('REDIS_HOST', 'localhost')
REDIS_PORT = int(os.getenv('REDIS_PORT', 6379))
JWT_SECRET = os.getenv('JWT_SECRET', 'supersecretjwtkey_change_in_production')
JWT_EXPIRY_HOURS = int(os.getenv('JWT_EXPIRY_HOURS', 1))
AES_KEY_HEX = os.getenv('AES_KEY', '0123456789abcdef0123456789abcdef')
DEVICE_SERVICE_TOKEN = os.getenv('DEVICE_SERVICE_TOKEN', 'dev-device-token-change-me')
ALLOWED_ORIGINS_ENV = os.getenv('ALLOWED_ORIGINS', 'http://localhost:3000,http://127.0.0.1:3000,http://frontend:3000')
ALLOWED_ORIGINS = [origin.strip() for origin in ALLOWED_ORIGINS_ENV.split(',') if origin.strip()]

# Global state
db_pool = None
redis_client = None
ws_manager = None
APP_START_TIME = datetime.now(timezone.utc)


# ============================================================================
# DATABASE CONNECTION POOL
# ============================================================================

class DBPool:
    """PostgreSQL connection pool."""
    def __init__(self, minconn=2, maxconn=20):
        self.dsn = f"dbname={POSTGRES_DB} user={POSTGRES_USER} password={POSTGRES_PASSWORD} host={POSTGRES_HOST} port={POSTGRES_PORT}"
        self.pool = pool.SimpleConnectionPool(minconn, maxconn, self.dsn)

    def get_conn(self):
        return self.pool.getconn()

    def put_conn(self, conn):
        self.pool.putconn(conn)

    def close_all(self):
        self.pool.closeall()

    def get_cursor(self):
        """Context manager that auto-returns connection on exit."""
        from contextlib import contextmanager
        @contextmanager
        def _cursor():
            conn = self.get_conn()
            try:
                cur = conn.cursor()
                yield conn, cur
                conn.commit()
            except Exception:
                conn.rollback()
                raise
            finally:
                try:
                    cur.close()
                except Exception:
                    pass
                self.put_conn(conn)
        return _cursor()


# ============================================================================
# PYDANTIC MODELS
# ============================================================================

class LoginRequest(BaseModel):
    username: str
    password: str

class LoginResponse(BaseModel):
    token: str
    user: Dict[str, Any]

class StudentCreate(BaseModel):
    student_number: str
    full_name: str
    department: Optional[str] = None
    semester: Optional[int] = None

class StudentUpdate(BaseModel):
    full_name: Optional[str] = None
    department: Optional[str] = None
    semester: Optional[int] = None

class EnrollmentRequest(BaseModel):
    student_id: str
    template_data_base64: str

class AttendanceRecord(BaseModel):
    device_id: str
    student_id: str
    classroom_id: str
    timestamp: str
    match_score: Optional[int] = None
    battery_pct: Optional[int] = None
    status: Optional[str] = 'present'
    verification_method: Optional[str] = 'fingerprint'

class AttendanceBatch(BaseModel):
    records: List[AttendanceRecord]

class AttendanceUpdateRequest(BaseModel):
    status: Optional[str] = Field(default=None)
    verification_method: Optional[str] = Field(default=None)
    match_score: Optional[int] = Field(default=None)
    timestamp: Optional[str] = Field(default=None)

class ManualAttendanceRequest(BaseModel):
    student_id: str
    classroom_id: str
    timestamp: str
    device_id: Optional[str] = 'MANUAL'
    status: Optional[str] = 'manual'

class TemplateSyncAckRequest(BaseModel):
    device_id: str
    template_id: str
    sync_version: int

class GatewayHeartbeat(BaseModel):
    gateway_id: str
    queue_depth: int
    uptime_seconds: int
    records_forwarded_total: int
    last_forward_at: Optional[str]
    backend_reachable: bool
    connected_devices: List[str]

class CreateUserRequest(BaseModel):
    role: str
    full_name: str
    email: str
    username: str
    password: str
    student_number: Optional[str] = None
    department: Optional[str] = None
    semester: Optional[int] = None
    employee_id: Optional[str] = None

class UserCredentialResponse(BaseModel):
    user_id: str
    username: str
    email: str
    role: str
    temporary_password: str
    login_url: str
    message: str

class ResetPasswordRequest(BaseModel):
    new_password: str


# ============================================================================
# JWT & AUTH UTILITIES
# ============================================================================

def hash_password(password: str) -> str:
    """Hash password with bcrypt."""
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

def verify_password(password: str, hash_val: str) -> bool:
    """Verify password against bcrypt hash."""
    return bcrypt.checkpw(password.encode(), hash_val.encode())

def create_jwt(user_id: str, username: str, role: str) -> str:
    """Create JWT token (1-hour expiry)."""
    payload = {
        'user_id': user_id,
        'username': username,
        'role': role,
        'exp': datetime.now(timezone.utc) + timedelta(hours=JWT_EXPIRY_HOURS),
        'iat': datetime.now(timezone.utc)
    }
    return jwt.encode(payload, JWT_SECRET, algorithm='HS256')

def verify_jwt(token: str) -> Optional[Dict]:
    """Verify and decode JWT token."""
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=['HS256'])
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None

def extract_token(request: Request) -> Optional[str]:
    """Extract JWT token from Authorization header."""
    auth_header = request.headers.get('authorization')
    if not auth_header:
        return None
    try:
        scheme, token = auth_header.split()
        if scheme.lower() != 'bearer':
            return None
        return token
    except:
        return None

def get_current_user(request: Request) -> Optional[Dict]:
    """Dependency to extract and verify current user from JWT."""
    token = extract_token(request)
    if not token:
        return None
    
    # Check blacklist
    if redis_client and redis_client.exists(f"jwt_blacklist:{token}"):
        return None
    
    decoded = verify_jwt(token)
    return decoded

def require_auth(func):
    """Decorator: require valid JWT."""
    @wraps(func)
    async def wrapper(request: Request, *args, **kwargs):
        user = get_current_user(request)
        if not user:
            raise HTTPException(status_code=401, detail="Unauthorized")
        kwargs['current_user'] = user
        return await func(request, *args, **kwargs)
    return wrapper

def require_role(*allowed_roles):
    """Decorator: require specific role."""
    def decorator(func):
        @wraps(func)
        async def wrapper(request: Request, *args, **kwargs):
            user = get_current_user(request)
            if not user or user.get('role') not in allowed_roles:
                raise HTTPException(status_code=403, detail="Forbidden")
            kwargs['current_user'] = user
            return await func(request, *args, **kwargs)
        return wrapper
    return decorator

def rate_limit_key(request: Request, endpoint: str) -> bool:
    """Check rate limit (100 req/min per IP)."""
    if not redis_client:
        return True
    
    ip = request.client.host if request.client else '0.0.0.0'
    key = f"ratelimit:{ip}:{endpoint}"
    
    count = redis_client.incr(key)
    if count == 1:
        redis_client.expire(key, 60)
    
    return count <= 100

def get_user_ip(request: Request) -> str:
    """Get client IP address."""
    ip = request.client.host if request.client else None
    return ip if ip else None

def get_user_agent(request: Request) -> str:
    """Get User-Agent header."""
    return request.headers.get('user-agent', '')

def require_device_token(request: Request):
    """Validate X-Device-Token for gateway/device-facing APIs."""
    token = request.headers.get('x-device-token')
    if not token or token != DEVICE_SERVICE_TOKEN:
        raise HTTPException(status_code=401, detail="Invalid device token")

def invalidate_user_sessions(user_id: str):
    """Blacklist all known active JWTs for a given user."""
    if not redis_client:
        return
    try:
        keys = redis_client.keys(f"jwt_user:{user_id}:*")
        ttl_seconds = max(60, int(JWT_EXPIRY_HOURS * 3600))
        for key in keys:
            token = key.split(':', 3)[-1]
            redis_client.setex(f"jwt_blacklist:{token}", ttl_seconds, '1')
            redis_client.delete(key)
    except Exception as e:
        logger.error(f"Session invalidation error: {e}")


# ============================================================================
# CRYPTO UTILITIES
# ============================================================================

def derive_aes_key(hex_key: str) -> bytes:
    """Convert hex string AES key to bytes."""
    if len(hex_key) == 64:
        return bytes.fromhex(hex_key)
    h = hashes.Hash(hashes.SHA256(), backend=default_backend())
    h.update(hex_key.encode())
    return h.finalize()

def encrypt_aes_gcm(plaintext: bytes, key: bytes) -> tuple:
    """Encrypt with AES-256-GCM. Returns (ciphertext, nonce, tag)."""
    cipher = AESGCM(key)
    nonce = os.urandom(12)
    ciphertext = cipher.encrypt(nonce, plaintext, None)
    return ciphertext[:-16], nonce, ciphertext[-16:]

def decrypt_aes_gcm(ciphertext: bytes, nonce: bytes, tag: bytes, key: bytes) -> bytes:
    """Decrypt AES-256-GCM."""
    cipher = AESGCM(key)
    return cipher.decrypt(nonce, ciphertext + tag, None)


# ============================================================================
# FASTAPI APP SETUP
# ============================================================================

app = FastAPI(title="Attendance API", version="1.0.0")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Startup/Shutdown
@app.on_event("startup")
async def startup():
    global db_pool, redis_client, ws_manager
    logger.info("Starting FastAPI app...")
    
    # Init DB pool
    try:
        db_pool = DBPool(minconn=2, maxconn=20)
        conn = db_pool.get_conn()
        cur = conn.cursor()
        cur.execute("SELECT 1")
        cur.execute(
            """CREATE UNIQUE INDEX IF NOT EXISTS uq_device_sync_log_device_template
               ON device_sync_log (device_id, template_id)"""
        )
        conn.commit()
        db_pool.put_conn(conn)
        logger.info("✓ Database connected")
    except Exception as e:
        logger.error(f"Database connection failed: {e}")
        sys.exit(1)
    
    # Init Redis
    try:
        redis_client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)
        redis_client.ping()
        logger.info("✓ Redis connected")
    except Exception as e:
        logger.warning(f"Redis connection failed: {e} (continuing without caching)")
    
    ws_manager = WebSocketManager()
    logger.info("✓ WebSocket manager initialized")

@app.on_event("shutdown")
async def shutdown():
    global db_pool
    if db_pool:
        db_pool.close_all()
    logger.info("✓ App shutdown complete")


# ============================================================================
# WEBSOCKET MANAGER
# ============================================================================

class WebSocketManager:
    """Manage WebSocket connections for real-time attendance."""
    
    def __init__(self):
        self.active_connections: Dict[str, Dict] = {}  # {client_id: {ws, user, role, faculty_id}}
        self.client_counter = 0
    
    async def connect(self, websocket: WebSocket, user: Dict):
        await websocket.accept()
        client_id = f"client_{self.client_counter}"
        self.client_counter += 1
        
        self.active_connections[client_id] = {
            'ws': websocket,
            'user_id': user['user_id'],
            'role': user['role'],
            'faculty_id': user.get('faculty_id')
        }
        logger.info(f"[WS] Client connected: {client_id} ({user['role']})")
        return client_id
    
    def disconnect(self, client_id: str):
        if client_id in self.active_connections:
            del self.active_connections[client_id]
            logger.info(f"[WS] Client disconnected: {client_id}")
    
    async def broadcast_attendance(self, event: Dict):
        """Broadcast attendance event to relevant clients."""
        disconnected = []
        
        for client_id, conn_info in self.active_connections.items():
            try:
                ws = conn_info['ws']
                role = conn_info['role']
                faculty_id = conn_info.get('faculty_id')
                
                # Filter by role
                should_send = False
                if role == 'admin':
                    should_send = True
                elif role == 'faculty':
                    # Only send if event's course belongs to this faculty
                    # (would need to lookup in DB, for now send all)
                    should_send = True
                elif role == 'student':
                    should_send = False  # Students don't receive broadcast
                
                if should_send:
                    await ws.send_json(event)
            except Exception as e:
                logger.warning(f"[WS] Failed to send to {client_id}: {e}")
                disconnected.append(client_id)
        
        for client_id in disconnected:
            self.disconnect(client_id)


# ============================================================================
# ENDPOINTS: AUTHENTICATION
# ============================================================================

@app.get("/api/health")
async def health():
    """Health check endpoint with service connectivity and uptime."""
    db_connected = False
    redis_connected = False

    try:
        with db_pool.get_cursor() as (_, cur):
            cur.execute("SELECT 1")
            db_connected = cur.fetchone()[0] == 1
    except Exception:
        db_connected = False

    try:
        if redis_client:
            redis_client.ping()
            redis_connected = True
    except Exception:
        redis_connected = False

    uptime_seconds = int((datetime.now(timezone.utc) - APP_START_TIME).total_seconds())

    return {
        "status": "ok" if db_connected else "degraded",
        "db_connected": db_connected,
        "redis_connected": redis_connected,
        "uptime_seconds": uptime_seconds
    }

@app.get("/api/health/db")
async def health_db():
    """Run database verification queries for instructor health checks."""
    try:
        with db_pool.get_cursor() as (_, cur):
            cur.execute("SELECT COUNT(*) FROM users")
            total_users = cur.fetchone()[0]

            cur.execute("SELECT COUNT(*) FROM attendance_records")
            total_records = cur.fetchone()[0]

            cur.execute(
                """SELECT table_name
                   FROM information_schema.tables
                   WHERE table_schema = 'public'
                   ORDER BY table_name"""
            )
            tables = [row[0] for row in cur.fetchall()]

        return {
            "status": "ok",
            "checks": {
                "total_users": total_users,
                "total_records": total_records,
                "tables": tables
            }
        }
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        return JSONResponse(status_code=503, content={"status": "error", "detail": str(e)})

@app.get("/api/admin/db-status")
async def admin_db_status(request: Request):
    """Return detailed DB diagnostics for administrators."""
    user = get_current_user(request)
    if not user or user.get('role') != 'admin':
        raise HTTPException(status_code=403, detail="Admin only")

    try:
        with db_pool.get_cursor() as (_, cur):
            cur.execute(
                """SELECT table_name
                   FROM information_schema.tables
                   WHERE table_schema = 'public'
                   ORDER BY table_name"""
            )
            table_names = [row[0] for row in cur.fetchall()]

            table_counts = {}
            for table_name in table_names:
                if not table_name.replace('_', '').isalnum():
                    continue
                cur.execute(sql.SQL("SELECT COUNT(*) FROM {}") .format(sql.Identifier(table_name)))
                table_counts[table_name] = cur.fetchone()[0]

            cur.execute(
                """SELECT inhrelid::regclass::text
                   FROM pg_inherits
                   WHERE inhparent = 'attendance_records'::regclass
                   ORDER BY inhrelid::regclass::text"""
            )
            partitions = [row[0] for row in cur.fetchall()]

            cur.execute("SELECT version()")
            postgres_version = cur.fetchone()[0]

        redis_ping_ms = None
        if redis_client:
            start = time.perf_counter()
            redis_client.ping()
            redis_ping_ms = round((time.perf_counter() - start) * 1000, 3)

        return {
            "status": "ok",
            "table_counts": table_counts,
            "attendance_partitions": partitions,
            "redis_ping_ms": redis_ping_ms,
            "postgres_version": postgres_version
        }
    except Exception as e:
        logger.error(f"Admin DB status error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.post("/api/auth/login", response_model=LoginResponse)
async def login(request: Request, login_req: LoginRequest):
    """Login endpoint. Returns JWT token."""

    if not rate_limit_key(request, "login"):
        raise HTTPException(status_code=429, detail="Too many login attempts")

    if not login_req.username or not login_req.password:
        raise HTTPException(status_code=400, detail="Username and password required")

    try:
        with db_pool.get_cursor() as (conn, cur):
            cur.execute(
                "SELECT user_id, username, email, password_hash, role, is_active FROM users WHERE username = %s",
                (login_req.username,)
            )
            row = cur.fetchone()

        if not row:
            log_audit(None, "login_failed", "user", login_req.username, get_user_ip(request), get_user_agent(request))
            raise HTTPException(status_code=401, detail="Invalid credentials")

        user_id, username, email, password_hash, role, is_active = row

        if not is_active:
            raise HTTPException(status_code=401, detail="User account is inactive")

        if not verify_password(login_req.password, password_hash):
            log_audit(str(user_id), "login_failed", "user", str(user_id), get_user_ip(request), get_user_agent(request))
            raise HTTPException(status_code=401, detail="Invalid credentials")

        token = create_jwt(str(user_id), username, role)
        if redis_client:
            redis_client.setex(f"jwt_user:{user_id}:{token}", int(JWT_EXPIRY_HOURS * 3600), '1')
        log_audit(str(user_id), "login", None, None, get_user_ip(request), get_user_agent(request))

        return LoginResponse(
            token=token,
            user={
                'user_id': str(user_id),
                'username': username,
                'email': email,
                'role': role
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.post("/api/auth/logout")
async def logout(request: Request):
    """Logout endpoint. Blacklist JWT."""
    user = get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    token = extract_token(request)
    if token and redis_client:
        # Blacklist token with remaining expiry
        exp_time = user.get('exp', 0)
        now = datetime.now(timezone.utc).timestamp()
        remaining = max(0, int(exp_time - now))
        if remaining > 0:
            redis_client.setex(f"jwt_blacklist:{token}", remaining, '1')
        redis_client.delete(f"jwt_user:{user['user_id']}:{token}")
    
    log_audit(user['user_id'], "logout", None, None, get_user_ip(request), get_user_agent(request))
    return {"message": "Logged out successfully"}

@app.get("/api/auth/me")
async def get_me(request: Request):
    """Get current user info."""
    user = get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    try:
        conn = db_pool.get_conn()
        cur = conn.cursor()
        
        cur.execute(
            "SELECT username, email, role FROM users WHERE user_id = %s",
            (user['user_id'],)
        )
        row = cur.fetchone()
        cur.close()
        db_pool.put_conn(conn)
        
        if not row:
            raise HTTPException(status_code=404, detail="User not found")
        
        username, email, role = row
        return {
            'user_id': user['user_id'],
            'username': username,
            'email': email,
            'role': role
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get user error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


# ============================================================================
# ENDPOINTS: USER MANAGEMENT (ADMIN + SELF PROFILE)
# ============================================================================

@app.post("/api/admin/users/create", response_model=UserCredentialResponse)
async def admin_create_user(request: Request, payload: CreateUserRequest):
    """Create a new student or faculty user and return one-time credentials."""
    user = get_current_user(request)
    if not user or user.get('role') != 'admin':
        raise HTTPException(status_code=403, detail="Admin only")

    if payload.role not in ('student', 'faculty'):
        raise HTTPException(status_code=400, detail="Role must be student or faculty")

    if payload.role == 'student' and not payload.student_number:
        raise HTTPException(status_code=400, detail="student_number is required for student role")

    if payload.semester is not None and (payload.semester < 1 or payload.semester > 8):
        raise HTTPException(status_code=400, detail="semester must be between 1 and 8")

    frontend_url = os.getenv('FRONTEND_URL', 'http://localhost:3000')

    try:
        with db_pool.get_cursor() as (_, cur):
            cur.execute("SELECT 1 FROM users WHERE username = %s", (payload.username,))
            if cur.fetchone():
                raise HTTPException(status_code=409, detail="Username already exists")

            cur.execute("SELECT 1 FROM users WHERE email = %s", (payload.email,))
            if cur.fetchone():
                raise HTTPException(status_code=409, detail="Email already exists")

            hashed = hash_password(payload.password)
            cur.execute(
                """INSERT INTO users (username, email, password_hash, role, is_active)
                   VALUES (%s, %s, %s, %s, TRUE)
                   RETURNING user_id""",
                (payload.username, payload.email, hashed, payload.role)
            )
            new_user_id = cur.fetchone()[0]

            if payload.role == 'student':
                cur.execute(
                    """INSERT INTO students
                       (user_id, student_number, full_name, department, semester, is_active)
                       VALUES (%s, %s, %s, %s, %s, TRUE)
                       RETURNING student_id""",
                    (new_user_id, payload.student_number, payload.full_name, payload.department, payload.semester)
                )
                _ = cur.fetchone()[0]

        log_audit(user['user_id'], "create_user", "user", str(new_user_id), get_user_ip(request), get_user_agent(request))

        return UserCredentialResponse(
            user_id=str(new_user_id),
            username=payload.username,
            email=payload.email,
            role=payload.role,
            temporary_password=payload.password,
            login_url=frontend_url,
            message="User created successfully. Share these credentials securely."
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Admin create user error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/api/admin/users")
async def admin_list_users(
    request: Request,
    role: Optional[str] = None,
    is_active: Optional[bool] = None
):
    """List users with optional role and active-state filters."""
    user = get_current_user(request)
    if not user or user.get('role') != 'admin':
        raise HTTPException(status_code=403, detail="Admin only")

    try:
        with db_pool.get_cursor() as (_, cur):
            conditions = []
            params: List[Any] = []
            if role in ('admin', 'faculty', 'student'):
                conditions.append("u.role = %s")
                params.append(role)
            if is_active is not None:
                conditions.append("u.is_active = %s")
                params.append(is_active)

            where_clause = "WHERE " + " AND ".join(conditions) if conditions else ""

            cur.execute(
                f"""SELECT u.user_id, u.username, u.email, u.role, u.is_active, u.created_at,
                           s.student_id, s.student_number, s.full_name, s.department, s.semester,
                           s.fp_enrolled
                    FROM users u
                    LEFT JOIN students s ON s.user_id = u.user_id
                    {where_clause}
                    ORDER BY u.created_at DESC""",
                params
            )
            rows = cur.fetchall()

            user_ids = [str(row[0]) for row in rows if row[3] == 'faculty']
            faculty_courses: Dict[str, List[Dict[str, str]]] = {}
            if user_ids:
                cur.execute(
                    """SELECT course_id, course_code, course_name, faculty_id
                       FROM courses
                       WHERE faculty_id = ANY(%s::uuid[])
                       ORDER BY course_code""",
                    (user_ids,)
                )
                for c_row in cur.fetchall():
                    fid = str(c_row[3])
                    faculty_courses.setdefault(fid, []).append(
                        {
                            'course_id': str(c_row[0]),
                            'course_code': c_row[1],
                            'course_name': c_row[2]
                        }
                    )

        results = []
        for row in rows:
            linked_info: Dict[str, Any] = {}
            if row[3] == 'student':
                linked_info = {
                    'student_id': str(row[6]) if row[6] else None,
                    'student_number': row[7],
                    'full_name': row[8],
                    'department': row[9],
                    'semester': row[10],
                    'fp_enrolled': row[11]
                }
            elif row[3] == 'faculty':
                linked_info = {
                    'employee_id': None,
                    'courses': faculty_courses.get(str(row[0]), [])
                }

            results.append(
                {
                    'user_id': str(row[0]),
                    'username': row[1],
                    'email': row[2],
                    'role': row[3],
                    'is_active': row[4],
                    'created_at': str(row[5]),
                    'linked_info': linked_info
                }
            )

        return results
    except Exception as e:
        logger.error(f"Admin list users error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.put("/api/admin/users/{user_id}/reset-password")
async def admin_reset_password(request: Request, user_id: str, payload: ResetPasswordRequest):
    """Reset a user's password and invalidate active sessions."""
    user = get_current_user(request)
    if not user or user.get('role') != 'admin':
        raise HTTPException(status_code=403, detail="Admin only")

    if len(payload.new_password.strip()) < 6:
        raise HTTPException(status_code=400, detail="new_password must be at least 6 characters")

    try:
        with db_pool.get_cursor() as (_, cur):
            cur.execute("SELECT user_id FROM users WHERE user_id = %s::uuid", (user_id,))
            if not cur.fetchone():
                raise HTTPException(status_code=404, detail="User not found")

            cur.execute(
                "UPDATE users SET password_hash = %s WHERE user_id = %s::uuid",
                (hash_password(payload.new_password), user_id)
            )

        invalidate_user_sessions(user_id)
        log_audit(user['user_id'], "reset_password", "user", user_id, get_user_ip(request), get_user_agent(request))
        return {'message': 'Password reset successful'}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Admin reset password error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.put("/api/admin/users/{user_id}/toggle-active")
async def admin_toggle_active(request: Request, user_id: str):
    """Toggle a user's active status and invalidate sessions when deactivated."""
    user = get_current_user(request)
    if not user or user.get('role') != 'admin':
        raise HTTPException(status_code=403, detail="Admin only")

    if user_id == user.get('user_id'):
        raise HTTPException(status_code=400, detail="Cannot deactivate your own account")

    try:
        with db_pool.get_cursor() as (_, cur):
            cur.execute("SELECT is_active FROM users WHERE user_id = %s::uuid", (user_id,))
            row = cur.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="User not found")

            new_state = not row[0]
            cur.execute("UPDATE users SET is_active = %s WHERE user_id = %s::uuid", (new_state, user_id))

        if not new_state:
            invalidate_user_sessions(user_id)

        action = "activate_user" if new_state else "deactivate_user"
        log_audit(user['user_id'], action, "user", user_id, get_user_ip(request), get_user_agent(request))
        return {'message': 'User status updated', 'is_active': new_state}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Admin toggle active error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/api/users/me/profile")
async def get_my_profile(request: Request):
    """Return role-aware profile details for the authenticated user."""
    user = get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Unauthorized")

    try:
        with db_pool.get_cursor() as (_, cur):
            cur.execute(
                """SELECT user_id, username, email, role, is_active, created_at
                   FROM users WHERE user_id = %s::uuid""",
                (user['user_id'],)
            )
            base = cur.fetchone()
            if not base:
                raise HTTPException(status_code=404, detail="User not found")

            response = {
                'user_id': str(base[0]),
                'username': base[1],
                'email': base[2],
                'role': base[3],
                'is_active': base[4],
                'created_at': str(base[5])
            }

            if base[3] == 'student':
                cur.execute(
                    """SELECT student_id, student_number, full_name, department, semester, fp_enrolled
                       FROM students WHERE user_id = %s::uuid""",
                    (user['user_id'],)
                )
                s_row = cur.fetchone()
                if s_row:
                    response.update(
                        {
                            'student_id': str(s_row[0]),
                            'student_number': s_row[1],
                            'full_name': s_row[2],
                            'department': s_row[3],
                            'semester': s_row[4],
                            'fp_enrolled': s_row[5]
                        }
                    )
            elif base[3] == 'faculty':
                cur.execute(
                    """SELECT course_id, course_code, course_name
                       FROM courses
                       WHERE faculty_id = %s::uuid AND is_active = TRUE
                       ORDER BY course_code""",
                    (user['user_id'],)
                )
                response['employee_id'] = None
                response['courses'] = [
                    {
                        'course_id': str(row[0]),
                        'course_code': row[1],
                        'course_name': row[2]
                    }
                    for row in cur.fetchall()
                ]
            else:
                response['full_name'] = base[1]

        return response
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get profile error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


# ============================================================================
# ENDPOINTS: STUDENTS (ADMIN ONLY)
# ============================================================================

@app.get("/api/students")
async def list_students(request: Request, offset: int = 0, limit: int = 50):
    """List all students (admin only)."""
    user = get_current_user(request)
    if not user or user.get('role') != 'admin':
        raise HTTPException(status_code=403, detail="Admin only")
    
    try:
        conn = db_pool.get_conn()
        cur = conn.cursor()
        
        cur.execute(
            """SELECT s.student_id, s.student_number, s.full_name, s.department, s.semester,
                      s.fp_enrolled, s.is_active
               FROM students s
               ORDER BY s.student_number
               LIMIT %s OFFSET %s""",
            (limit, offset)
        )
        rows = cur.fetchall()
        cur.close()
        db_pool.put_conn(conn)
        
        return [
            {
                'student_id': str(row[0]),
                'student_number': row[1],
                'full_name': row[2],
                'department': row[3],
                'semester': row[4],
                'fp_enrolled': row[5],
                'is_active': row[6]
            }
            for row in rows
        ]
    
    except Exception as e:
        logger.error(f"List students error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/api/students/enrolled")
async def list_enrolled_students(request: Request):
    """List enrolled students (device access)."""
    try:
        conn = db_pool.get_conn()
        cur = conn.cursor()
        
        cur.execute(
            """SELECT s.student_id, s.student_number, s.full_name
               FROM students s
               WHERE s.fp_enrolled = TRUE AND s.is_active = TRUE
               ORDER BY s.student_number"""
        )
        rows = cur.fetchall()
        cur.close()
        db_pool.put_conn(conn)
        
        return [
            {
                'student_id': str(row[0]),
                'student_number': row[1],
                'full_name': row[2]
            }
            for row in rows
        ]
    
    except Exception as e:
        logger.error(f"List enrolled error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.post("/api/students")
async def create_student(request: Request, student: StudentCreate):
    """Create student (admin only)."""
    user = get_current_user(request)
    if not user or user.get('role') != 'admin':
        raise HTTPException(status_code=403, detail="Admin only")
    
    try:
        # Hash default password: same as username
        password_hash = hash_password(student.student_number[-4:])  # Last 4 digits of student number
        
        conn = db_pool.get_conn()
        cur = conn.cursor()
        
        # Create user account
        cur.execute(
            """INSERT INTO users (username, email, password_hash, role, is_active)
               VALUES (%s, %s, %s, 'student', TRUE)
               RETURNING user_id""",
            (f"student_{student.student_number}", f"{student.student_number}@university.edu", password_hash)
        )
        user_id = cur.fetchone()[0]
        
        # Create student record
        cur.execute(
            """INSERT INTO students (user_id, student_number, full_name, department, semester, is_active)
               VALUES (%s, %s, %s, %s, %s, TRUE)
               RETURNING student_id""",
            (user_id, student.student_number, student.full_name, student.department, student.semester)
        )
        student_id = cur.fetchone()[0]
        
        conn.commit()
        cur.close()
        db_pool.put_conn(conn)
        
        log_audit(user['user_id'], "create_student", "student", str(student_id), get_user_ip(request), get_user_agent(request))
        
        return {'student_id': str(student_id), 'message': 'Student created'}
    
    except Exception as e:
        logger.error(f"Create student error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.put("/api/students/{student_id}")
async def update_student(request: Request, student_id: str, update: StudentUpdate):
    """Update student (admin only)."""
    user = get_current_user(request)
    if not user or user.get('role') != 'admin':
        raise HTTPException(status_code=403, detail="Admin only")
    
    try:
        conn = db_pool.get_conn()
        cur = conn.cursor()
        
        updates = []
        params = []
        if update.full_name:
            updates.append("full_name = %s")
            params.append(update.full_name)
        if update.department:
            updates.append("department = %s")
            params.append(update.department)
        if update.semester:
            updates.append("semester = %s")
            params.append(update.semester)
        
        if updates:
            params.append(student_id)
            cur.execute(
                f"UPDATE students SET {', '.join(updates)} WHERE student_id = %s",
                params
            )
            conn.commit()
        
        cur.close()
        db_pool.put_conn(conn)
        
        log_audit(user['user_id'], "update_student", "student", student_id, get_user_ip(request), get_user_agent(request))
        
        return {'message': 'Student updated'}
    
    except Exception as e:
        logger.error(f"Update student error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.delete("/api/students/{student_id}")
async def delete_student(request: Request, student_id: str):
    """Soft-delete student (admin only)."""
    user = get_current_user(request)
    if not user or user.get('role') != 'admin':
        raise HTTPException(status_code=403, detail="Admin only")
    
    try:
        conn = db_pool.get_conn()
        cur = conn.cursor()
        
        cur.execute("UPDATE students SET is_active = FALSE WHERE student_id = %s", (student_id,))
        conn.commit()
        cur.close()
        db_pool.put_conn(conn)
        
        log_audit(user['user_id'], "delete_student", "student", student_id, get_user_ip(request), get_user_agent(request))
        
        return {'message': 'Student deleted'}
    
    except Exception as e:
        logger.error(f"Delete student error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


# ============================================================================
# ENDPOINTS: FINGERPRINT ENROLLMENT (ADMIN ONLY)
# ============================================================================

@app.post("/api/enrollment/enroll")
async def enroll_fingerprint(request: Request, enrollment: EnrollmentRequest):
    """Enroll fingerprint for student (admin only)."""
    user = get_current_user(request)
    if not user or user.get('role') != 'admin':
        raise HTTPException(status_code=403, detail="Admin only")
    
    conn = None
    cur = None
    
    try:
        # Validate student_id format (UUID)
        try:
            from uuid import UUID
            UUID(enrollment.student_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid student_id format")
        
        # Decode template_data from base64
        try:
            template_bytes = base64.b64decode(enrollment.template_data_base64)
        except:
            raise HTTPException(status_code=400, detail="Invalid base64 template data")
        
        # Encrypt with AES-256-GCM
        aes_key = derive_aes_key(AES_KEY_HEX)
        template_hash = hashlib.sha256(template_bytes).hexdigest()
        ciphertext, nonce, tag = encrypt_aes_gcm(template_bytes, aes_key)
        
        conn = db_pool.get_conn()
        cur = conn.cursor()
        
        # Check if student exists
        cur.execute(
            "SELECT student_id FROM students WHERE student_id = %s AND is_active = TRUE",
            (enrollment.student_id,)
        )
        if not cur.fetchone():
            raise HTTPException(status_code=404, detail="Student not found")
        
        # Verify enrolled_by user exists (handle JWT token with invalid user_id)
        enrolled_by_user_id = None
        if user.get('user_id'):
            cur.execute(
                "SELECT user_id FROM users WHERE user_id = %s",
                (user['user_id'],)
            )
            if cur.fetchone():
                enrolled_by_user_id = user['user_id']
        
        # Auto-assign next available device_slot
        cur.execute(
            "SELECT COALESCE(MAX(device_slot), -1) + 1 FROM fingerprint_templates WHERE is_active = TRUE"
        )
        device_slot = cur.fetchone()[0]
        
        # Create fingerprint template
        cur.execute(
            """INSERT INTO fingerprint_templates 
               (student_id, template_data, template_hash, device_slot, enrolled_by, sync_version, is_active)
               VALUES (%s, %s, %s, %s, %s, 1, TRUE)
               RETURNING template_id""",
            (enrollment.student_id, ciphertext, template_hash, device_slot, enrolled_by_user_id)
        )
        template_id = cur.fetchone()[0]
        
        # Mark student as enrolled
        cur.execute(
            "UPDATE students SET fp_enrolled = TRUE, fp_enrolled_at = NOW(), fp_enrolled_by = %s WHERE student_id = %s",
            (enrolled_by_user_id, enrollment.student_id)
        )
        
        conn.commit()
        
        # Only log audit if user_id is valid
        if enrolled_by_user_id:
            log_audit(enrolled_by_user_id, "enroll_fingerprint", "student", enrollment.student_id, get_user_ip(request), get_user_agent(request))
        
        return {'template_id': str(template_id), 'message': 'Fingerprint enrolled'}
    
    except HTTPException:
        raise
    except psycopg2.errors.UniqueViolation:
        logger.error(f"Device slot constraint violation during enrollment")
        raise HTTPException(status_code=409, detail="Device slot already assigned")
    except psycopg2.errors.ForeignKeyViolation:
        logger.error(f"Foreign key violation during enrollment")
        raise HTTPException(status_code=404, detail="Student not found")
    except Exception as e:
        logger.error(f"Enrollment error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
    finally:
        # Ensure connection cleanup
        if cur:
            try:
                cur.close()
            except:
                pass
        if conn:
            try:
                db_pool.put_conn(conn)
            except:
                pass

@app.delete("/api/enrollment/revoke/{student_id}")
async def revoke_enrollment(request: Request, student_id: str):
    """Revoke fingerprint enrollment (admin only)."""
    user = get_current_user(request)
    if not user or user.get('role') != 'admin':
        raise HTTPException(status_code=403, detail="Admin only")
    
    try:
        conn = db_pool.get_conn()
        cur = conn.cursor()
        
        cur.execute("UPDATE fingerprint_templates SET is_active = FALSE WHERE student_id = %s", (student_id,))
        cur.execute("UPDATE students SET fp_enrolled = FALSE WHERE student_id = %s", (student_id,))
        
        conn.commit()
        cur.close()
        db_pool.put_conn(conn)
        
        log_audit(user['user_id'], "revoke_enrollment", "student", student_id, get_user_ip(request), get_user_agent(request))
        
        return {'message': 'Enrollment revoked'}
    
    except Exception as e:
        logger.error(f"Revoke error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/api/enrollment/status/{student_id}")
async def get_enrollment_status(request: Request, student_id: str):
    """Get enrollment status for student."""
    try:
        conn = db_pool.get_conn()
        cur = conn.cursor()

        cur.execute(
            """SELECT s.fp_enrolled, s.fp_enrolled_at
               FROM students s WHERE s.student_id = %s""",
            (student_id,)
        )
        student_row = cur.fetchone()
        resolved_student_id = student_id

        # Compatibility path: frontend may send user_id instead of student_id.
        if not student_row:
            cur.execute(
                """SELECT s.student_id, s.fp_enrolled, s.fp_enrolled_at
                   FROM students s WHERE s.user_id = %s::uuid""",
                (student_id,)
            )
            mapped_row = cur.fetchone()
            if not mapped_row:
                cur.close()
                db_pool.put_conn(conn)
                raise HTTPException(status_code=404, detail="Student not found")
            resolved_student_id = str(mapped_row[0])
            student_row = (mapped_row[1], mapped_row[2])

        fp_enrolled, fp_enrolled_at = student_row

        # Get device sync status
        cur.execute(
            """SELECT dsl.device_id, dsl.sync_version, dsl.sync_status, dsl.synced_at
               FROM device_sync_log dsl
               WHERE dsl.template_id IN (SELECT template_id FROM fingerprint_templates WHERE student_id = %s)
               ORDER BY dsl.device_id""",
            (resolved_student_id,)
        )
        sync_rows = cur.fetchall()
        cur.close()
        db_pool.put_conn(conn)

        return {
            'student_id': resolved_student_id,
            'fp_enrolled': fp_enrolled,
            'enrolled_at': str(fp_enrolled_at) if fp_enrolled_at else None,
            'sync_status_per_device': [
                {
                    'device_id': row[0],
                    'sync_version': row[1],
                    'sync_status': row[2],
                    'synced_at': str(row[3]) if row[3] else None
                }
                for row in sync_rows
            ]
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Enrollment status error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


# ============================================================================
# ENDPOINTS: FINGERPRINT TEMPLATES
# ============================================================================

@app.get("/api/templates/pending-sync")
async def get_pending_templates(request: Request):
    """Get templates pending sync to devices (gateway access)."""
    require_device_token(request)
    try:
        conn = db_pool.get_conn()
        cur = conn.cursor()
        
        # Get templates newer than last synced version per device
        cur.execute(
            """SELECT ft.template_id, ft.student_id, ft.sync_version,
                      COALESCE(cl.device_id, 'UNASSIGNED') as device_id,
                      ft.template_data
               FROM fingerprint_templates ft
               LEFT JOIN students s ON s.student_id = ft.student_id
               LEFT JOIN class_schedule cs ON cs.course_id IN (
                   SELECT ce.course_id FROM course_enrollments ce WHERE ce.student_id = s.student_id
               )
               LEFT JOIN classrooms cl ON cl.classroom_id = cs.classroom_id
               WHERE ft.is_active = TRUE
               AND ft.sync_version > COALESCE(
                   (SELECT MAX(sync_version)
                      FROM device_sync_log dsl
                     WHERE dsl.template_id = ft.template_id AND dsl.device_id = COALESCE(cl.device_id, 'UNASSIGNED')),
                   0
               )
               LIMIT 20"""
        )
        rows = cur.fetchall()
        cur.close()
        db_pool.put_conn(conn)
        
        return [
            {
                'template_id': str(row[0]),
                'student_id': str(row[1]),
                'sync_version': row[2],
                'device_id': row[3],
                'template_data': base64.b64encode(row[4]).decode()
            }
            for row in rows
        ]
    
    except Exception as e:
        logger.error(f"Pending templates error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/api/templates/device/{device_id}")
async def get_device_templates(request: Request, device_id: str):
    """Get templates assigned to a specific device."""
    try:
        conn = db_pool.get_conn()
        cur = conn.cursor()
        
        cur.execute(
            """SELECT ft.template_id, ft.student_id, ft.device_slot
               FROM fingerprint_templates ft
               WHERE ft.is_active = TRUE
               ORDER BY ft.device_slot"""
        )
        rows = cur.fetchall()
        cur.close()
        db_pool.put_conn(conn)
        
        return {str(row[1]): row[2] for row in rows}
    
    except Exception as e:
        logger.error(f"Device templates error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.post("/api/templates/sync-ack")
async def sync_ack(request: Request, ack: TemplateSyncAckRequest):
    """Acknowledge template sync (gateway)."""
    require_device_token(request)
    try:
        conn = db_pool.get_conn()
        cur = conn.cursor()
        
        cur.execute(
            """INSERT INTO device_sync_log (device_id, template_id, sync_version, sync_status, synced_at)
               VALUES (%s, %s, %s, 'synced', NOW())
               ON CONFLICT (device_id, template_id) DO UPDATE SET
                   sync_version = EXCLUDED.sync_version,
                   sync_status = 'synced',
                   synced_at = NOW()""",
            (ack.device_id, ack.template_id, ack.sync_version)
        )
        conn.commit()
        cur.close()
        db_pool.put_conn(conn)
        
        return {'message': 'Sync acknowledged'}
    
    except Exception as e:
        logger.error(f"Sync ACK error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


# ============================================================================
# ENDPOINTS: ATTENDANCE
# ============================================================================

@app.post("/api/attendance")
async def record_attendance(request: Request, batch: AttendanceBatch):
    """Record attendance scans from gateway (accepts batch of records)."""
    from fastapi.responses import JSONResponse
    require_device_token(request)

    inserted = []
    skipped = []

    try:
        conn = db_pool.get_conn()
        cur = conn.cursor()

        for record in batch.records:
            try:
                # Dedup check (30s TTL)
                dedup_key = f"dedup:{record.student_id}:{record.device_id}:{record.timestamp[:16]}"
                if redis_client and redis_client.exists(dedup_key):
                    skipped.append(record.student_id)
                    continue

                # Validate student exists
                cur.execute(
                    "SELECT student_id FROM students WHERE student_id = %s AND is_active = TRUE",
                    (record.student_id,)
                )
                if not cur.fetchone():
                    logger.warning(f"Student not found: {record.student_id}")
                    skipped.append(record.student_id)
                    continue

                # Resolve classroom_id — accept UUID directly or look up by device_id
                classroom_uuid = None
                # Try direct UUID match first
                cur.execute(
                    "SELECT classroom_id FROM classrooms WHERE classroom_id::text = %s",
                    (record.classroom_id,)
                )
                row = cur.fetchone()
                if row:
                    classroom_uuid = row[0]
                else:
                    # Fall back: look up classroom by device_id assigned to it
                    cur.execute(
                        "SELECT classroom_id FROM classrooms WHERE device_id = %s",
                        (record.device_id,)
                    )
                    row = cur.fetchone()
                    if row:
                        classroom_uuid = row[0]

                if not classroom_uuid:
                    logger.warning(f"Classroom not found for device={record.device_id}, classroom_id={record.classroom_id}")
                    skipped.append(record.student_id)
                    continue

                # Insert record
                cur.execute(
                    """INSERT INTO attendance_records
                       (student_id, classroom_id, device_id, timestamp, match_score, battery_pct, status, verification_method)
                       VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                       RETURNING record_id""",
                    (record.student_id, classroom_uuid, record.device_id, record.timestamp,
                     record.match_score, record.battery_pct, record.status, record.verification_method)
                )
                record_id = cur.fetchone()[0]
                inserted.append(str(record_id))

                # Set dedup cache
                if redis_client:
                    redis_client.setex(dedup_key, 30, '1')

                # Broadcast WebSocket event
                if ws_manager:
                    cur.execute(
                        """SELECT s.full_name, s.student_number, cl.room_number,
                                  c.course_name
                           FROM students s
                           JOIN classrooms cl ON cl.classroom_id = %s::uuid
                           LEFT JOIN class_schedule cs ON cs.classroom_id = cl.classroom_id
                               AND cs.day_of_week = TRIM(TO_CHAR(%s::timestamptz, 'Day'))
                           LEFT JOIN courses c ON c.course_id = cs.course_id
                           WHERE s.student_id = %s::uuid
                           LIMIT 1""",
                        (str(classroom_uuid), record.timestamp, record.student_id)
                    )
                    enriched_row = cur.fetchone()
                    event = {
                        'event': 'attendance_scan',
                        'student_id': record.student_id,
                        'student_name': enriched_row[0] if enriched_row else None,
                        'student_number': enriched_row[1] if enriched_row else None,
                        'classroom_id': str(classroom_uuid),
                        'room_number': enriched_row[2] if enriched_row else None,
                        'course_name': enriched_row[3] if enriched_row else None,
                        'device_id': record.device_id,
                        'timestamp': record.timestamp
                    }
                    await ws_manager.broadcast_attendance(event)

            except Exception as e:
                logger.error(f"Error processing record for student {record.student_id}: {e}")
                skipped.append(record.student_id)
                continue

        conn.commit()
        cur.close()
        db_pool.put_conn(conn)

        log_audit(None, "record_attendance_batch", "attendance_record", None, None, None)

        return JSONResponse(
            status_code=201,
            content={'inserted': len(inserted), 'skipped': len(skipped), 'record_ids': inserted}
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Record attendance error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/api/attendance/live")
async def get_live_attendance(request: Request):
    """Get attendance from last 24 hours."""
    try:
        conn = db_pool.get_conn()
        cur = conn.cursor()
        cur.execute(
            """SELECT ar.record_id, ar.student_id, s.full_name, ar.classroom_id,
                      cl.room_number, ar.device_id, ar.timestamp, ar.status, ar.match_score
               FROM attendance_records ar
               JOIN students s ON ar.student_id = s.student_id
               JOIN classrooms cl ON ar.classroom_id = cl.classroom_id
               WHERE ar.timestamp > NOW() - INTERVAL '24 hours'
               ORDER BY ar.timestamp DESC
               LIMIT 100"""
        )
        rows = cur.fetchall()
        cur.close()
        db_pool.put_conn(conn)
        return [
            {
                'record_id': str(row[0]),
                'student_id': str(row[1]),
                'student_name': row[2],
                'classroom_id': str(row[3]),
                'room_number': row[4],
                'device_id': row[5],
                'timestamp': str(row[6]),
                'status': row[7],
                'match_score': row[8]
            }
            for row in rows
        ]
    except Exception as e:
        logger.error(f"Live attendance error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/api/attendance/history")
async def get_attendance_history(
    request: Request,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    student_id: Optional[str] = None,
    course_id: Optional[str] = None,
    limit: int = 200
):
    """Get past attendance with optional filters (admin/faculty only)."""
    user = get_current_user(request)
    if not user or user.get('role') not in ('admin', 'faculty'):
        raise HTTPException(status_code=403, detail="Admin or Faculty only")
    try:
        conn = db_pool.get_conn()
        cur = conn.cursor()

        # Build dynamic query
        conditions = []
        params = []

        if date_from:
            conditions.append("ar.timestamp >= %s::timestamptz")
            params.append(date_from)
        if date_to:
            conditions.append("ar.timestamp <= %s::timestamptz")
            params.append(date_to + ' 23:59:59')
        if student_id:
            conditions.append("ar.student_id = %s::uuid")
            params.append(student_id)

        where_clause = ("WHERE " + " AND ".join(conditions)) if conditions else ""
        params.append(limit)

        cur.execute(
            f"""SELECT ar.record_id, ar.student_id, s.full_name, s.student_number,
                       ar.classroom_id, cl.room_number, ar.device_id,
                       ar.timestamp, ar.status, ar.match_score, ar.verification_method
                FROM attendance_records ar
                JOIN students s ON ar.student_id = s.student_id
                JOIN classrooms cl ON ar.classroom_id = cl.classroom_id
                {where_clause}
                ORDER BY ar.timestamp DESC
                LIMIT %s""",
            params
        )
        rows = cur.fetchall()
        cur.close()
        db_pool.put_conn(conn)

        return [
            {
                'record_id': str(row[0]),
                'student_id': str(row[1]),
                'student_name': row[2],
                'student_number': row[3],
                'classroom_id': str(row[4]),
                'room_number': row[5],
                'device_id': row[6],
                'timestamp': str(row[7]),
                'status': row[8],
                'match_score': row[9],
                'verification_method': row[10]
            }
            for row in rows
        ]
    except Exception as e:
        logger.error(f"Attendance history error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/api/attendance/student/{student_id}")
async def get_student_attendance(request: Request, student_id: str):
    """Get attendance history for a specific student."""
    user = get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Unauthorized")

    try:
        conn = db_pool.get_conn()
        cur = conn.cursor()

        # Students can only access their own attendance records.
        resolved_student_id = student_id
        if user['role'] == 'student':
            cur.execute("SELECT student_id FROM students WHERE user_id = %s::uuid", (user['user_id'],))
            own_student_row = cur.fetchone()
            if not own_student_row:
                raise HTTPException(status_code=404, detail="Student profile not found")
            if str(own_student_row[0]) != student_id:
                raise HTTPException(status_code=403, detail="Can only view own records")
            resolved_student_id = str(own_student_row[0])

        cur.execute(
            """SELECT ar.record_id, ar.timestamp, ar.classroom_id, cl.room_number,
                      ar.status, ar.verification_method, ar.match_score
               FROM attendance_records ar
               JOIN classrooms cl ON cl.classroom_id = ar.classroom_id
               WHERE ar.student_id = %s::uuid
               ORDER BY ar.timestamp DESC
               LIMIT 100""",
            (resolved_student_id,)
        )
        rows = cur.fetchall()
        cur.close()
        db_pool.put_conn(conn)

        return [
            {
                'record_id': str(row[0]),
                'timestamp': str(row[1]),
                'classroom_id': str(row[2]),
                'room_number': row[3],
                'status': row[4],
                'verification_method': row[5],
                'match_score': row[6]
            }
            for row in rows
        ]

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Student attendance error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.delete("/api/attendance/{record_id}")
async def delete_attendance_record(request: Request, record_id: str):
    """Delete an attendance record (admin only)."""
    user = get_current_user(request)
    if not user or user.get('role') != 'admin':
        raise HTTPException(status_code=403, detail="Admin only")
    
    try:
        conn = db_pool.get_conn()
        cur = conn.cursor()
        
        # Check if record exists
        cur.execute("SELECT record_id FROM attendance_records WHERE record_id = %s", (record_id,))
        if not cur.fetchone():
            cur.close()
            db_pool.put_conn(conn)
            raise HTTPException(status_code=404, detail="Attendance record not found")
        
        # Delete the record
        cur.execute("DELETE FROM attendance_records WHERE record_id = %s", (record_id,))
        conn.commit()
        cur.close()
        db_pool.put_conn(conn)
        
        log_audit(user['user_id'], "delete_attendance", "attendance_record", record_id, get_user_ip(request), get_user_agent(request))
        
        return {'message': 'Attendance record deleted successfully'}
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Delete attendance error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.put("/api/attendance/{record_id}")
async def update_attendance_record(request: Request, record_id: str, update_data: AttendanceUpdateRequest):
    """Update an attendance record (admin only)."""
    user = get_current_user(request)
    if not user or user.get('role') != 'admin':
        raise HTTPException(status_code=403, detail="Admin only")
    
    try:
        conn = db_pool.get_conn()
        cur = conn.cursor()
        
        # Check if record exists
        cur.execute("SELECT record_id FROM attendance_records WHERE record_id = %s", (record_id,))
        if not cur.fetchone():
            cur.close()
            db_pool.put_conn(conn)
            raise HTTPException(status_code=404, detail="Attendance record not found")
        
        # Build update query dynamically based on provided fields
        allowed_fields = ['status', 'verification_method', 'match_score', 'timestamp']
        updates = []
        params = []
        
        payload = update_data.model_dump(exclude_none=True)
        for field in allowed_fields:
            if field in payload:
                updates.append(f"{field} = %s")
                params.append(payload[field])
        
        if not updates:
            raise HTTPException(status_code=400, detail="No valid fields to update")
        
        params.append(record_id)
        update_query = f"UPDATE attendance_records SET {', '.join(updates)} WHERE record_id = %s"
        
        cur.execute(update_query, params)
        conn.commit()
        cur.close()
        db_pool.put_conn(conn)
        
        log_audit(user['user_id'], "update_attendance", "attendance_record", record_id, get_user_ip(request), get_user_agent(request))
        
        return {'message': 'Attendance record updated successfully'}
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Update attendance error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.post("/api/attendance/manual")
async def add_manual_attendance(request: Request, attendance_data: ManualAttendanceRequest):
    """Manually add an attendance record (admin/faculty only)."""
    user = get_current_user(request)
    if not user or user.get('role') not in ('admin', 'faculty'):
        raise HTTPException(status_code=403, detail="Admin or Faculty only")
    
    try:
        conn = db_pool.get_conn()
        cur = conn.cursor()
        payload = attendance_data.model_dump()
        
        # Validate student exists
        cur.execute("SELECT student_id FROM students WHERE student_id = %s AND is_active = TRUE", 
               (payload['student_id'],))
        if not cur.fetchone():
            cur.close()
            db_pool.put_conn(conn)
            raise HTTPException(status_code=404, detail="Student not found")
        
        # Validate classroom exists
        cur.execute("SELECT classroom_id FROM classrooms WHERE classroom_id = %s", 
               (payload['classroom_id'],))
        if not cur.fetchone():
            cur.close()
            db_pool.put_conn(conn)
            raise HTTPException(status_code=404, detail="Classroom not found")
        
        # Insert manual attendance record
        cur.execute(
            """INSERT INTO attendance_records
               (student_id, classroom_id, device_id, timestamp, status, verification_method, match_score)
               VALUES (%s, %s, %s, %s, %s, %s, %s)
               RETURNING record_id""",
            (
                payload['student_id'],
                payload['classroom_id'],
                payload.get('device_id', 'MANUAL'),
                payload['timestamp'],
                payload.get('status', 'manual'),
                'manual',
                None
            )
        )
        record_id = cur.fetchone()[0]
        conn.commit()
        cur.close()
        db_pool.put_conn(conn)
        
        log_audit(user['user_id'], "add_manual_attendance", "attendance_record", str(record_id), 
                 get_user_ip(request), get_user_agent(request))
        
        return {'message': 'Manual attendance record added successfully', 'record_id': str(record_id)}
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Add manual attendance error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/api/attendance/course/{course_id}")
async def get_course_attendance(request: Request, course_id: str):
    """Get all attendance for a course."""
    user = get_current_user(request)
    if not user or user['role'] not in ('faculty', 'admin'):
        raise HTTPException(status_code=403, detail="Faculty/Admin only")
    
    try:
        conn = db_pool.get_conn()
        cur = conn.cursor()
        
        cur.execute(
            """SELECT ar.record_id, ar.student_id, ar.timestamp, ar.status
               FROM attendance_records ar
               JOIN classrooms cl ON ar.classroom_id = cl.classroom_id
               WHERE ar.timestamp > NOW() - INTERVAL '120 days'
               ORDER BY ar.timestamp DESC
               LIMIT 500"""
        )
        rows = cur.fetchall()
        cur.close()
        db_pool.put_conn(conn)
        
        return [
            {
                'record_id': str(row[0]),
                'student_id': str(row[1]),
                'timestamp': str(row[2]),
                'status': row[3]
            }
            for row in rows
        ]
    
    except Exception as e:
        logger.error(f"Course attendance error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/api/attendance/stats")
async def get_attendance_stats(request: Request):
    """Get aggregate stats."""
    try:
        conn = db_pool.get_conn()
        cur = conn.cursor()
        
        cur.execute(
            """SELECT COUNT(*) FROM attendance_records
               WHERE timestamp > NOW() - INTERVAL '1 day'"""
        )
        total_today = cur.fetchone()[0]
        
        cur.execute(
            """SELECT COUNT(DISTINCT student_id) FROM attendance_records
               WHERE timestamp > NOW() - INTERVAL '1 day'"""
        )
        unique_students = cur.fetchone()[0]
        
        cur.close()
        db_pool.put_conn(conn)
        
        return {
            'total_scans_today': total_today,
            'unique_students_today': unique_students,
            'attendance_pct_by_course': []
        }
    
    except Exception as e:
        logger.error(f"Stats error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


# ============================================================================
# ENDPOINTS: SETTINGS
# ============================================================================

_attendance_threshold = {'value': int(os.getenv('ATTENDANCE_THRESHOLD', 75))}

@app.get("/api/settings/threshold")
async def get_threshold(request: Request):
    return {'threshold': _attendance_threshold['value']}

@app.post("/api/settings/threshold")
async def set_threshold(request: Request, body: dict = Body(...)):
    user = get_current_user(request)
    if not user or user.get('role') not in ('admin', 'faculty'):
        raise HTTPException(status_code=403, detail="Admin or Faculty only")
    val = body.get('threshold')
    if not isinstance(val, int) or val < 1 or val > 100:
        raise HTTPException(status_code=400, detail="Threshold must be 1-100")
    _attendance_threshold['value'] = val
    log_audit(user['user_id'], "set_threshold", None, None, get_user_ip(request), get_user_agent(request))
    return {'threshold': val, 'message': 'Threshold updated'}


# ============================================================================
# ENDPOINTS: REPORTS
# ============================================================================

@app.get("/api/reports/student/{student_id}")
async def get_student_report(request: Request, student_id: str):
    """Get per-student attendance report by course."""
    user = get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Unauthorized")

    if user.get('role') == 'student':
        try:
            with db_pool.get_cursor() as (_, cur):
                cur.execute("SELECT student_id FROM students WHERE user_id = %s::uuid", (user['user_id'],))
                row = cur.fetchone()
                if not row:
                    raise HTTPException(status_code=404, detail="Student profile not found")
                if str(row[0]) != student_id:
                    raise HTTPException(status_code=403, detail="Can only view own report")
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Student report access check error: {e}")
            raise HTTPException(status_code=500, detail="Internal server error")

    try:
        with db_pool.get_cursor() as (_, cur):
            cur.execute(
                """SELECT c.course_id, c.course_name,
                          COALESCE(COUNT(ar.record_id) FILTER (WHERE ar.status = 'present'), 0) AS present,
                          COALESCE(COUNT(ar.record_id), 0) AS total
                   FROM course_enrollments ce
                   JOIN courses c ON c.course_id = ce.course_id
                   LEFT JOIN class_schedule cs ON cs.course_id = c.course_id
                   LEFT JOIN attendance_records ar
                       ON ar.student_id = ce.student_id
                      AND ar.classroom_id = cs.classroom_id
                   WHERE ce.student_id = %s::uuid
                   GROUP BY c.course_id, c.course_name
                   ORDER BY c.course_name""",
                (student_id,)
            )
            rows = cur.fetchall()

        courses = []
        for row in rows:
            total = row[3]
            pct = round((row[2] / total) * 100, 2) if total > 0 else 0.0
            courses.append(
                {
                    'course_id': str(row[0]),
                    'course_name': row[1],
                    'present': row[2],
                    'total': total,
                    'attendance_pct': pct,
                    'status_chip': 'success' if pct >= 75 else 'warning' if pct >= 50 else 'error'
                }
            )

        return {'student_id': student_id, 'courses': courses}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Student report error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/api/reports/course/{course_id}")
async def get_course_report(request: Request, course_id: str):
    """Get course attendance report."""
    user = get_current_user(request)
    if not user or user['role'] not in ('faculty', 'admin'):
        raise HTTPException(status_code=403, detail="Faculty/Admin only")

    try:
        with db_pool.get_cursor() as (_, cur):
            cur.execute(
                """SELECT c.course_id, c.course_name, c.faculty_id
                   FROM courses c
                   WHERE c.course_id = %s::uuid AND c.is_active = TRUE""",
                (course_id,)
            )
            course_row = cur.fetchone()
            if not course_row:
                raise HTTPException(status_code=404, detail="Course not found")

            if user['role'] == 'faculty' and str(course_row[2]) != user['user_id']:
                raise HTTPException(status_code=403, detail="Can only view own course")

            cur.execute(
                """SELECT COUNT(*)
                   FROM course_enrollments
                   WHERE course_id = %s::uuid""",
                (course_id,)
            )
            total_enrolled = cur.fetchone()[0]

            cur.execute(
                """SELECT COUNT(*) FILTER (WHERE ar.status = 'present') AS present_count,
                          COUNT(ar.record_id) AS total_count
                   FROM class_schedule cs
                   LEFT JOIN attendance_records ar ON ar.classroom_id = cs.classroom_id
                   WHERE cs.course_id = %s::uuid""",
                (course_id,)
            )
            present_count, total_records = cur.fetchone()
            attendance_pct = round((present_count / total_records) * 100, 2) if total_records > 0 else 0.0

            cur.execute(
                """SELECT s.student_id, s.full_name, s.student_number,
                          COALESCE(COUNT(ar.record_id) FILTER (WHERE ar.status = 'present'), 0) AS present_count,
                          COALESCE(COUNT(ar.record_id), 0) AS total_count
                   FROM course_enrollments ce
                   JOIN students s ON s.student_id = ce.student_id
                   LEFT JOIN class_schedule cs ON cs.course_id = ce.course_id
                   LEFT JOIN attendance_records ar
                       ON ar.student_id = ce.student_id
                      AND ar.classroom_id = cs.classroom_id
                   WHERE ce.course_id = %s::uuid
                   GROUP BY s.student_id, s.full_name, s.student_number
                   ORDER BY s.full_name""",
                (course_id,)
            )
            at_risk_rows = cur.fetchall()

        at_risk_students = []
        for row in at_risk_rows:
            total = row[4]
            pct = round((row[3] / total) * 100, 2) if total > 0 else 0.0
            if pct < 75:
                at_risk_students.append(
                    {
                        'student_id': str(row[0]),
                        'full_name': row[1],
                        'student_number': row[2],
                        'attendance_pct': pct
                    }
                )

        return {
            'course_id': str(course_row[0]),
            'course_name': course_row[1],
            'total_enrolled': total_enrolled,
            'total_records': total_records,
            'attendance_pct': attendance_pct,
            'at_risk_students': at_risk_students
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Course report error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/api/reports/system")
async def get_system_report(request: Request):
    """Get system-wide report (admin only)."""
    user = get_current_user(request)
    if not user or user['role'] != 'admin':
        raise HTTPException(status_code=403, detail="Admin only")

    try:
        with db_pool.get_cursor() as (_, cur):
            cur.execute("SELECT COUNT(*) FROM students WHERE is_active = TRUE")
            total_students = cur.fetchone()[0]

            cur.execute("SELECT COUNT(*) FROM courses WHERE is_active = TRUE")
            total_courses = cur.fetchone()[0]

            cur.execute("SELECT COUNT(*) FROM attendance_records")
            total_scans_all_time = cur.fetchone()[0]

            cur.execute(
                """SELECT
                       COUNT(*) FILTER (WHERE status = 'present')::float,
                       COUNT(*)::float
                   FROM attendance_records"""
            )
            present_count, total_count = cur.fetchone()
            avg_attendance_pct = round((present_count / total_count) * 100, 2) if total_count > 0 else 0.0

            cur.execute(
                """SELECT c.course_id, c.course_name, COUNT(ar.record_id) AS scans
                   FROM courses c
                   LEFT JOIN class_schedule cs ON cs.course_id = c.course_id
                   LEFT JOIN attendance_records ar ON ar.classroom_id = cs.classroom_id
                   WHERE c.is_active = TRUE
                   GROUP BY c.course_id, c.course_name
                   ORDER BY scans DESC
                   LIMIT 5"""
            )
            top_rows = cur.fetchall()

        devices_online = 0
        if redis_client:
            for key in redis_client.keys("gateway:*:health"):
                payload = redis_client.get(key)
                if not payload:
                    continue
                heartbeat = json.loads(payload)
                devices_online += len(heartbeat.get('connected_devices', []))

        return {
            'total_students': total_students,
            'total_courses': total_courses,
            'total_scans_all_time': total_scans_all_time,
            'avg_attendance_pct': avg_attendance_pct,
            'devices_online': devices_online,
            'top_courses': [
                {'course_id': str(row[0]), 'course_name': row[1], 'scans': row[2]}
                for row in top_rows
            ]
        }
    except Exception as e:
        logger.error(f"System report error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/api/reports/export/csv/{course_id}")
async def export_attendance_csv(request: Request, course_id: str):
    """Export attendance CSV for course."""
    user = get_current_user(request)
    if not user or user['role'] not in ('faculty', 'admin'):
        raise HTTPException(status_code=403, detail="Faculty/Admin only")

    try:
        with db_pool.get_cursor() as (_, cur):
            cur.execute("SELECT course_name, faculty_id FROM courses WHERE course_id = %s::uuid", (course_id,))
            course_row = cur.fetchone()
            if not course_row:
                raise HTTPException(status_code=404, detail="Course not found")

            if user['role'] == 'faculty' and str(course_row[1]) != user['user_id']:
                raise HTTPException(status_code=403, detail="Can only export own course")

            cur.execute(
                """SELECT s.full_name, s.student_number,
                          DATE(ar.timestamp) AS class_date,
                          ar.timestamp,
                          ar.status
                   FROM course_enrollments ce
                   JOIN students s ON s.student_id = ce.student_id
                   LEFT JOIN class_schedule cs ON cs.course_id = ce.course_id
                   LEFT JOIN attendance_records ar
                       ON ar.student_id = ce.student_id
                      AND ar.classroom_id = cs.classroom_id
                   WHERE ce.course_id = %s::uuid
                   ORDER BY s.full_name, ar.timestamp DESC NULLS LAST""",
                (course_id,)
            )
            rows = cur.fetchall()

        csv_lines = ["Student,StudentNumber,Date,Timestamp,Status"]
        for row in rows:
            class_date = str(row[2]) if row[2] else ''
            ts = str(row[3]) if row[3] else ''
            status = row[4] if row[4] else 'absent'
            csv_lines.append(f"{row[0]},{row[1]},{class_date},{ts},{status}")

        csv_data = "\n".join(csv_lines) + "\n"
        return StreamingResponse(
            iter([csv_data]),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename=attendance_{course_id}.csv"}
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"CSV export error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


# ============================================================================
# ENDPOINTS: DEVICES & GATEWAY
# ============================================================================

@app.get("/api/devices")
async def list_devices(request: Request):
    """List all registered devices."""
    user = get_current_user(request)
    if not user or user['role'] != 'admin':
        raise HTTPException(status_code=403, detail="Admin only")

    try:
        with db_pool.get_cursor() as (_, cur):
            cur.execute(
                """SELECT classroom_id, room_number, building, device_id
                   FROM classrooms
                   WHERE device_id IS NOT NULL
                   ORDER BY room_number"""
            )
            classroom_rows = cur.fetchall()

        heartbeat_by_device = {}
        if redis_client:
            for key in redis_client.keys("gateway:*:health"):
                raw = redis_client.get(key)
                if not raw:
                    continue
                hb = json.loads(raw)
                for device_id in hb.get('connected_devices', []):
                    heartbeat_by_device[device_id] = {
                        'gateway_id': hb.get('gateway_id'),
                        'last_seen': hb.get('last_forward_at'),
                        'backend_reachable': hb.get('backend_reachable', False),
                        'queue_depth': hb.get('queue_depth', 0),
                    }

        results = []
        for row in classroom_rows:
            heartbeat = heartbeat_by_device.get(row[3], {})
            results.append(
                {
                    'classroom_id': str(row[0]),
                    'device_id': row[3],
                    'classroom': row[1],
                    'building': row[2],
                    'last_seen': heartbeat.get('last_seen'),
                    'status': 'online' if heartbeat else 'offline',
                    'gateway_id': heartbeat.get('gateway_id'),
                    'backend_reachable': heartbeat.get('backend_reachable', False),
                    'queue_depth': heartbeat.get('queue_depth', 0),
                }
            )

        return results
    except Exception as e:
        logger.error(f"List devices error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.post("/api/gateway/heartbeat")
async def gateway_heartbeat(request: Request, heartbeat: GatewayHeartbeat):
    """Receive gateway heartbeat."""
    require_device_token(request)
    # Update Redis cache for gateway status
    if redis_client:
        redis_client.setex(f"gateway:{heartbeat.gateway_id}:health", 120, json.dumps(heartbeat.dict()))
    
    logger.info(f"[Gateway] Heartbeat: {heartbeat.gateway_id} | Queue: {heartbeat.queue_depth}")
    return {'status': 'ok'}


# ============================================================================
# ENDPOINTS: AUDIT LOG
# ============================================================================

def log_audit(user_id: Optional[str], action: str, entity_type: Optional[str],
              entity_id: Optional[str], ip_address: str, user_agent: str):
    """Log action to audit log."""
    try:
        if not db_pool:
            return
        
        conn = db_pool.get_conn()
        cur = conn.cursor()
        
        cur.execute(
            """INSERT INTO audit_log (user_id, action, entity_type, entity_id, ip_address, user_agent, created_at)
               VALUES (%s, %s, %s, %s, %s, %s, NOW())""",
            (user_id, action, entity_type, entity_id, ip_address, user_agent)
        )
        conn.commit()
        cur.close()
        db_pool.put_conn(conn)
    
    except Exception as e:
        logger.error(f"Audit log error: {e}")


@app.get("/api/audit-log")
async def get_audit_log(request: Request, offset: int = 0, limit: int = 50):
    """Get audit log entries (admin only)."""
    user = get_current_user(request)
    if not user or user['role'] != 'admin':
        raise HTTPException(status_code=403, detail="Admin only")
    
    try:
        conn = db_pool.get_conn()
        cur = conn.cursor()
        
        cur.execute(
            """SELECT al.log_id, al.user_id, al.action, al.entity_type, al.ip_address, al.created_at
               FROM audit_log al
               ORDER BY al.created_at DESC
               LIMIT %s OFFSET %s""",
            (limit, offset)
        )
        rows = cur.fetchall()
        cur.close()
        db_pool.put_conn(conn)
        
        return [
            {
                'log_id': str(row[0]),
                'user_id': str(row[1]) if row[1] else None,
                'action': row[2],
                'entity_type': row[3],
                'ip_address': row[4],
                'created_at': str(row[5])
            }
            for row in rows
        ]
    
    except Exception as e:
        logger.error(f"Audit log error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


# ============================================================================
# WEBSOCKET
# ============================================================================

@app.websocket("/ws/attendance")
async def websocket_endpoint(websocket: WebSocket, token: str = Query(None)):
    """WebSocket endpoint for real-time attendance feed."""
    
    if not token:
        await websocket.close(code=4000, reason="Missing token")
        return
    
    user_data = verify_jwt(token)
    if not user_data:
        await websocket.close(code=4001, reason="Invalid token")
        return
    
    if redis_client and redis_client.exists(f"jwt_blacklist:{token}"):
        await websocket.close(code=4001, reason="Token blacklisted")
        return
    
    client_id = await ws_manager.connect(websocket, user_data)
    
    try:
        while True:
            # Keep connection alive
            data = await websocket.receive_text()
            # Echo ping
            await websocket.send_text(json.dumps({'ping': 'pong'}))
    
    except:
        ws_manager.disconnect(client_id)


if __name__ == '__main__':
    uvicorn.run(app, host='0.0.0.0', port=8000, reload=True)
