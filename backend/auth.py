"""JWT authentication + PBKDF2 password hashing + role-based guards.

Password hashing uses hashlib.pbkdf2_hmac from the standard library
(no external crypto pitfalls), tokens are HS256 JWTs via python-jose.
"""
import hashlib
import hmac
import secrets
from datetime import datetime, timedelta

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.orm import Session

import models
from config import settings
from database import get_db

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

_ITERATIONS = 120_000


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), _ITERATIONS)
    return f"pbkdf2_sha256${_ITERATIONS}${salt}${dk.hex()}"


def verify_password(password: str, hashed: str) -> bool:
    try:
        algo, iters, salt, digest = hashed.split("$")
        assert algo == "pbkdf2_sha256"
        dk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), int(iters))
        return hmac.compare_digest(dk.hex(), digest)
    except Exception:
        return False


def create_access_token(subject: str) -> str:
    expire = datetime.now() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    return jwt.encode(
        {"sub": subject, "exp": expire},
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM,
    )


def get_current_user(
    token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)
) -> models.User:
    exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Not authenticated",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        username: str = payload.get("sub")
        if not username:
            raise exc
    except JWTError:
        raise exc
    user = db.query(models.User).filter(models.User.username == username).first()
    if not user or not user.is_active:
        raise exc
    return user


def require_roles(*roles: str):
    """Dependency factory: allow only users whose role is in *roles*."""

    def _guard(user: models.User = Depends(get_current_user)) -> models.User:
        if user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Requires one of roles: {', '.join(roles)}",
            )
        return user

    return _guard


require_admin = require_roles(models.ROLE_ADMIN)
require_manager = require_roles(models.ROLE_ADMIN, models.ROLE_MANAGER)
