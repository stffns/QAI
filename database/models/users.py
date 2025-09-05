"""
User models for QA Intelligence
Provides User, Role, and AuditLog models with security features
"""

from __future__ import annotations

from typing import Optional
from datetime import datetime, timedelta, timezone
from enum import Enum
import json
import re

from sqlmodel import SQLModel, Field
from pydantic import field_validator

from ..base import BaseModel, register_timestamp_listeners


class UserRole(str, Enum):
    ADMIN = "admin"
    ANALYST = "analyst"
    VIEWER = "viewer"
    OPERATOR = "operator"


class User(BaseModel, table=True):
    """
    Modelo de usuario con campos de seguridad
    Incluye validación, auditoría y relaciones
    """
    __tablename__ = "users"

    # Primary key
    id: Optional[int] = Field(default=None, primary_key=True)

    # Basic info (case-preserving)
    username: str = Field(
        index=True,
        min_length=3,
        max_length=50,
        description="Unique username for login (case-preserving)",
    )
    # Campo normalizado (lowercase) para unicidad real
    username_norm: str = Field(
        index=True,
        description="Lowercased username for unique constraint",
        sa_column_kwargs={"unique": True},
    )

    email: str = Field(
        max_length=255,
        description="User email address (case-preserving)",
    )
    email_norm: str = Field(
        index=True,
        description="Lowercased email for unique constraint",
        sa_column_kwargs={"unique": True},
    )

    full_name: Optional[str] = Field(
        default=None,
        max_length=255,
        description="Full display name",
    )

    role: UserRole = Field(
        default=UserRole.VIEWER,
        description="User role in the system",
    )

    # Security fields
    password_hash: str = Field(
        max_length=255,
        description="Hashed password",
        repr=False,  # evita mostrarlo en repr/logs
    )

    is_verified: bool = Field(
        default=False,
        description="Whether user email is verified",
    )

    failed_login_attempts: int = Field(
        default=0,
        ge=0,
        description="Number of consecutive failed login attempts",
    )

    last_login: Optional[datetime] = Field(
        default=None,
        description="Timestamp of last successful login (UTC)",
    )

    locked_until: Optional[datetime] = Field(
        default=None,
        description="Account locked until this timestamp (UTC)",
    )

    # -------- Métodos de estado (UTC-aware) --------

    def is_locked(self) -> bool:
        """Check if account is currently locked"""
        if self.locked_until is None:
            return False
        return datetime.now(timezone.utc) < self.locked_until

    def lock_account(self, duration_minutes: int = 30):
        """Lock account for specified duration"""
        self.locked_until = datetime.now(timezone.utc) + timedelta(minutes=duration_minutes)
        self.failed_login_attempts = 0

    def unlock_account(self):
        """Unlock the account"""
        self.locked_until = None
        self.failed_login_attempts = 0

    def record_failed_login(self):
        """Record a failed login attempt"""
        self.failed_login_attempts += 1
        if self.failed_login_attempts >= 5:
            self.lock_account()

    def record_successful_login(self):
        """Record a successful login"""
        self.last_login = datetime.now(timezone.utc)
        self.failed_login_attempts = 0
        self.locked_until = None

    # -------- Validadores / Normalización --------

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        v = v.strip()
        pattern = r"^[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}$"
        if not re.match(pattern, v):
            raise ValueError("Invalid email format")
        return v

    @field_validator("username")
    @classmethod
    def validate_username(cls, v: str) -> str:
        v = v.strip()
        if not re.match(r"^[A-Za-z0-9_-]+$", v):
            raise ValueError("Username can only contain letters, numbers, underscores, and hyphens")
        return v

    @field_validator("username_norm", mode="before")
    @classmethod
    def ensure_username_norm(cls, v: Optional[str], info) -> str:
        data = info.data or {}
        base = (v or data.get("username") or "").strip()
        if not base:
            raise ValueError("username_norm requires username")
        return base.lower()

    @field_validator("email_norm", mode="before")
    @classmethod
    def ensure_email_norm(cls, v: Optional[str], info) -> str:
        data = info.data or {}
        base = (v or data.get("email") or "").strip()
        if not base:
            raise ValueError("email_norm requires email")
        return base.lower()


class AuditLog(BaseModel, table=True):
    """
    Registro de auditoría para compliance
    Registra todas las acciones importantes del sistema
    """
    __tablename__ = "audit_log"  # Corregido para coincidir con la migración

    # Primary key
    id: Optional[int] = Field(default=None, primary_key=True)

    # Foreign keys
    user_id: Optional[int] = Field(default=None, foreign_key="users.id", index=True)

    # Audit fields
    action: str = Field(max_length=100, description="Action performed", index=True)
    table_name: Optional[str] = Field(max_length=50, description="Table affected by the action", index=True)
    record_id: Optional[int] = Field(default=None, description="ID of the affected record", index=True)

    old_values: Optional[str] = Field(default=None, description="JSON of old values")
    new_values: Optional[str] = Field(default=None, description="JSON of new values")

    ip_address: Optional[str] = Field(default=None, max_length=45, description="IP address of the user")
    user_agent: Optional[str] = Field(default=None, max_length=500, description="User agent string")

    def __str__(self):
        return f"AuditLog({self.action} by user {self.user_id} at {self.created_at})"

    # Helpers para JSON (útiles en SQLite; en Postgres usa JSON/JSONB)
    def set_old_values(self, data: dict) -> None:
        self.old_values = json.dumps(data, ensure_ascii=False)

    def set_new_values(self, data: dict) -> None:
        self.new_values = json.dumps(data, ensure_ascii=False)


# Register timestamp listeners for automatic updated_at handling
register_timestamp_listeners(User)
register_timestamp_listeners(AuditLog)