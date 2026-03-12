"""JWT authentication for team collaboration.

Provides login, current-user, and user-management endpoints.
Passwords are bcrypt-hashed. JWTs use HS256 with a configurable secret.

Routes:
  POST /api/auth/login         — exchange email+password for JWT
  GET  /api/auth/me            — current user info
  POST /api/auth/users         — create a user (admin only)
  GET  /api/auth/users         — list users (admin only)
  PUT  /api/auth/users/{id}    — update user (admin only)
  DELETE /api/auth/users/{id}  — deactivate user (admin only)

Usage in other endpoints:
  from app.auth import require_auth, require_role
  @router.get("/protected")
  def endpoint(user = Depends(require_auth)):
      ...
"""

from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from typing import Optional

import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
import bcrypt as _bcrypt_lib
from jose import JWTError, jwt
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db import get_db
from app.models.user import User

log = structlog.get_logger()
router = APIRouter(prefix="/api/auth", tags=["auth"])

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

_SECRET_KEY = os.environ.get("APP_SECRET_KEY", "change-me-in-production-please")
_ALGORITHM = "HS256"
_TOKEN_EXPIRE_HOURS = 24 * 7  # 7 days

_bearer = HTTPBearer(auto_error=False)


# ---------------------------------------------------------------------------
# Password utilities
# ---------------------------------------------------------------------------


def hash_password(plaintext: str) -> str:
    return _bcrypt_lib.hashpw(plaintext.encode(), _bcrypt_lib.gensalt()).decode()


def verify_password(plaintext: str, hashed: str) -> bool:
    return _bcrypt_lib.checkpw(plaintext.encode(), hashed.encode())


# ---------------------------------------------------------------------------
# JWT utilities
# ---------------------------------------------------------------------------


def create_access_token(user_id: int, role: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(hours=_TOKEN_EXPIRE_HOURS)
    payload = {"sub": str(user_id), "role": role, "exp": expire}
    return jwt.encode(payload, _SECRET_KEY, algorithm=_ALGORITHM)


def decode_token(token: str) -> dict:
    try:
        return jwt.decode(token, _SECRET_KEY, algorithms=[_ALGORITHM])
    except JWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        ) from exc


# ---------------------------------------------------------------------------
# FastAPI dependencies
# ---------------------------------------------------------------------------


def require_auth(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer),
    db: Session = Depends(get_db),
) -> User:
    """Dependency: require a valid JWT. Returns the authenticated User."""
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
        )
    payload = decode_token(credentials.credentials)
    user_id = int(payload["sub"])
    user = db.query(User).filter_by(id=user_id, is_active=True).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or deactivated",
        )
    return user


def require_role(*roles: str):
    """Dependency factory: require one of the specified roles."""

    def _dep(user: User = Depends(require_auth)) -> User:
        if user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{user.role}' is not authorized for this action.",
            )
        return user

    return _dep


# ---------------------------------------------------------------------------
# Request/response models
# ---------------------------------------------------------------------------


class LoginRequest(BaseModel):
    email: str
    password: str


class CreateUserRequest(BaseModel):
    email: str
    password: str
    full_name: str = ""
    role: str = "admin"


class UpdateUserRequest(BaseModel):
    full_name: Optional[str] = None
    role: Optional[str] = None
    is_active: Optional[bool] = None
    password: Optional[str] = None


def _serialize_user(u: User) -> dict:
    return {
        "id": u.id,
        "email": u.email,
        "full_name": u.full_name,
        "role": u.role,
        "is_active": u.is_active,
        "created_at": u.created_at.isoformat(),
    }


VALID_ROLES = {"admin", "manager", "housekeeper", "owner", "accountant"}

# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.post("/login")
def login(body: LoginRequest, db: Session = Depends(get_db)) -> dict:
    """Authenticate and return a JWT access token."""
    user = db.query(User).filter_by(email=body.email, is_active=True).first()
    if not user or not verify_password(body.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )
    token = create_access_token(user.id, user.role)
    log.info("user_login", user_id=user.id, email=user.email)
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": _serialize_user(user),
    }


@router.get("/me")
def me(user: User = Depends(require_auth)) -> dict:
    return _serialize_user(user)


@router.post("/users", status_code=201)
def create_user(
    body: CreateUserRequest,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_role("admin")),
) -> dict:
    if body.role not in VALID_ROLES:
        raise HTTPException(
            status_code=422, detail=f"role must be one of {sorted(VALID_ROLES)}"
        )
    existing = db.query(User).filter_by(email=body.email).first()
    if existing:
        raise HTTPException(status_code=409, detail="Email already in use")
    user = User(
        email=body.email,
        hashed_password=hash_password(body.password),
        full_name=body.full_name,
        role=body.role,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return _serialize_user(user)


@router.get("/users")
def list_users(
    db: Session = Depends(get_db),
    _admin: User = Depends(require_role("admin")),
) -> list[dict]:
    return [_serialize_user(u) for u in db.query(User).order_by(User.created_at).all()]


@router.put("/users/{user_id}")
def update_user(
    user_id: int,
    body: UpdateUserRequest,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_role("admin")),
) -> dict:
    user = db.query(User).filter_by(id=user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if body.full_name is not None:
        user.full_name = body.full_name
    if body.role is not None:
        if body.role not in VALID_ROLES:
            raise HTTPException(
                status_code=422, detail=f"role must be one of {sorted(VALID_ROLES)}"
            )
        user.role = body.role
    if body.is_active is not None:
        user.is_active = body.is_active
    if body.password is not None:
        user.hashed_password = hash_password(body.password)
    db.commit()
    db.refresh(user)
    return _serialize_user(user)


@router.delete("/users/{user_id}", status_code=204)
def deactivate_user(
    user_id: int,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_role("admin")),
) -> None:
    user = db.query(User).filter_by(id=user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.is_active = False
    db.commit()
