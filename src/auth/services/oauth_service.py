"""
OAuth Services for QA Intelligence
Servicios para gestión de autenticación OIDC y generación de tokens
"""

from __future__ import annotations

import base64
import hashlib
import json
import secrets
import urllib.parse
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

import httpx

try:
    from database.repositories.exceptions import EntityNotFoundError
    from src.logging_config import get_logger

    from ..models.oauth_models import (
        OAuthApplication,
        OAuthEnvironment,
        OAuthEnvironmentConfig,
        OAuthJWK,
        OAuthProduct,
        OAuthToken,
        OAuthUser,
        TokenType,
    )
    from ..repositories.oauth_repositories import (
        OAuthApplicationRepository,
        OAuthEnvironmentConfigRepository,
        OAuthJWKRepository,
        OAuthTokenRepository,
        OAuthUserRepository,
    )
except ImportError:
    import os
    import sys

    sys.path.append(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
    from database.repositories.exceptions import EntityNotFoundError
    from src.auth.models.oauth_models import (
        OAuthApplication,
        OAuthEnvironment,
        OAuthEnvironmentConfig,
        OAuthJWK,
        OAuthProduct,
        OAuthToken,
        OAuthUser,
        TokenType,
    )
    from src.auth.repositories.oauth_repositories import (
        OAuthApplicationRepository,
        OAuthEnvironmentConfigRepository,
        OAuthJWKRepository,
        OAuthTokenRepository,
        OAuthUserRepository,
    )
    from src.logging_config import get_logger


logger = get_logger("OAuthService")


@dataclass
class OAuthConfig:
    """Configuración compilada para OAuth"""

    environment: OAuthEnvironment
    country_code: str
    product: OAuthProduct

    # Usuario
    user: OAuthUser

    # Aplicación
    application: OAuthApplication

    # Configuración del ambiente
    environment_config: OAuthEnvironmentConfig

    # JWK
    jwk: OAuthJWK

    @property
    def issuer(self) -> str:
        return self.environment_config.issuer

    @property
    def oidc_domain(self) -> str:
        return self.environment_config.oidc_domain

    @property
    def client_id(self) -> str:
        return self.application.client_id

    @property
    def callback_url(self) -> str:
        return self.application.callback_url

    @property
    def needs_resource_param(self) -> bool:
        return self.application.needs_resource_param

    @property
    def resource_url(self) -> str:
        return self.application.resource_url or ""

    @property
    def key_id(self) -> str:
        return self.jwk.key_id


class OAuthConfigService:
    """Servicio para compilar configuraciones OAuth dinámicamente"""

    def __init__(
        self,
        user_repo: OAuthUserRepository,
        app_repo: OAuthApplicationRepository,
        jwk_repo: OAuthJWKRepository,
        env_repo: OAuthEnvironmentConfigRepository,
    ):
        self.user_repo = user_repo
        self.app_repo = app_repo
        self.jwk_repo = jwk_repo
        self.env_repo = env_repo

    def get_config(
        self,
        environment: OAuthEnvironment,
        country_code: str,
        product: OAuthProduct,
    ) -> OAuthConfig:
        """Compila la configuración OAuth completa"""
        logger.info(f"Building OAuth config for {environment}/{country_code}/{product}")

        # Obtener usuario
        user = self.user_repo.get_by_config(environment, country_code, product)
        if not user:
            raise EntityNotFoundError(
                "OAuthUser", "config", f"{environment}/{country_code}/{product}"
            )

        # Obtener aplicación
        application = self.app_repo.get_by_config(environment, country_code, product)
        if not application:
            raise EntityNotFoundError(
                "OAuthApplication", "config", f"{environment}/{country_code}/{product}"
            )

        # Obtener configuración de ambiente
        env_config = self.env_repo.get_by_environment(environment)
        if not env_config:
            raise EntityNotFoundError(
                "OAuthEnvironmentConfig", "environment", environment.value
            )

        # Obtener JWK
        jwk = self.jwk_repo.get_by_environment(environment)
        if not jwk:
            raise EntityNotFoundError("OAuthJWK", "environment", environment.value)

        return OAuthConfig(
            environment=environment,
            country_code=country_code,
            product=product,
            user=user,
            application=application,
            environment_config=env_config,
            jwk=jwk,
        )


class PKCEService:
    """Servicio para generar códigos PKCE"""

    @staticmethod
    def generate_code_verifier() -> str:
        """Genera un code_verifier para PKCE"""
        return (
            base64.urlsafe_b64encode(secrets.token_bytes(32))
            .decode("utf-8")
            .rstrip("=")
        )

    @staticmethod
    def generate_code_challenge(verifier: str) -> str:
        """Genera code_challenge a partir del verifier"""
        digest = hashlib.sha256(verifier.encode("utf-8")).digest()
        return base64.urlsafe_b64encode(digest).decode("utf-8").rstrip("=")


class OIDCProviderService:
    """Servicio para interactuar con proveedores OIDC"""

    def __init__(self):
        self.client = httpx.AsyncClient(timeout=30.0)

    async def get_provider_metadata(self, issuer: str) -> Dict[str, Any]:
        """Obtiene metadatos del proveedor OIDC"""
        url = f"{issuer}/.well-known/openid-configuration"
        logger.info(f"Fetching OIDC metadata from {url}")

        response = await self.client.get(url)
        response.raise_for_status()
        return response.json()

    def generate_authorization_url(
        self,
        config: OAuthConfig,
        code_verifier: str,
        state: Optional[str] = None,
    ) -> str:
        """Genera URL de autorización"""
        code_challenge = PKCEService.generate_code_challenge(code_verifier)

        params = {
            "response_type": "code",
            "client_id": config.client_id,
            "redirect_uri": config.callback_url,
            "scope": "openid profile email",
            "code_challenge": code_challenge,
            "code_challenge_method": "S256",
        }

        if state:
            params["state"] = state

        auth_endpoint = f"https://{config.oidc_domain}/op/authorization"
        query_string = urllib.parse.urlencode(params)
        return f"{auth_endpoint}?{query_string}"

    async def exchange_code_for_tokens(
        self,
        token_endpoint: str,
        code: str,
        code_verifier: str,
        config: OAuthConfig,
    ) -> Dict[str, Any]:
        """Intercambia authorization code por tokens"""
        data = {
            "grant_type": "authorization_code",
            "code": code,
            "client_id": config.client_id,
            "redirect_uri": config.callback_url,
            "code_verifier": code_verifier,
        }

        if config.needs_resource_param and config.resource_url:
            data["resource"] = config.resource_url

        logger.info(f"Exchanging code for tokens at {token_endpoint}")
        response = await self.client.post(token_endpoint, data=data)
        response.raise_for_status()
        return response.json()


class ImpersonationService:
    """Servicio para generar tokens de impersonación"""

    def __init__(self, jwk_repo: OAuthJWKRepository):
        self.jwk_repo = jwk_repo

    def generate_impersonation_token(
        self,
        config: OAuthConfig,
        authorization_endpoint: str,
    ) -> str:
        """
        Genera token de impersonación JWT

        NOTA: Esta es una implementación simplificada.
        En producción necesitarías una librería JWT completa como PyJWT
        """
        logger.info(f"Generating impersonation token for {config.user.email}")

        # Header JWT
        header = {
            "alg": "RS256",
            "typ": "JWT",
            "kid": config.key_id,
        }

        # Payload con información del usuario
        now = datetime.utcnow()
        exp = now + timedelta(minutes=5)  # Token de corta duración

        payload = {
            "iss": config.issuer,
            "sub": config.user.email,
            "aud": authorization_endpoint,
            "exp": int(exp.timestamp()),
            "iat": int(now.timestamp()),
            "given_name": config.user.given_name,
            "family_name": config.user.family_name,
            "email": config.user.email,
            "phone_number": config.user.phone_number,
            "gender": config.user.gender,
        }

        # En una implementación real, aquí firmarías con la clave privada JWK
        # Por ahora retornamos un token mock
        token_data = f"{header}.{payload}"
        return base64.urlsafe_b64encode(token_data.encode()).decode().rstrip("=")


class OAuthTokenService:
    """Servicio principal para generación de tokens OAuth"""

    def __init__(
        self,
        config_service: OAuthConfigService,
        provider_service: OIDCProviderService,
        impersonation_service: ImpersonationService,
        token_repo: OAuthTokenRepository,
    ):
        self.config_service = config_service
        self.provider_service = provider_service
        self.impersonation_service = impersonation_service
        self.token_repo = token_repo

    async def get_access_token(
        self,
        environment: OAuthEnvironment,
        country_code: str,
        product: OAuthProduct,
        test_name: Optional[str] = None,
    ) -> str:
        """
        Obtiene un access token para testing

        Este es el método principal que replica la funcionalidad del código Scala
        """
        logger.info(f"Getting access token for {environment}/{country_code}/{product}")

        # 1. Compilar configuración
        config = self.config_service.get_config(environment, country_code, product)

        # 2. Obtener metadatos del proveedor
        provider_metadata = await self.provider_service.get_provider_metadata(
            config.issuer
        )

        # 3. Generar código PKCE
        code_verifier = PKCEService.generate_code_verifier()

        # 4. Generar URL de autorización
        auth_url = self.provider_service.generate_authorization_url(
            config, code_verifier
        )

        # 5. Generar token de impersonación
        impersonation_token = self.impersonation_service.generate_impersonation_token(
            config, provider_metadata["authorization_endpoint"]
        )

        # 6. Simular obtención del authorization code
        # En el código Scala real esto implica interactuar con el navegador
        authorization_code = self._simulate_authorization_flow(
            config, auth_url, impersonation_token
        )

        # 7. Intercambiar código por tokens
        token_response = await self.provider_service.exchange_code_for_tokens(
            provider_metadata["token_endpoint"],
            authorization_code,
            code_verifier,
            config,
        )

        access_token = token_response["access_token"]

        # 8. Guardar en auditoría
        await self._save_token_audit(
            TokenType.ACCESS_TOKEN,
            access_token,
            config,
            token_response.get("expires_in"),
            test_name,
        )

        logger.info(f"Successfully obtained access token for {config.user.email}")
        return access_token

    def _simulate_authorization_flow(
        self, config: OAuthConfig, auth_url: str, impersonation_token: str
    ) -> str:
        """
        Simula el flujo de autorización

        En el código Scala real esto usa Selenium/navegador
        Por ahora retornamos un código mock
        """
        logger.info("Simulating authorization flow")
        # En implementación real aquí iría la lógica de Selenium
        return "mock_authorization_code_" + secrets.token_urlsafe(16)

    async def _save_token_audit(
        self,
        token_type: TokenType,
        token: str,
        config: OAuthConfig,
        expires_in: Optional[int],
        test_name: Optional[str],
    ):
        """Guarda auditoría del token generado"""
        # Hash del token para auditoría (no guardamos el token real)
        token_hash = hashlib.sha256(token.encode()).hexdigest()

        expires_at = None
        if expires_in:
            expires_at = datetime.utcnow() + timedelta(seconds=expires_in)

        self.token_repo.create_token(
            token_type=token_type,
            token_hash=token_hash,
            user_id=config.user.id,
            application_id=config.application.id,
            expires_at=expires_at,
            generated_for_test=test_name,
        )


class OAuthServiceFactory:
    """Factory para crear servicios OAuth configurados"""

    @staticmethod
    def create_oauth_service(
        user_repo: OAuthUserRepository,
        app_repo: OAuthApplicationRepository,
        jwk_repo: OAuthJWKRepository,
        env_repo: OAuthEnvironmentConfigRepository,
        token_repo: OAuthTokenRepository,
    ) -> OAuthTokenService:
        """Crea un servicio OAuth completamente configurado"""
        config_service = OAuthConfigService(user_repo, app_repo, jwk_repo, env_repo)
        provider_service = OIDCProviderService()
        impersonation_service = ImpersonationService(jwk_repo)

        return OAuthTokenService(
            config_service,
            provider_service,
            impersonation_service,
            token_repo,
        )
