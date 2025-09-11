# QA Intelligence - Authentication Module
"""
Authentication module for QA Intelligence platform.

This module provides OAuth/OIDC authentication for testing scenarios
and various authentication methods and middleware for securing the QA workflows.
"""

from .models.oauth_models import (
    OAuthUser,
    OAuthApplication,
    OAuthCountry,
    OAuthJWK,
    OAuthEnvironmentConfig,
    OAuthToken,
    OAuthEnvironment,
    OAuthProduct,
    Gender,
    TokenType,
)

try:
    from .services.oauth_service import (
        OAuthTokenService,
        OAuthConfigService,
        OAuthServiceFactory,
        OAuthConfig,
    )
except ImportError:
    # Services might not be available if dependencies are missing
    pass

__version__ = "1.0.0"

__all__ = [
    # Models
    "OAuthUser",
    "OAuthApplication", 
    "OAuthCountry",
    "OAuthJWK",
    "OAuthEnvironmentConfig",
    "OAuthToken",
    "OAuthEnvironment",
    "OAuthProduct", 
    "Gender",
    "TokenType",
]
