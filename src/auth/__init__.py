# QA Intelligence - Authentication Module
"""
Authentication module for QA Intelligence platform.

This module provides OAuth/OIDC authentication for testing scenarios
and various authentication methods and middleware for securing the QA workflows.
"""

# Import modern consolidated OAuth models
try:
    from database.models.oauth import OAuthAppClients as OAuthApplication
    from database.models.oauth import OAuthJWKs as OAuthJWK
    from database.models.oauth import OAuthUsers as OAuthUser
except ImportError:  # pragma: no cover
    OAuthUser = OAuthApplication = OAuthJWK = None  # type: ignore

# Legacy enums / types no longer provided here; keep placeholders for compatibility
OAuthCountry = None  # Removed legacy model
OAuthEnvironmentConfig = None  # Removed legacy model
OAuthToken = None  # Token history model not migrated yet
OAuthEnvironment = None  # Use config enums elsewhere if needed
OAuthProduct = None
Gender = None
TokenType = None

try:
    from .services.oauth_service import (
        OAuthConfig,
        OAuthConfigService,
        OAuthServiceFactory,
        OAuthTokenService,
    )
except ImportError:
    # Services might not be available if dependencies are missing
    pass

__version__ = "1.0.0"

__all__ = [
    # Models
    "OAuthUser",
    "OAuthApplication",
    "OAuthJWK",
]
