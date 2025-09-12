"""
Modelos OAuth para QA Intelligence

Modelos SQLModel para autenticación OAuth integrados con esquema QAI.
Siguen el patrón SOLID y Repository establecido en el proyecto.

Estructura de relaciones:
- oauth_users -> mapping_id (app_environment_country_mappings)
- oauth_jwks -> environment_id (environments_master)
- oauth_app_clients -> mapping_id (app_environment_country_mappings)
"""

from datetime import datetime
from typing import Optional
from sqlmodel import SQLModel, Field, Relationship
import json


class OAuthUserBase(SQLModel):
    """Modelo base para usuarios OAuth - matches real table schema"""
    
    mapping_id: int = Field(
        foreign_key="app_environment_country_mappings.id",
        description="FK a app_environment_country_mappings (app+env+country)"
    )
    email: str = Field(
        max_length=255,
        description="Email del usuario OAuth"
    )
    given_name: str = Field(
        max_length=100,
        description="Nombre del usuario"
    )
    family_name: str = Field(
        max_length=100,
        description="Apellido del usuario"
    )
    phone_number: str = Field(
        max_length=20,
        description="Número de teléfono"
    )
    gender: str = Field(
        max_length=10,
        description="Género del usuario"
    )
    password_hash: str = Field(
        description="Hash de password para autenticación"
    )
    test_purpose: Optional[str] = Field(
        default=None,
        description="Propósito de testing"
    )
    locale: Optional[str] = Field(
        default=None,
        max_length=10,
        description="Locale del usuario (ro-RO, fr-FR, etc.)"
    )
    
    # Control
    is_active: bool = Field(default=True, description="Usuario activo")
    
    # Auditoría
    created_at: Optional[datetime] = Field(default=None)
    updated_at: Optional[datetime] = Field(default=None)


class OAuthUsers(OAuthUserBase, table=True):
    """Tabla usuarios OAuth"""
    
    __tablename__ = "oauth_users"
    
    id: Optional[int] = Field(default=None, primary_key=True)


class OAuthJWKBase(SQLModel):
    """Modelo base para claves JWK OAuth"""
    
    environment_id: int = Field(
        foreign_key="environments_master.id",
        description="FK a environments_master"
    )
    key_id: str = Field(
        max_length=100,
        unique=True,
        description="Identificador único de la clave JWK"
    )
    jwk_content: str = Field(
        description="Contenido JWK en formato JSON"
    )
    algorithm: str = Field(
        default="ES256",
        max_length=10,
        description="Algoritmo de firma JWT"
    )
    
    # Control
    is_active: bool = Field(default=True, description="JWK activa")
    
    # Auditoría - oauth_jwks only has created_at, no updated_at
    created_at: Optional[datetime] = Field(default=None)


class OAuthJWKs(OAuthJWKBase, table=True):
    """Tabla claves JWK OAuth"""
    
    __tablename__ = "oauth_jwks"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    
    @property
    def jwk_data(self) -> dict:
        """Parsear contenido JWK como diccionario"""
        try:
            return json.loads(self.jwk_content)
        except json.JSONDecodeError:
            return {}


class OAuthAppClientBase(SQLModel):
    """Modelo base para clientes OAuth de aplicaciones"""
    
    mapping_id: int = Field(
        foreign_key="app_environment_country_mappings.id",
        unique=True,
        description="FK a app_environment_country_mappings (un client por mapping)"
    )
    
    # Configuración OAuth
    client_id: str = Field(
        max_length=255,
        unique=True,
        description="Client ID OAuth"
    )
    client_name: str = Field(
        max_length=100,
        description="Nombre descriptivo del cliente"
    )
    
    # URLs de configuración
    callback_url: str = Field(
        max_length=500,
        description="URL de callback OAuth"
    )
    resource_url: Optional[str] = Field(
        default=None,
        max_length=500,
        description="URL del recurso (si es requerida)"
    )
    
    # Flags de configuración
    needs_resource_param: bool = Field(
        default=False,
        description="Si requiere parámetro resource en la URL"
    )
    is_pkce_required: bool = Field(
        default=True,
        description="Si requiere PKCE (recomendado)"
    )
    
    # Scopes OAuth
    default_scopes: str = Field(
        default="openid profile email",
        max_length=200,
        description="Scopes por defecto separados por espacios"
    )
    
    # Control
    is_active: bool = Field(default=True, description="Cliente activo")
    
    # Auditoría
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = Field(default=None)


class OAuthAppClients(OAuthAppClientBase, table=True):
    """Tabla clientes OAuth de aplicaciones"""
    
    __tablename__ = "oauth_app_clients"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    
    @property
    def scopes_list(self) -> list[str]:
        """Convertir scopes a lista"""
        return self.default_scopes.split() if self.default_scopes else []


# Modelos para crear/actualizar (sin auditoría automática)
class OAuthUserCreate(OAuthUserBase):
    """Modelo para crear usuario OAuth"""
    pass


class OAuthUserUpdate(SQLModel):
    """Modelo para actualizar usuario OAuth"""
    email: Optional[str] = None
    password_hash: Optional[str] = None
    realm: Optional[str] = None
    is_active: Optional[bool] = None
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class OAuthJWKCreate(OAuthJWKBase):
    """Modelo para crear JWK OAuth"""
    pass


class OAuthJWKUpdate(SQLModel):
    """Modelo para actualizar JWK OAuth"""
    jwk_content: Optional[str] = None
    algorithm: Optional[str] = None
    is_active: Optional[bool] = None
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class OAuthAppClientCreate(OAuthAppClientBase):
    """Modelo para crear cliente OAuth"""
    pass


class OAuthAppClientUpdate(SQLModel):
    """Modelo para actualizar cliente OAuth"""
    client_name: Optional[str] = None
    callback_url: Optional[str] = None
    resource_url: Optional[str] = None
    needs_resource_param: Optional[bool] = None
    is_pkce_required: Optional[bool] = None
    default_scopes: Optional[str] = None
    is_active: Optional[bool] = None
    updated_at: datetime = Field(default_factory=datetime.utcnow)


# Export de todos los modelos
__all__ = [
    # Modelos principales
    "OAuthUsers",
    "OAuthJWKs", 
    "OAuthAppClients",
    
    # Modelos base
    "OAuthUserBase",
    "OAuthJWKBase",
    "OAuthAppClientBase",
    
    # Modelos de operación
    "OAuthUserCreate",
    "OAuthUserUpdate",
    "OAuthJWKCreate", 
    "OAuthJWKUpdate",
    "OAuthAppClientCreate",
    "OAuthAppClientUpdate",
]
