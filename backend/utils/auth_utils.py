from datetime import datetime, timedelta
from typing import Optional
from jose import jwt, JWTError
from config import settings

# ✅ Fix: avoid passlib bcrypt bug by using bcrypt directly
try:
    import bcrypt as _bcrypt
    def hash_password(password: str) -> str:
        pw = password.encode("utf-8")[:72]  # bcrypt max 72 bytes
        return _bcrypt.hashpw(pw, _bcrypt.gensalt()).decode("utf-8")

    def verify_password(plain: str, hashed: str) -> bool:
        pw = plain.encode("utf-8")[:72]
        return _bcrypt.checkpw(pw, hashed.encode("utf-8"))

except ImportError:
    # Fallback to passlib if bcrypt not available
    from passlib.context import CryptContext
    _ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")
    def hash_password(password: str) -> str:
        return _ctx.hash(password[:72])
    def verify_password(plain: str, hashed: str) -> bool:
        return _ctx.verify(plain[:72], hashed)


def create_token(user_id: str) -> str:
    expire = datetime.utcnow() + timedelta(hours=settings.JWT_EXPIRE_HOURS)
    return jwt.encode(
        {"sub": user_id, "exp": expire},
        settings.JWT_SECRET,
        algorithm="HS256",
    )


def decode_token(token: str) -> Optional[str]:
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=["HS256"])
        return payload.get("sub")
    except JWTError:
        return None