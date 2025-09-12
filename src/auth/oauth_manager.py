"""
OAuth Manager for QA Intelligence
Manager principal que integra todos los componentes OAuth siguiendo el patrón SOLID del proyecto
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlmodel import Session

try:
    from database.connection import db_manager
    from database.repositories import create_unit_of_work_factory
    from src.logging_config import get_logger

    from .models.oauth_models import (
        OAuthApplication,
        OAuthCountry,
        OAuthEnvironment,
        OAuthEnvironmentConfig,
        OAuthJWK,
        OAuthProduct,
        OAuthToken,
        OAuthUser,
    )
    from .repositories.oauth_repositories import (
        OAuthApplicationRepository,
        OAuthCountryRepository,
        OAuthEnvironmentConfigRepository,
        OAuthJWKRepository,
        OAuthTokenRepository,
        OAuthUserRepository,
    )
    from .services.oauth_service import (
        OAuthConfig,
        OAuthServiceFactory,
        OAuthTokenService,
    )
except ImportError:
    import os
    import sys

    sys.path.append(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
    from database.connection import db_manager
    from database.repositories import create_unit_of_work_factory
    from src.auth.models.oauth_models import (
        OAuthApplication,
        OAuthCountry,
        OAuthEnvironment,
        OAuthEnvironmentConfig,
        OAuthJWK,
        OAuthProduct,
        OAuthToken,
        OAuthUser,
    )
    from src.auth.repositories.oauth_repositories import (
        OAuthApplicationRepository,
        OAuthCountryRepository,
        OAuthEnvironmentConfigRepository,
        OAuthJWKRepository,
        OAuthTokenRepository,
        OAuthUserRepository,
    )
    from src.auth.services.oauth_service import (
        OAuthConfig,
        OAuthServiceFactory,
        OAuthTokenService,
    )
    from src.logging_config import get_logger


logger = get_logger("OAuthManager")


class OAuthManager:
    """
    Manager principal para OAuth/OIDC siguiendo el patrón SOLID del proyecto

    Funcionalidades:
    - Gestión de usuarios OAuth para testing
    - Configuración de aplicaciones por ambiente/país/producto
    - Generación de access tokens para pruebas Gatling
    - Auditoría de tokens generados
    - Configuración dinámica vs datos hardcoded
    """

    def __init__(self, session: Session):
        self.session = session

        # Inicializar repositorios
        self.user_repo = OAuthUserRepository(session)
        self.app_repo = OAuthApplicationRepository(session)
        self.country_repo = OAuthCountryRepository(session)
        self.jwk_repo = OAuthJWKRepository(session)
        self.env_repo = OAuthEnvironmentConfigRepository(session)
        self.token_repo = OAuthTokenRepository(session)

        # Inicializar servicio OAuth
        self.oauth_service = OAuthServiceFactory.create_oauth_service(
            self.user_repo,
            self.app_repo,
            self.jwk_repo,
            self.env_repo,
            self.token_repo,
        )

    # ========== Métodos principales (equivalentes al código Scala) ==========

    async def get_access_token(
        self,
        environment: str,
        country: str,
        product: str,
        test_name: Optional[str] = None,
    ) -> str:
        """
        Obtiene un access token para testing

        Equivalente a: OIDCAuthentication.getAccessToken()

        Args:
            environment: sta, uat, prod
            country: mx, cl, co, etc.
            product: one-app, m-app, eva, etc.
            test_name: Nombre del test para auditoría

        Returns:
            Access token para usar en las pruebas
        """
        try:
            # Convertir strings a enums
            env = OAuthEnvironment(environment.lower())
            prod = OAuthProduct(product.lower())

            logger.info(f"Getting access token for {environment}/{country}/{product}")

            token = await self.oauth_service.get_access_token(
                env, country.lower(), prod, test_name
            )

            logger.info(
                f"Successfully obtained access token for {environment}/{country}/{product}"
            )
            return token

        except Exception as e:
            logger.error(f"Failed to get access token: {e}")
            raise

    def get_user_config(
        self,
        environment: str,
        country: str,
        product: str,
    ) -> Optional[OAuthUser]:
        """
        Obtiene la configuración de usuario para testing

        Equivalente a: UserMap.get()
        """
        try:
            env = OAuthEnvironment(environment.lower())
            prod = OAuthProduct(product.lower())

            return self.user_repo.get_by_config(env, country.lower(), prod)

        except Exception as e:
            logger.error(f"Failed to get user config: {e}")
            return None

    def get_application_config(
        self,
        environment: str,
        country: str,
        product: str,
    ) -> Optional[OAuthApplication]:
        """
        Obtiene la configuración de aplicación

        Equivalente a: ClientIdMap.get()
        """
        try:
            env = OAuthEnvironment(environment.lower())
            prod = OAuthProduct(product.lower())

            return self.app_repo.get_by_config(env, country.lower(), prod)

        except Exception as e:
            logger.error(f"Failed to get application config: {e}")
            return None

    def get_jwk_config(self, environment: str) -> Optional[OAuthJWK]:
        """
        Obtiene la configuración JWK

        Equivalente a: JwkMap.get()
        """
        try:
            env = OAuthEnvironment(environment.lower())
            return self.jwk_repo.get_by_environment(env)

        except Exception as e:
            logger.error(f"Failed to get JWK config: {e}")
            return None

    # ========== Métodos de gestión de datos ==========

    def list_available_configs(self) -> Dict[str, List[Dict[str, str]]]:
        """Lista todas las configuraciones disponibles"""
        configs = []

        try:
            users = (
                self.session.query(OAuthUser).filter(OAuthUser.is_active == True).all()
            )

            for user in users:
                configs.append(
                    {
                        "environment": user.environment.value,
                        "country": user.country_code,
                        "product": user.product.value,
                        "user_email": user.email,
                        "user_name": f"{user.given_name} {user.family_name}",
                    }
                )

            return {"available_configs": configs}

        except Exception as e:
            logger.error(f"Failed to list configs: {e}")
            return {"available_configs": []}

    def get_token_audit_history(
        self,
        limit: int = 50,
        environment: Optional[str] = None,
        country: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Obtiene historial de tokens generados"""
        try:
            query = self.session.query(OAuthToken).order_by(
                OAuthToken.created_at.desc()
            )

            if environment or country:
                query = query.join(OAuthUser)
                if environment:
                    env = OAuthEnvironment(environment.lower())
                    query = query.filter(OAuthUser.environment == env)
                if country:
                    query = query.filter(OAuthUser.country_code == country.lower())

            tokens = query.limit(limit).all()

            history = []
            for token in tokens:
                history.append(
                    {
                        "id": token.id,
                        "token_type": token.token_type.value,
                        "created_at": token.created_at.isoformat(),
                        "expires_at": (
                            token.expires_at.isoformat() if token.expires_at else None
                        ),
                        "user_email": token.user.email if token.user else None,
                        "application_name": (
                            token.application.name if token.application else None
                        ),
                        "generated_for_test": token.generated_for_test,
                        "is_revoked": token.is_revoked,
                    }
                )

            return history

        except Exception as e:
            logger.error(f"Failed to get token history: {e}")
            return []

    def cleanup_expired_tokens(self) -> int:
        """Limpia tokens expirados"""
        try:
            count = self.token_repo.cleanup_expired_tokens()
            logger.info(f"Cleaned up {count} expired tokens")
            return count

        except Exception as e:
            logger.error(f"Failed to cleanup tokens: {e}")
            return 0

    # ========== Métodos de configuración ==========

    def add_test_user(
        self,
        email: str,
        given_name: str,
        family_name: str,
        phone_number: str,
        gender: str,
        password: str,
        environment: str,
        country: str,
        product: str,
        test_purpose: Optional[str] = None,
    ) -> OAuthUser:
        """Agrega un nuevo usuario de testing"""
        try:
            import hashlib

            password_hash = hashlib.sha256(password.encode()).hexdigest()

            env = OAuthEnvironment(environment.lower())
            prod = OAuthProduct(product.lower())

            user = self.user_repo.create_user(
                email=email,
                given_name=given_name,
                family_name=family_name,
                phone_number=phone_number,
                gender=gender,
                password_hash=password_hash,
                environment=env,
                country_code=country.lower(),
                product=prod,
                test_purpose=test_purpose,
            )

            logger.info(f"Added test user: {email}")
            return user

        except Exception as e:
            logger.error(f"Failed to add test user: {e}")
            raise

    def add_oauth_application(
        self,
        client_id: str,
        name: str,
        environment: str,
        country: str,
        product: str,
        callback_url: str,
        resource_url: Optional[str] = None,
        needs_resource_param: bool = False,
    ) -> OAuthApplication:
        """Agrega una nueva aplicación OAuth"""
        try:
            env = OAuthEnvironment(environment.lower())
            prod = OAuthProduct(product.lower())

            app = self.app_repo.create_application(
                client_id=client_id,
                name=name,
                environment=env,
                country_code=country.lower(),
                product=prod,
                callback_url=callback_url,
                resource_url=resource_url,
                needs_resource_param=needs_resource_param,
            )

            logger.info(f"Added OAuth application: {name}")
            return app

        except Exception as e:
            logger.error(f"Failed to add OAuth application: {e}")
            raise


class OAuthManagerFactory:
    """Factory para crear OAuthManager configurado"""

    @staticmethod
    def create_manager(session: Optional[Session] = None) -> OAuthManager:
        """Crea un OAuthManager con la configuración del proyecto"""
        if not session:
            session = Session(db_manager.engine)

        return OAuthManager(session)

    @staticmethod
    def create_with_unit_of_work():
        """Crea un manager usando el patrón Unit of Work del proyecto"""
        # Usar session directa por ahora
        session = Session(db_manager.engine)
        return OAuthManager(session)
