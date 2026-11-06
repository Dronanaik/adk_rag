import base64
import hashlib
import hmac
import json
import re
import secrets
import time
import uuid
from typing import Any

from fastapi import Header, HTTPException
from psycopg2.extras import RealDictCursor

from app.config import DATABASE_URL, GOOGLE_API_KEY, JWT_EXPIRE_HOURS, JWT_SECRET_KEY
from app.database import get_db_connection, init_postgres_db

_auth_schema_initialized = False
PBKDF2_ITERATIONS = 260_000
EMAIL_REGEX = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _ensure_auth_schema() -> None:
    global _auth_schema_initialized
    if not _auth_schema_initialized:
        init_postgres_db()
        _auth_schema_initialized = True


def _get_signing_secret() -> bytes:
    """
    Return the secret key bytes for signing JWT tokens.
    If JWT_SECRET_KEY is not explicitly set in .env, derive a deterministic secret
    from DATABASE_URL + GOOGLE_API_KEY so tokens remain valid across Uvicorn reloads.
    """
    raw = JWT_SECRET_KEY or f"adk-rag-neon-auth::{DATABASE_URL}::{GOOGLE_API_KEY}"
    return hashlib.sha256(raw.encode("utf-8")).digest()


def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _b64url_decode(segment: str) -> bytes:
    padding = "=" * (-len(segment) % 4)
    return base64.urlsafe_b64decode(segment + padding)


def hash_password(password: str) -> str:
    """
    Hash a plaintext password using PBKDF2-HMAC-SHA256 with a 16-byte random salt.
    """
    salt = secrets.token_hex(16)
    derived = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("ascii"),
        PBKDF2_ITERATIONS,
    )
    return f"pbkdf2_sha256${PBKDF2_ITERATIONS}${salt}${derived.hex()}"


def verify_password(password: str, stored_hash: str) -> bool:
    """
    Constant-time verification of a plaintext password against a stored PBKDF2 hash.
    """
    try:
        algorithm, iterations_str, salt, hex_digest = stored_hash.split("$", 3)
        if algorithm != "pbkdf2_sha256":
            return False
        iterations = int(iterations_str)
        derived = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            salt.encode("ascii"),
            iterations,
        )
        return hmac.compare_digest(derived.hex(), hex_digest)
    except Exception:
        return False


def create_access_token(user: dict[str, Any]) -> str:
    """
    Create a signed HS256 JWT token containing the user's identity.
    """
    now = int(time.time())
    header = {"alg": "HS256", "typ": "JWT"}
    payload = {
        "sub": str(user["id"]),
        "email": user["email"],
        "full_name": user["full_name"],
        "iat": now,
        "exp": now + (JWT_EXPIRE_HOURS * 3600),
    }

    header_b64 = _b64url_encode(json.dumps(header, separators=(",", ":")).encode("utf-8"))
    payload_b64 = _b64url_encode(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
    signing_input = f"{header_b64}.{payload_b64}".encode("ascii")

    signature = hmac.new(_get_signing_secret(), signing_input, hashlib.sha256).digest()
    signature_b64 = _b64url_encode(signature)

    return f"{header_b64}.{payload_b64}.{signature_b64}"


def decode_access_token(token: str) -> dict[str, Any]:
    """
    Verify and decode an HS256 JWT token. Raises ValueError if invalid or expired.
    """
    parts = token.strip().split(".")
    if len(parts) != 3:
        raise ValueError("Invalid authentication token format.")

    header_b64, payload_b64, signature_b64 = parts
    signing_input = f"{header_b64}.{payload_b64}".encode("ascii")
    expected_sig = hmac.new(_get_signing_secret(), signing_input, hashlib.sha256).digest()
    actual_sig = _b64url_decode(signature_b64)

    if not hmac.compare_digest(expected_sig, actual_sig):
        raise ValueError("Invalid authentication token signature.")

    payload = json.loads(_b64url_decode(payload_b64).decode("utf-8"))
    exp = int(payload.get("exp", 0))
    if exp < int(time.time()):
        raise ValueError("Session token has expired. Please sign in again.")

    return payload


def register_user(email: str, password: str, full_name: str) -> dict[str, Any]:
    """
    Register a new user in the Neon PostgreSQL `users` table.
    """
    _ensure_auth_schema()

    email_clean = email.strip().lower()
    name_clean = full_name.strip()

    if not EMAIL_REGEX.match(email_clean):
        raise ValueError("Please enter a valid email address.")
    if len(name_clean) < 2:
        raise ValueError("Full name must be at least 2 characters.")
    if len(password) < 6:
        raise ValueError("Password must be at least 6 characters.")

    user_uuid = str(uuid.uuid4())
    pw_hash = hash_password(password)

    with get_db_connection(register_pgvector=False) as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                "SELECT id FROM users WHERE LOWER(email) = %s;",
                (email_clean,),
            )
            if cur.fetchone():
                raise ValueError("An account with this email already exists. Please sign in.")

            cur.execute(
                """
                INSERT INTO users (id, email, full_name, password_hash, last_login_at)
                VALUES (%s::uuid, %s, %s, %s, CURRENT_TIMESTAMP)
                RETURNING id::text AS id, email, full_name, created_at;
                """,
                (user_uuid, email_clean, name_clean, pw_hash),
            )
            row = cur.fetchone()

    return {
        "id": row["id"],
        "email": row["email"],
        "full_name": row["full_name"],
        "created_at": row["created_at"].isoformat() if row.get("created_at") else None,
    }


