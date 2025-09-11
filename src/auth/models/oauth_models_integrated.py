"""
OAuth/OIDC Models integrados con el esquema existente del proyecto QAI
Se vincula con: app_environment_country_mappings, apps_master, environments_master, countries_master
"""

from __future__ import annotations

from typing import Optional
from datetime import datetime
from enum import Enum

from sqlmodel import SQLModel, Field
from pydantic import field_validator, EmailStr

try:
    from database.base import BaseModel
except ImportError:
    import sys
    import os
    sys.path.append(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
    from database.base import BaseModel


class Gender(str, Enum):
    """Géneros soportados (del código Scala original)"""
    MALE = "male"
    FEMALE = "female" 
    HOMME = "Homme"  # French
    FEMEIE = "Femeie"  # Romanian


class OAuthUser(SQLModel, table=True):
    """
    Usuarios OAuth para testing - VINCULADOS al esquema existente
    Se relaciona con app_environment_country_mappings para validar que el usuario
    sea válido para la combinación app+environment+country específica
    """
    __tablename__ = "oauth_users"

    id: Optional[int] = Field(default=None, primary_key=True)
    
    # Información del usuario (del código Scala UserMap)
    email: EmailStr = Field(description="Email del usuario", unique=True)
    given_name: str = Field(max_length=100, description="Nombre")
    family_name: str = Field(max_length=100, description="Apellido") 
    phone_number: str = Field(max_length=20, description="Teléfono")
    gender: Gender = Field(description="Género")
    password_hash: str = Field(description="Password hasheado", repr=False)
    
    # RELACIÓN CON ESQUEMA EXISTENTE - Validación por constraints FK
    mapping_id: int = Field(
        foreign_key="app_environment_country_mappings.id", 
        description="FK a app_environment_country_mappings - define para qué app+env+country es válido este usuario"
    )
    
    # Control y metadata  
    is_active: bool = Field(default=True, description="Si el usuario está activo")
    test_purpose: Optional[str] = Field(default=None, max_length=200, description="Propósito del testing")
    locale: str = Field(max_length=10, default="en-US", description="Locale del usuario")
    
    # Auditoría
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = Field(default=None)
    created_by: Optional[str] = Field(default=None, max_length=100)

    def get_full_name(self) -> str:
        """Retorna el nombre completo"""
        return f"{self.given_name} {self.family_name}"

    @field_validator('email')
    def validate_email_format(cls, v: str) -> str:
        """Validar formato del email"""
        if not v or '@' not in v:
            raise ValueError('Email must be valid')
        return v.lower()

    @field_validator('phone_number')
    def validate_phone_format(cls, v: str) -> str:
        """Validar formato del teléfono"""
        if not v.startswith('+'):
            raise ValueError('Phone number must start with +')
        return v


class OAuthJWK(SQLModel, table=True):
    """
    Claves JWK por ambiente - VINCULADAS a environments_master
    Una clave JWK por ambiente (STA, UAT, PROD)
    """
    __tablename__ = "oauth_jwks"

    id: Optional[int] = Field(default=None, primary_key=True)
    
    # RELACIÓN CON ESQUEMA EXISTENTE
    environment_id: int = Field(
        foreign_key="environments_master.id", 
        description="FK a environments_master"
    )
    
    # Datos de la clave (del código Scala JWKMap)
    key_id: str = Field(max_length=100, description="Key ID único", unique=True)
    jwk_content: str = Field(description="Contenido JWK JSON completo", repr=False)
    algorithm: str = Field(max_length=10, default="ES256", description="Algoritmo (ES256, RS256, etc.)")
    
    # Control
    is_active: bool = Field(default=True, description="Si la clave está activa")
    expires_at: Optional[datetime] = Field(default=None, description="Cuándo expira la clave")
    
    # Auditoría
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = Field(default=None)

    @field_validator('jwk_content')
    def validate_jwk_json(cls, v: str) -> str:
        """Validar que el JWK sea JSON válido"""
        import json
        try:
            jwk_data = json.loads(v)
            # Validaciones básicas JWK
            required_fields = ['kty', 'kid']
            for field in required_fields:
                if field not in jwk_data:
                    raise ValueError(f'JWK must contain {field}')
            return v
        except json.JSONDecodeError:
            raise ValueError('JWK content must be valid JSON')

    @field_validator('algorithm')
    def validate_algorithm(cls, v: str) -> str:
        """Validar algoritmo soportado"""
        valid_algorithms = ['ES256', 'ES384', 'ES512', 'RS256', 'RS384', 'RS512']
        if v not in valid_algorithms:
            raise ValueError(f'Algorithm must be one of: {valid_algorithms}')
        return v


class OAuthAppClient(SQLModel, table=True):
    """
    Client IDs OAuth por aplicación - VINCULADOS a apps_master
    Cada app puede tener múltiples client_ids según el ambiente/país
    """
    __tablename__ = "oauth_app_clients"

    id: Optional[int] = Field(default=None, primary_key=True)
    
    # RELACIÓN CON ESQUEMA EXISTENTE  
    application_id: int = Field(
        foreign_key="apps_master.id",
        description="FK a apps_master"
    )
    environment_id: int = Field(
        foreign_key="environments_master.id", 
        description="FK a environments_master"
    )
    
    # Configuración OAuth (del código Scala ClientIdMap)
    client_id: str = Field(max_length=255, description="Client ID OAuth", unique=True)
    client_name: str = Field(max_length=100, description="Nombre descriptivo del cliente")
    
    # URLs de configuración
    callback_url: str = Field(description="URL de callback/redirect")
    resource_url: Optional[str] = Field(default=None, description="URL del recurso (si aplica)")
    
    # Flags de configuración
    needs_resource_param: bool = Field(default=False, description="Si necesita parámetro resource")
    is_pkce_required: bool = Field(default=True, description="Si requiere PKCE")
    
    # Scopes OAuth
    default_scopes: str = Field(default="openid profile email", description="Scopes por defecto")
    
    # Control
    is_active: bool = Field(default=True, description="Si el cliente está activo")
    
    # Auditoría
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = Field(default=None)

    @field_validator('client_id')
    def validate_client_id_format(cls, v: str) -> str:
        """Validar formato del client ID"""
        if len(v) < 10:
            raise ValueError('Client ID must be at least 10 characters')
        return v

    @field_validator('callback_url')
    def validate_callback_url(cls, v: str) -> str:
        """Validar formato de URL de callback"""
        if not v.startswith(('http://', 'https://')):
            raise ValueError('Callback URL must start with http:// or https://')
        return v

    @field_validator('default_scopes')
    def validate_scopes(cls, v: str) -> str:
        """Validar scopes OAuth"""
        valid_scopes = ['openid', 'profile', 'email', 'phone', 'address', 'offline_access']
        scopes = [s.strip() for s in v.split()]
        for scope in scopes:
            if scope not in valid_scopes:
                raise ValueError(f'Invalid scope: {scope}. Valid scopes: {valid_scopes}')
        return v


# ===== CONSTRAINTS Y ÍNDICES SQL ADICIONALES =====

# Se definirán en el script de migración:
# 
# 1. UNIQUE constraint en oauth_users(email, mapping_id) 
#    - Un usuario no puede repetirse para la misma combinación app+env+country
#
# 2. UNIQUE constraint en oauth_jwks(environment_id)
#    - Solo una clave JWK activa por ambiente
#
# 3. UNIQUE constraint en oauth_app_clients(application_id, environment_id) 
#    - Solo un client_id por app+ambiente
#
# 4. CHECK constraints adicionales para validación a nivel DB
#    - oauth_users.locale debe seguir formato xx-XX
#    - oauth_jwks.expires_at debe ser futuro
#    - oauth_app_clients.callback_url debe ser URL válida
#
# 5. Índices de performance:
#    - oauth_users(mapping_id, is_active) 
#    - oauth_jwks(environment_id, is_active)
#    - oauth_app_clients(application_id, environment_id, is_active)
