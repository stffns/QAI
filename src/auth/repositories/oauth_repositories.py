"""
OAuth Repositories for QA Intelligence
Implementa el patrón Repository para gestión de datos OAuth/OIDC
Sigue los principios SOLID del proyecto
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

try:
    from database.repositories.base import BaseRepository
    from database.repositories.exceptions import (
        DuplicateEntityError,
        EntityNotFoundError,
        InvalidEntityError,
    )

    from ..models.oauth_models import (
        OAuthApplication,
        OAuthCountry,
        OAuthEnvironment,
        OAuthEnvironmentConfig,
        OAuthJWK,
        OAuthProduct,
        OAuthToken,
        OAuthUser,
    )
except ImportError:
    import os
    import sys

    sys.path.append(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
    from database.repositories.base import BaseRepository
    from database.repositories.exceptions import (
        DuplicateEntityError,
        EntityNotFoundError,
        InvalidEntityError,
    )
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


class OAuthCountryRepository(BaseRepository[OAuthCountry]):
    """Repository para gestión de países OAuth"""

    def __init__(self, session: Session):
        super().__init__(session, OAuthCountry)

    def get_by_code(self, code: str) -> Optional[OAuthCountry]:
        """Obtiene un país por su código"""
        statement = select(self.model_class).where(
            self.model_class.code == code.lower()
        )
        return self.session.exec(statement).first()

    def get_active_countries(self) -> List[OAuthCountry]:
        """Obtiene todos los países activos"""
        statement = select(self.model_class).where(self.model_class.is_active == True)
        return list(self.session.exec(statement).all())

    def create_country(self, code: str, name: str, locale: str) -> OAuthCountry:
        """Crea un nuevo país"""
        existing = self.get_by_code(code)
        if existing:
            raise DuplicateEntityError("OAuthCountry", "code", code)

        country = OAuthCountry(
            code=code.lower(),
            name=name,
            locale=locale,
        )
        return self.save(country)


class OAuthUserRepository(BaseRepository[OAuthUser]):
    """Repository para gestión de usuarios OAuth"""

    def __init__(self, session: Session):
        super().__init__(session, OAuthUser)

    def get_by_config(
        self,
        environment: OAuthEnvironment,
        country_code: str,
        product: OAuthProduct,
    ) -> Optional[OAuthUser]:
        """Obtiene un usuario por configuración de ambiente/país/producto"""
        statement = select(self.model).where(
            self.model.environment == environment,
            self.model.country_code == country_code.lower(),
            self.model.product == product,
            self.model.is_active == True,
        )
        return self.session.exec(statement).first()

    def get_by_email(self, email: str) -> Optional[OAuthUser]:
        """Obtiene un usuario por email"""
        statement = select(self.model).where(self.model.email == email)
        return self.session.exec(statement).first()

    def get_users_by_environment(
        self, environment: OAuthEnvironment
    ) -> List[OAuthUser]:
        """Obtiene todos los usuarios activos de un ambiente"""
        statement = select(self.model).where(
            self.model.environment == environment,
            self.model.is_active == True,
        )
        return list(self.session.exec(statement).all())

    def get_users_by_product(self, product: OAuthProduct) -> List[OAuthUser]:
        """Obtiene todos los usuarios de un producto"""
        statement = select(self.model).where(
            self.model.product == product,
            self.model.is_active == True,
        )
        return list(self.session.exec(statement).all())

    def create_user(
        self,
        email: str,
        given_name: str,
        family_name: str,
        phone_number: str,
        gender: str,
        password_hash: str,
        environment: OAuthEnvironment,
        country_code: str,
        product: OAuthProduct,
        test_purpose: Optional[str] = None,
    ) -> OAuthUser:
        """Crea un nuevo usuario OAuth"""
        existing = self.get_by_email(email)
        if existing:
            raise DuplicateEntityError(f"User with email {email} already exists")

        user = OAuthUser(
            email=email,
            given_name=given_name,
            family_name=family_name,
            phone_number=phone_number,
            gender=gender,
            password_hash=password_hash,
            environment=environment,
            country_code=country_code.lower(),
            product=product,
            test_purpose=test_purpose,
        )
        return self.create(user)

    def deactivate_user(self, user_id: int) -> OAuthUser:
        """Desactiva un usuario"""
        user = self.get_by_id(user_id)
        if not user:
            raise EntityNotFoundError(f"User with id {user_id} not found")

        user.is_active = False
        user.updated_at = datetime.utcnow()
        return self.update(user)


class OAuthApplicationRepository(BaseRepository[OAuthApplication]):
    """Repository para gestión de aplicaciones OAuth"""

    def __init__(self, session: Session):
        super().__init__(session, OAuthApplication)

    def get_by_client_id(self, client_id: str) -> Optional[OAuthApplication]:
        """Obtiene una aplicación por client_id"""
        statement = select(self.model).where(self.model.client_id == client_id)
        return self.session.exec(statement).first()

    def get_by_config(
        self,
        environment: OAuthEnvironment,
        country_code: str,
        product: OAuthProduct,
    ) -> Optional[OAuthApplication]:
        """Obtiene una aplicación por configuración"""
        statement = select(self.model).where(
            self.model.environment == environment,
            self.model.country_code == country_code.lower(),
            self.model.product == product,
            self.model.is_active == True,
        )
        return self.session.exec(statement).first()

    def get_applications_by_environment(
        self, environment: OAuthEnvironment
    ) -> List[OAuthApplication]:
        """Obtiene todas las aplicaciones activas de un ambiente"""
        statement = select(self.model).where(
            self.model.environment == environment,
            self.model.is_active == True,
        )
        return list(self.session.exec(statement).all())

    def create_application(
        self,
        client_id: str,
        name: str,
        environment: OAuthEnvironment,
        country_code: str,
        product: OAuthProduct,
        callback_url: str,
        resource_url: Optional[str] = None,
        needs_resource_param: bool = False,
    ) -> OAuthApplication:
        """Crea una nueva aplicación OAuth"""
        existing = self.get_by_client_id(client_id)
        if existing:
            raise DuplicateEntityError(
                f"Application with client_id {client_id} already exists"
            )

        application = OAuthApplication(
            client_id=client_id,
            name=name,
            environment=environment,
            country_code=country_code.lower(),
            product=product,
            callback_url=callback_url,
            resource_url=resource_url,
            needs_resource_param=needs_resource_param,
        )
        return self.create(application)


class OAuthJWKRepository(BaseRepository[OAuthJWK]):
    """Repository para gestión de claves JWK"""

    def __init__(self, session: Session):
        super().__init__(session, OAuthJWK)

    def get_by_environment(self, environment: OAuthEnvironment) -> Optional[OAuthJWK]:
        """Obtiene la clave JWK activa de un ambiente"""
        statement = select(self.model).where(
            self.model.environment == environment,
            self.model.is_active == True,
        )
        return self.session.exec(statement).first()

    def get_active_jwks(self) -> List[OAuthJWK]:
        """Obtiene todas las claves JWK activas"""
        statement = select(self.model).where(self.model.is_active == True)
        return list(self.session.exec(statement).all())

    def create_jwk(
        self,
        environment: OAuthEnvironment,
        key_id: str,
        jwk_content: str,
        expires_at: Optional[datetime] = None,
    ) -> OAuthJWK:
        """Crea una nueva clave JWK"""
        # Desactivar claves anteriores del mismo ambiente
        existing = self.get_by_environment(environment)
        if existing:
            existing.is_active = False
            self.update(existing)

        jwk = OAuthJWK(
            environment=environment,
            key_id=key_id,
            jwk_content=jwk_content,
            expires_at=expires_at,
        )
        return self.create(jwk)


class OAuthEnvironmentConfigRepository(BaseRepository[OAuthEnvironmentConfig]):
    """Repository para configuración de ambientes"""

    def __init__(self, session: Session):
        super().__init__(session, OAuthEnvironmentConfig)

    def get_by_environment(
        self, environment: OAuthEnvironment
    ) -> Optional[OAuthEnvironmentConfig]:
        """Obtiene la configuración de un ambiente"""
        statement = select(self.model).where(
            self.model.environment == environment,
            self.model.is_active == True,
        )
        return self.session.exec(statement).first()

    def create_environment_config(
        self,
        environment: OAuthEnvironment,
        oidc_domain: str,
        issuer: str,
    ) -> OAuthEnvironmentConfig:
        """Crea configuración de ambiente"""
        existing = self.get_by_environment(environment)
        if existing:
            raise DuplicateEntityError(
                f"Environment config for {environment} already exists"
            )

        config = OAuthEnvironmentConfig(
            environment=environment,
            oidc_domain=oidc_domain,
            issuer=issuer,
        )
        return self.create(config)


class OAuthTokenRepository(BaseRepository[OAuthToken]):
    """Repository para gestión de tokens OAuth"""

    def __init__(self, session: Session):
        super().__init__(session, OAuthToken)

    def get_tokens_by_user(self, user_id: int) -> List[OAuthToken]:
        """Obtiene todos los tokens de un usuario"""
        statement = select(self.model).where(
            self.model.user_id == user_id,
            self.model.is_revoked == False,
        )
        return list(self.session.exec(statement).all())

    def get_tokens_by_application(self, application_id: int) -> List[OAuthToken]:
        """Obtiene todos los tokens de una aplicación"""
        statement = select(self.model).where(
            self.model.application_id == application_id,
            self.model.is_revoked == False,
        )
        return list(self.session.exec(statement).all())

    def get_active_tokens(self) -> List[OAuthToken]:
        """Obtiene todos los tokens activos (no expirados ni revocados)"""
        now = datetime.utcnow()
        statement = select(self.model).where(
            self.model.is_revoked == False,
            (self.model.expires_at.is_(None)) | (self.model.expires_at > now),
        )
        return list(self.session.exec(statement).all())

    def create_token(
        self,
        token_type: str,
        token_hash: str,
        user_id: Optional[int] = None,
        application_id: Optional[int] = None,
        expires_at: Optional[datetime] = None,
        scopes: Optional[str] = None,
        generated_for_test: Optional[str] = None,
    ) -> OAuthToken:
        """Crea un registro de token"""
        token = OAuthToken(
            token_type=token_type,
            token_hash=token_hash,
            user_id=user_id,
            application_id=application_id,
            expires_at=expires_at,
            scopes=scopes,
            generated_for_test=generated_for_test,
        )
        return self.create(token)

    def revoke_token(self, token_id: int) -> OAuthToken:
        """Revoca un token"""
        token = self.get_by_id(token_id)
        if not token:
            raise EntityNotFoundError(f"Token with id {token_id} not found")

        token.is_revoked = True
        token.updated_at = datetime.utcnow()
        return self.update(token)

    def cleanup_expired_tokens(self) -> int:
        """Limpia tokens expirados y retorna el número eliminado"""
        now = datetime.utcnow()
        expired_tokens = self.session.exec(
            select(self.model).where(
                self.model.expires_at.is_not(None),
                self.model.expires_at < now,
            )
        ).all()

        count = 0
        for token in expired_tokens:
            self.delete(token.id)
            count += 1

        return count
