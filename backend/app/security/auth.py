"""Password hashing, JWT issue/verify and the `current principal` dependency."""

from __future__ import annotations

import base64
import hashlib
import hmac
import secrets
import time
from dataclasses import dataclass

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import get_session
from app.models import User
from app.security.rbac import permissions_for

_ITERATIONS = 310_000
_bearer = HTTPBearer(auto_error=False)


def hash_password(password: str, salt: bytes | None = None) -> str:
    salt = salt or secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, _ITERATIONS)
    return (
        f"pbkdf2_sha256${_ITERATIONS}${base64.b64encode(salt).decode()}${base64.b64encode(digest).decode()}"
    )


def verify_password(password: str, stored: str) -> bool:
    try:
        scheme, iters, salt_b64, digest_b64 = stored.split("$")
        if scheme != "pbkdf2_sha256":
            return False
        salt = base64.b64decode(salt_b64)
        expected = base64.b64decode(digest_b64)
        actual = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, int(iters))
        return hmac.compare_digest(actual, expected)
    except (ValueError, TypeError):
        return False


def create_token(username: str, role: str) -> str:
    s = get_settings()
    now = int(time.time())
    payload = {"sub": username, "role": role, "iat": now, "exp": now + s.jwt_expire_minutes * 60}
    return jwt.encode(payload, s.jwt_secret, algorithm="HS256")


def decode_token(token: str) -> dict:
    return jwt.decode(
        token, get_settings().jwt_secret, algorithms=["HS256"], options={"require": ["exp", "sub"]}
    )


@dataclass(frozen=True)
class Principal:
    username: str
    role: str
    permissions: tuple[str, ...]

    def can(self, permission: str) -> bool:
        return permission in self.permissions


def current_principal(
    creds: HTTPAuthorizationCredentials | None = Depends(_bearer),
    session: Session = Depends(get_session),
) -> Principal:
    unauthorized = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Not authenticated",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if creds is None or creds.scheme.lower() != "bearer":
        raise unauthorized
    try:
        claims = decode_token(creds.credentials)
    except jwt.PyJWTError:
        raise unauthorized from None
    user = session.scalar(select(User).where(User.username == claims["sub"]))
    if user is None or not user.is_active:
        raise unauthorized
    # The role is re-read from the database; a stale token cannot keep a revoked role.
    return Principal(user.username, user.role, tuple(permissions_for(user.role)))


def require(permission: str):
    """Dependency factory: `Depends(require("approval:decide"))`."""

    def _dep(principal: Principal = Depends(current_principal)) -> Principal:
        if not principal.can(permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail=f"Missing permission: {permission}"
            )
        return principal

    return _dep
