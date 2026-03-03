"""
meetingmind/auth.py — JWT auth with proper security
"""
import os
import uuid
import bcrypt
from datetime import datetime, timedelta, timezone
from typing import Optional

from dotenv import load_dotenv
from jose import JWTError, jwt

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 30))
REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", 7))
MAX_FAILED_LOGINS = 5
LOCKOUT_MINUTES = 15

if not SECRET_KEY:
    raise ValueError("SECRET_KEY not found in .env file")

def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt(rounds=12)).decode()

def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode(), hashed.encode())

def create_access_token(user_id: int, role: str) -> str:
    jti = str(uuid.uuid4())
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {
        "sub": str(user_id),
        "role": role,
        "jti": jti,
        "type": "access",
        "exp": expire
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

def create_refresh_token(user_id: int) -> str:
    jti = str(uuid.uuid4())
    expire = datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    payload = {
        "sub": str(user_id),
        "jti": jti,
        "type": "refresh",
        "exp": expire
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

def decode_token(token: str) -> Optional[dict]:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        return None

def revoke_token(jti: str, expires_at: datetime, conn):
    conn.execute(
        "INSERT OR IGNORE INTO revoked_tokens (jti, expires_at) VALUES (?, ?)",
        (jti, expires_at.isoformat())
    )
    conn.commit()

def is_token_revoked(jti: str, conn) -> bool:
    row = conn.execute(
        "SELECT jti FROM revoked_tokens WHERE jti = ?", (jti,)
    ).fetchone()
    return row is not None

def cleanup_expired_tokens(conn):
    """Remove expired tokens from blacklist to keep table small."""
    conn.execute(
        "DELETE FROM revoked_tokens WHERE expires_at < ?",
        (datetime.now(timezone.utc).isoformat(),)
    )
    conn.commit()

def is_account_locked(user) -> bool:
    if user["locked_until"] is None:
        return False
    locked_until = datetime.fromisoformat(user["locked_until"])
    if locked_until.tzinfo is None:
        locked_until = locked_until.replace(tzinfo=timezone.utc)
    return datetime.now(timezone.utc) < locked_until

def record_failed_login(user_id: int, conn):
    user = conn.execute("SELECT failed_logins FROM users WHERE id = ?", (user_id,)).fetchone()
    failed = user["failed_logins"] + 1
    locked_until = None
    if failed >= MAX_FAILED_LOGINS:
        locked_until = (datetime.now(timezone.utc) + timedelta(minutes=LOCKOUT_MINUTES)).isoformat()
        failed = 0  # reset counter after lockout
    conn.execute(
        "UPDATE users SET failed_logins = ?, locked_until = ? WHERE id = ?",
        (failed, locked_until, user_id)
    )
    conn.commit()

def reset_failed_logins(user_id: int, conn):
    conn.execute(
        "UPDATE users SET failed_logins = 0, locked_until = NULL WHERE id = ?",
        (user_id,)
    )
    conn.commit()
