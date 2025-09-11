"""
OAuth/OIDC Models for QA Intelligence
Modelos para gestión de autenticación OIDC y tokens para testing
"""

from __future__ import annotations

from typing import Optional, Dict, Any
from datetime import datetime, timedelta
from enum import Enum
import json

from sqlmodel import SQLModel, Field, Relationship
from pydantic import field_validator, EmailStr

try:
    from database.base import BaseModel
except ImportError:
    import sys
    import os
    sys.path.append(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
    from database.base import BaseModel


class OAuthEnvironment(str, Enum):
    """Ambientes soportados"""
    STA = "sta"
    UAT = "uat" 
    PROD = "prod"


class OAuthProduct(str, Enum):
    """Productos soportados"""
    ONE_APP = "one-app"
    ONE_APP1 = "one-app1"
    ONE_APP2 = "one-app2"  
    ONE_APP3 = "one-app3"
    ONE_APP4 = "one-app4"
    M_APP = "m-app"
    EVA = "eva"


class Gender(str, Enum):
    """Géneros soportados"""
    MALE = "male"
    FEMALE = "female"
    HOMME = "Homme"  # French
    FEMEIE = "Femeie"  # Romanian


class OAuthCountry(SQLModel, table=True):
    """
    Configuración de países para OAuth
    """
    __tablename__ = "oauth_countries"

    id: Optional[int] = Field(default=None, primary_key=True)
    code: str = Field(max_length=2, unique=True, description="Código de país ISO (mx, cl, co, etc.)")
    name: str = Field(max_length=100, description="Nombre del país")
    locale: str = Field(max_length=10, description="Locale del país (es-MX, pt-BR, etc.)")
    is_active: bool = Field(default=True, description="Si el país está activo")
    
    # Auditoría
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = Field(default=None)
    
    # Relaciones
    oauth_users: list["OAuthUser"] = Relationship(back_populates="country")
    oauth_applications: list["OAuthApplication"] = Relationship(back_populates="country")

    @field_validator('code')
    def validate_country_code(cls, v: str) -> str:
        """Validar código de país"""
        if len(v) != 2:
            raise ValueError('Country code must be 2 characters')
        return v.lower()


class OAuthUser(SQLModel, table=True):
    """
    Usuarios para testing OAuth/OIDC
    Passwords hasheados de forma segura
    """
    __tablename__ = "oauth_users"

    id: Optional[int] = Field(default=None, primary_key=True)
    email: EmailStr = Field(description="Email del usuario")
    given_name: str = Field(max_length=100, description="Nombre")
    family_name: str = Field(max_length=100, description="Apellido") 
    phone_number: str = Field(max_length=20, description="Teléfono")
    gender: Gender = Field(description="Género")
    password_hash: str = Field(description="Password hasheado", repr=False)
    
    # Configuración
    environment: OAuthEnvironment = Field(description="Ambiente (sta, uat, prod)")
    product: OAuthProduct = Field(description="Producto (one-app, m-app, eva)")
    country_code: str = Field(foreign_key="oauth_countries.code", description="Código del país")
    
    # Control
    is_active: bool = Field(default=True, description="Si el usuario está activo")
    test_purpose: Optional[str] = Field(default=None, description="Propósito del usuario de testing")
    
    # Relaciones
    country: OAuthCountry = Relationship(back_populates="oauth_users")
    tokens: list["OAuthToken"] = Relationship(back_populates="user")

    def get_full_name(self) -> str:
        """Retorna el nombre completo"""
        return f"{self.given_name} {self.family_name}"


class OAuthApplication(SQLModel, table=True):
    """
    Configuración de aplicaciones OAuth/OIDC
    """
    __tablename__ = "oauth_applications"

    id: Optional[int] = Field(default=None, primary_key=True)
    client_id: str = Field(unique=True, description="Client ID de OAuth")
    name: str = Field(max_length=100, description="Nombre de la aplicación")
    
    # Configuración
    environment: OAuthEnvironment = Field(description="Ambiente")
    product: OAuthProduct = Field(description="Producto") 
    country_code: str = Field(foreign_key="oauth_countries.code", description="Código del país")
    
    # URLs y configuración OIDC
    callback_url: str = Field(description="URL de callback")
    resource_url: Optional[str] = Field(default=None, description="URL del recurso (si aplica)")
    needs_resource_param: bool = Field(default=False, description="Si necesita parámetro resource")
    
    # Control
    is_active: bool = Field(default=True, description="Si la aplicación está activa")
    
    # Relaciones  
    country: OAuthCountry = Relationship(back_populates="oauth_applications")
    tokens: list["OAuthToken"] = Relationship(back_populates="application")


class OAuthJWK(SQLModel, table=True):
    """
    Gestión de claves JWK por ambiente
    """
    __tablename__ = "oauth_jwks"

    id: Optional[int] = Field(default=None, primary_key=True)
    environment: OAuthEnvironment = Field(unique=True, description="Ambiente")
    key_id: str = Field(description="Key ID")
    jwk_content: str = Field(description="Contenido JWK JSON", repr=False)
    
    # Control
    is_active: bool = Field(default=True)
    expires_at: Optional[datetime] = Field(default=None, description="Fecha de expiración de la clave")

    def get_jwk_dict(self) -> Dict[str, Any]:
        """Retorna el JWK como diccionario"""
        return json.loads(self.jwk_content)


class OAuthEnvironmentConfig(SQLModel, table=True):
    """
    Configuración por ambiente
    """
    __tablename__ = "oauth_environment_configs"

    id: Optional[int] = Field(default=None, primary_key=True)
    environment: OAuthEnvironment = Field(unique=True, description="Ambiente")
    
    # Configuración OIDC
    oidc_domain: str = Field(description="Dominio OIDC (connect.sta.pluxee.app)")
    issuer: str = Field(description="URL del issuer")
    
    # Control
    is_active: bool = Field(default=True)


class TokenType(str, Enum):
    """Tipos de token"""
    ACCESS_TOKEN = "access_token"
    REFRESH_TOKEN = "refresh_token"
    ID_TOKEN = "id_token"
    IMPERSONATION_TOKEN = "impersonation_token"


class OAuthToken(SQLModel, table=True):
    """
    Historial y cache de tokens generados
    Para auditoría y troubleshooting
    """
    __tablename__ = "oauth_tokens"

    id: Optional[int] = Field(default=None, primary_key=True)
    token_type: TokenType = Field(description="Tipo de token")
    token_hash: str = Field(description="Hash del token (no el token real)", repr=False)
    
    # Referencias
    user_id: Optional[int] = Field(default=None, foreign_key="oauth_users.id")
    application_id: Optional[int] = Field(default=None, foreign_key="oauth_applications.id")
    
    # Metadata
    expires_at: Optional[datetime] = Field(default=None, description="Expiración del token")
    scopes: Optional[str] = Field(default=None, description="Scopes del token")
    
    # Auditoría
    generated_for_test: Optional[str] = Field(default=None, description="Nombre del test que generó el token")
    is_revoked: bool = Field(default=False, description="Si el token fue revocado")
    
    # Relaciones
    user: Optional[OAuthUser] = Relationship(back_populates="tokens")
    application: Optional[OAuthApplication] = Relationship(back_populates="tokens")

    def is_expired(self) -> bool:
        """Verifica si el token está expirado"""
        if not self.expires_at:
            return False
        return datetime.utcnow() > self.expires_at


# Índices compuestos para optimizar búsquedas
class OAuthUserIndex(SQLModel):
    """Índices para optimizar búsquedas de usuarios"""
    __table_args__ = (
        # Búsqueda por ambiente/país/producto
        {"extend_existing": True}
    )


class OAuthApplicationIndex(SQLModel): 
    """Índices para optimizar búsquedas de aplicaciones"""
    __table_args__ = (
        # Búsqueda por ambiente/país/producto
        {"extend_existing": True}
    )
