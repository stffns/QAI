"""
Base models and mixins for QA Intelligence
Provides common functionality for all SQLModel models (Pydantic v2)
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional, Any, Dict

from sqlmodel import SQLModel, Field
from pydantic import field_validator

# --- Mixins (no-table) -------------------------------------------------------

class TimestampMixin(SQLModel, table=False):
    """Campos de auditoría temporal (UTC)."""
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc), index=True
    )
    updated_at: Optional[datetime] = Field(default=None, index=True)

class AuditMixin(SQLModel, table=False):
    """Campos de auditoría de usuario."""
    created_by: Optional[int] = Field(default=None, foreign_key="users.id")
    updated_by: Optional[int] = Field(default=None, foreign_key="users.id")
    is_active: bool = Field(default=True, index=True)

# --- Base abstracta ----------------------------------------------------------

class BaseModel(TimestampMixin, AuditMixin, table=False):
    """
    Modelo base con auditoría completa: timestamps + usuario + estado.
    No crea tabla por sí misma (table=False).
    """

    # Pydantic v2: solo validar formateo si viene string (defensive).
    @field_validator("created_at", "updated_at", mode="before")
    @classmethod
    def _ensure_datetime_tz(cls, v: Any) -> Any:
        if v is None:
            return v
        if isinstance(v, str):
            # intenta parsear ISO; si ya viene datetime, se respeta
            try:
                parsed = datetime.fromisoformat(v)
                if parsed.tzinfo is None:
                    parsed = parsed.replace(tzinfo=timezone.utc)
                return parsed
            except Exception:
                # deja que pydantic lance su error si no puede parsear
                return v
        if isinstance(v, datetime) and v.tzinfo is None:
            return v.replace(tzinfo=timezone.utc)
        return v

    def dict_for_audit(self) -> Dict[str, Any]:
        """Representación segura/serializada para logs/auditoría."""
        data = self.model_dump()  # pydantic v2
        for k, v in list(data.items()):
            if isinstance(v, datetime):
                data[k] = v.isoformat()
        return data

# --- Hooks de SQLAlchemy para mantener updated_at ----------------------------
# Úsalos tras definir tus modelos concretos (table=True) y antes de usar el engine.

from sqlalchemy import event
from sqlalchemy.orm import Mapper

def _set_timestamps_on_insert(mapper: Mapper, connection, target):
    if isinstance(target, TimestampMixin):
        now = datetime.now(timezone.utc)
        if target.created_at is None:
            target.created_at = now
        # si no está definido, inicializa updated_at = created_at
        if target.updated_at is None:
            target.updated_at = target.created_at

def _set_updated_on_update(mapper: Mapper, connection, target):
    if isinstance(target, TimestampMixin):
        target.updated_at = datetime.now(timezone.utc)

def register_timestamp_listeners(model_cls: type[SQLModel]) -> None:
    """
    Registra listeners para un modelo concreto (table=True).
    Llama a esta función por cada modelo que herede de BaseModel/TimestampMixin.
    """
    event.listen(model_cls, "before_insert", _set_timestamps_on_insert)
    event.listen(model_cls, "before_update", _set_updated_on_update)

# --- Configuración (referencial) ---------------------------------------------

class DatabaseConfig:
    """Configuración global para DB (aplicada al crear el engine)."""

    # SQLite PRAGMAs (aplícalos al crear el engine con connect_args / init_command)
    SQLITE_PRAGMAS = {
        "journal_mode": "WAL",
        "cache_size": -64000,       # 64 MB (en páginas negativas -> KB; válido para SQLite)
        "foreign_keys": 1,
        "ignore_check_constraints": 0,
        "synchronous": 1,           # NORMAL
    }

    # Parámetros típicos para PostgreSQL (cuando migres)
    POSTGRES_POOL_SIZE = 20
    POSTGRES_MAX_OVERFLOW = 0
    POSTGRES_POOL_PRE_PING = True