def authenticate_user(email: str, password: str) -> dict[str, Any]:
    """
    Authenticate an existing user against the Neon PostgreSQL `users` table.
    """
    _ensure_auth_schema()

    email_clean = email.strip().lower()
    if not email_clean or not password:
        raise ValueError("Email and password are required.")

    with get_db_connection(register_pgvector=False) as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                SELECT id::text AS id, email, full_name, password_hash, created_at
                FROM users
                WHERE LOWER(email) = %s;
                """,
                (email_clean,),
            )
            user = cur.fetchone()

            if not user or not verify_password(password, user["password_hash"]):
                raise ValueError("Invalid email or password.")

            cur.execute(
                "UPDATE users SET last_login_at = CURRENT_TIMESTAMP WHERE id = %s::uuid;",
                (user["id"],),
            )

    return {
        "id": user["id"],
        "email": user["email"],
        "full_name": user["full_name"],
        "created_at": user["created_at"].isoformat() if user.get("created_at") else None,
    }


def get_user_by_id(user_id: str) -> dict[str, Any] | None:
    """
    Look up a user by UUID in Neon PostgreSQL.
    """
    _ensure_auth_schema()
    with get_db_connection(register_pgvector=False) as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                SELECT id::text AS id, email, full_name, created_at, last_login_at
                FROM users
                WHERE id = %s::uuid;
                """,
                (str(user_id),),
            )
            row = cur.fetchone()

    if not row:
        return None

    return {
        "id": row["id"],
        "email": row["email"],
        "full_name": row["full_name"],
        "created_at": row["created_at"].isoformat() if row.get("created_at") else None,
    }


def get_current_user(
    authorization: str | None = Header(default=None),
    x_user_id: str | None = Header(default=None, alias="x-user-id"),
) -> dict[str, Any]:
    """
    FastAPI dependency to authenticate requests via Bearer JWT token (backed by Neon PostgreSQL).
    Returns a dictionary containing `id`, `email`, `full_name`, and `user_id` (used for data isolation).
    """
    if authorization and authorization.lower().startswith("bearer "):
        token = authorization[7:].strip()
        try:
            payload = decode_access_token(token)
            email = payload.get("email")
            sub = payload.get("sub")
            full_name = payload.get("full_name", email)
            if not email or not sub:
                raise ValueError("Malformed token payload.")
            return {
                "id": sub,
                "email": email,
                "full_name": full_name,
                "user_id": email,
            }
        except ValueError as err:
            raise HTTPException(status_code=401, detail=str(err))

    # Fallback only for CLI/curl backwards compatibility if x-user-id is passed directly
    if x_user_id and x_user_id.strip():
        uid = x_user_id.strip()
        return {
            "id": uid,
            "email": uid,
            "full_name": uid,
            "user_id": uid,
        }

    raise HTTPException(
        status_code=401,
        detail="Authentication required. Please sign in with your Neon account.",
    )
