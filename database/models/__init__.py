"""database.models
Declarative exports for core SQLModel entities used by QA Intelligence.

Clean architecture with normalized application endpoints structure.
"""

from ..base import BaseModel  # Base mixin used across most models
from .users import User, AuditLog, UserRole  # Core user & audit trail

# Core application models ---------------------------------------------------
from .apps import Apps
from .environments import Environments  
from .countries import Countries
from .app_environment_country_mappings import AppEnvironmentCountryMapping
from .application_endpoints import ApplicationEndpoint  # Clean structure with mapping_id only

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
    # Core user models
    "User",
    "AuditLog", 
    "UserRole",
    # Core application models (clean architecture)
    "Apps",
    "Environments",
    "Countries", 
    "AppEnvironmentCountryMapping",
    "ApplicationEndpoint",  # Clean structure
]

if _oauth_models_loaded:
    __all__.extend([
        "OAuthUsers",
        "OAuthJWKs",
        "OAuthAppClients",
    ])

# MODEL_REGISTRY with clean application models
MODEL_REGISTRY = [
    "User", "AuditLog", "Apps", "Environments", "Countries", 
    "AppEnvironmentCountryMapping", "ApplicationEndpoint"
]
if _oauth_models_loaded:
    MODEL_REGISTRY.extend(["OAuthUsers", "OAuthJWKs", "OAuthAppClients"])
