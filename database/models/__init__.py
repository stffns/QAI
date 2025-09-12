"""database.models
Declarative exports for core SQLModel entities used by QA Intelligence.

Cleaning goals:
- Remove large commented blocks that created noise in diffs.
- Export only models that are actually safe to import at app start.
- Keep optional OAuth models behind a best‑effort import so missing tables
  or partial environments don't break startup.
- Provide a minimal MODEL_REGISTRY used by migration/introspection utilities.
"""

from ..base import BaseModel  # Base mixin used across most models
from .users import User, AuditLog, UserRole  # Core user & audit trail

# Optional / modular models -------------------------------------------------
_oauth_models_loaded = False
try:  # OAuth models are optional and depend on recent migrations
    from .oauth import (
        OAuthUsers,
        OAuthJWKs,
        OAuthAppClients,
    )
    _oauth_models_loaded = True
except Exception:  # pragma: no cover - absence is acceptable
    # Silent: missing OAuth models should not block the rest of the system.
    pass

# Public exports ------------------------------------------------------------
__all__ = [
    "BaseModel",
    # Core
    "User",
    "AuditLog",
    "UserRole",
]

if _oauth_models_loaded:
    __all__.extend([
        "OAuthUsers",
        "OAuthJWKs",
        "OAuthAppClients",
    ])

# MODEL_REGISTRY kept intentionally small; tooling that needs discovery of
# optional families (RAG, Performance, etc.) should load them explicitly to
# avoid circular imports and startup cost.
MODEL_REGISTRY = ["User", "AuditLog"]
if _oauth_models_loaded:
    MODEL_REGISTRY.extend(["OAuthUsers", "OAuthJWKs", "OAuthAppClients"])
