"""
Modelos SQLModel Mejorados - Sistema de Permisos RBAC
===================================================

Implementación completa de RBAC con auditoría, jerarquías y permisos contextuales.
Basado en el análisis de recomendaciones del sistema actual.

Author: QA Intelligence Team
Date: 2025-09-08
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from enum import Enum

from sqlmodel import SQLModel, Field, Relationship, Column, String, Integer, Boolean, DateTime
from sqlalchemy import ForeignKey, UniqueConstraint
from pydantic import validator


# =============================================================================
# ENUMS
# =============================================================================

class UserStatus(str, Enum):
    """Estado del usuario en el sistema."""
    ACTIVE = "active"
    INACTIVE = "inactive"
    LOCKED = "locked"
    SUSPENDED = "suspended"


class PermissionCategory(str, Enum):
    """Categorías de permisos del sistema."""
    ADMIN = "ADMIN"
    DATA = "DATA"
    REPORTING = "REPORTING"
    TESTING = "TESTING"
    API = "API"
    SECURITY = "SECURITY"


class ResourceType(str, Enum):
    """Tipos de recursos para permisos contextuales."""
    SYSTEM = "system"
    APPLICATION = "application"
    COUNTRY = "country"
    ENVIRONMENT = "environment"
    TEST_SUITE = "test_suite"
    REPORT = "report"
    USER = "user"
    CONFIG = "config"


class PermissionAction(str, Enum):
    """Acciones disponibles para permisos granulares."""
    CREATE = "create"
    READ = "read"
    UPDATE = "update"
    DELETE = "delete"
    EXECUTE = "execute"
    APPROVE = "approve"
    ADMIN = "admin"
    VIEW_ALL = "view_all"


# =============================================================================
# MODELOS BASE
# =============================================================================

class TimestampMixin(SQLModel):
    """Mixin para campos de timestamp."""
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = Field(default=None)


class AuditMixin(SQLModel):
    """Mixin para campos de auditoría."""
    created_by: Optional[str] = Field(default=None, max_length=100)
    updated_by: Optional[str] = Field(default=None, max_length=100)


# =============================================================================
# MODELOS PRINCIPALES
# =============================================================================

class Role(TimestampMixin, AuditMixin, table=True):
    """
    Modelo de roles con soporte para jerarquías.
    
    Características:
    - Jerarquía de roles (parent_role_id)
    - Roles de sistema vs customizables
    - Prioridad para resolución de conflictos
    """
    
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(max_length=50, unique=True, index=True)
    description: Optional[str] = Field(default=None, max_length=255)
    
    # Jerarquía
    parent_role_id: Optional[int] = Field(default=None, foreign_key="role.id")
    priority: int = Field(default=0, description="Prioridad para resolución de conflictos")
    
    # Sistema
    is_system_role: bool = Field(default=False, description="Rol del sistema, no editable")
    is_active: bool = Field(default=True)
    
    # Relaciones
    parent_role: Optional["Role"] = Relationship(
        back_populates="child_roles",
        sa_relationship_kwargs={"remote_side": "Role.id"}
    )
    child_roles: List["Role"] = Relationship(back_populates="parent_role")
    
    # Usuarios y permisos
    user_roles: List["UserRole"] = Relationship(back_populates="role")
    role_permissions: List["RolePermission"] = Relationship(back_populates="role")
    
    @validator('name')
    def validate_name(cls, v):
        if not v or len(v.strip()) == 0:
            raise ValueError("El nombre del rol no puede estar vacío")
        return v.strip().upper()
    
    def get_effective_permissions(self, include_inherited: bool = True) -> List["Permission"]:
        """Obtener permisos efectivos incluyendo herencia."""
        permissions = []
        
        # Permisos directos
        for rp in self.role_permissions:
            if rp.is_active:
                permissions.append(rp.permission)
        
        # Permisos heredados
        if include_inherited and self.parent_role:
            permissions.extend(self.parent_role.get_effective_permissions())
        
        # Eliminar duplicados
        return list(set(permissions))


class Permission(TimestampMixin, AuditMixin, table=True):
    """
    Modelo de permisos con contexto y granularidad.
    
    Características:
    - Permisos contextuales por recurso
    - Acciones granulares
    - Scopes para filtrado adicional
    """
    
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(max_length=100, unique=True, index=True)
    description: Optional[str] = Field(default=None, max_length=255)
    category: PermissionCategory = Field(index=True)
    
    # Contexto y granularidad
    resource_type: Optional[ResourceType] = Field(default=None, index=True)
    action: Optional[PermissionAction] = Field(default=None, index=True)
    scope: Optional[str] = Field(default=None, max_length=100, description="Scope adicional como app_id, country_code")
    
    # Sistema
    is_system_permission: bool = Field(default=False, description="Permiso del sistema, no editable")
    is_active: bool = Field(default=True)
    
    # Relaciones
    role_permissions: List["RolePermission"] = Relationship(back_populates="permission")
    user_permissions: List["UserPermission"] = Relationship(back_populates="permission")
    
    @validator('name')
    def validate_name(cls, v):
        if not v or len(v.strip()) == 0:
            raise ValueError("El nombre del permiso no puede estar vacío")
        return v.strip().lower()
    
    def get_permission_key(self) -> str:
        """Generar clave única para el permiso."""
        parts = [self.name]
        if self.resource_type:
            parts.append(self.resource_type.value)
        if self.action:
            parts.append(self.action.value)
        if self.scope:
            parts.append(self.scope)
        return ":".join(parts)


class User(TimestampMixin, AuditMixin, table=True):
    """
    Modelo de usuario mejorado sin campo role duplicado.
    
    Características:
    - Solo relación many-to-many con roles
    - Campos de seguridad y auditoría
    - Estados del usuario
    """
    
    id: Optional[int] = Field(default=None, primary_key=True)
    username: str = Field(max_length=50, unique=True, index=True)
    email: str = Field(max_length=100, unique=True, index=True)
    full_name: Optional[str] = Field(default=None, max_length=100)
    
    # Seguridad
    password_hash: str = Field(max_length=255)
    status: UserStatus = Field(default=UserStatus.ACTIVE, index=True)
    
    # Control de acceso
    failed_login_attempts: int = Field(default=0)
    last_login_at: Optional[datetime] = Field(default=None)
    locked_until: Optional[datetime] = Field(default=None)
    password_changed_at: Optional[datetime] = Field(default=None)
    
    # Configuración
    timezone: Optional[str] = Field(default="UTC", max_length=50)
    language: Optional[str] = Field(default="es", max_length=10)
    
    # Relaciones
    user_roles: List["UserRole"] = Relationship(back_populates="user")
    user_permissions: List["UserPermission"] = Relationship(back_populates="user")
    audit_logs: List["AuditLog"] = Relationship(back_populates="user")
    
    @validator('email')
    def validate_email(cls, v):
        if '@' not in v:
            raise ValueError("Email inválido")
        return v.lower()
    
    def get_effective_permissions(self) -> List[Permission]:
        """Obtener todos los permisos efectivos del usuario."""
        permissions = []
        
        # Permisos directos activos
        for up in self.user_permissions:
            if up.is_active and not up.is_revoked():
                permissions.append(up.permission)
        
        # Permisos por roles
        for ur in self.user_roles:
            if ur.is_active:
                permissions.extend(ur.role.get_effective_permissions())
        
        # Eliminar duplicados
        return list(set(permissions))
    
    def has_permission(self, permission_name: str, resource_type: Optional[str] = None, 
                       action: Optional[str] = None, scope: Optional[str] = None) -> bool:
        """Verificar si el usuario tiene un permiso específico."""
        effective_permissions = self.get_effective_permissions()
        
        for perm in effective_permissions:
            if perm.name == permission_name:
                # Verificar contexto si se especifica
                if resource_type and perm.resource_type and perm.resource_type.value != resource_type:
                    continue
                if action and perm.action and perm.action.value != action:
                    continue
                if scope and perm.scope and perm.scope != scope:
                    continue
                return True
        
        return False


# =============================================================================
# MODELOS DE RELACIÓN
# =============================================================================

class UserRole(TimestampMixin, table=True):
    """Relación many-to-many entre usuarios y roles."""
    
    user_id: int = Field(foreign_key="users.id", primary_key=True)
    role_id: int = Field(foreign_key="roles.id", primary_key=True)
    
    # Auditoría
    assigned_at: datetime = Field(default_factory=datetime.utcnow)
    assigned_by: Optional[str] = Field(default=None, max_length=100)
    expires_at: Optional[datetime] = Field(default=None)
    is_active: bool = Field(default=True)
    
    # Relaciones
    user: User = Relationship(back_populates="user_roles")
    role: Role = Relationship(back_populates="user_roles")
    
    def is_expired(self) -> bool:
        """Verificar si la asignación de rol ha expirado."""
        return self.expires_at is not None and self.expires_at < datetime.utcnow()


class RolePermission(TimestampMixin, table=True):
    """
    Relación many-to-many entre roles y permisos.
    Esta es la tabla clave para RBAC completo.
    """
    
    id: Optional[int] = Field(default=None, primary_key=True)
    role_id: int = Field(foreign_key="roles.id", index=True)
    permission_id: int = Field(foreign_key="permissions.id", index=True)
    
    # Auditoría
    granted_at: datetime = Field(default_factory=datetime.utcnow)
    granted_by: Optional[str] = Field(default=None, max_length=100)
    is_active: bool = Field(default=True)
    
    # Relaciones
    role: Role = Relationship(back_populates="role_permissions")
    permission: Permission = Relationship(back_populates="role_permissions")


class UserPermission(TimestampMixin, table=True):
    """
    Permisos directos de usuario (excepciones al RBAC).
    Solo para casos especiales donde se requiere permiso específico.
    """
    
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", index=True)
    permission_id: int = Field(foreign_key="permissions.id", index=True)
    
    # Auditoría completa
    granted_at: datetime = Field(default_factory=datetime.utcnow)
    granted_by: Optional[str] = Field(default=None, max_length=100)
    revoked_at: Optional[datetime] = Field(default=None)
    revoked_by: Optional[str] = Field(default=None, max_length=100)
    expires_at: Optional[datetime] = Field(default=None)
    is_active: bool = Field(default=True)
    
    # Contexto adicional
    reason: Optional[str] = Field(default=None, max_length=255, description="Razón para permiso directo")
    
    # Relaciones
    user: User = Relationship(back_populates="user_permissions")
    permission: Permission = Relationship(back_populates="user_permissions")
    
    def is_revoked(self) -> bool:
        """Verificar si el permiso ha sido revocado."""
        return self.revoked_at is not None
    
    def is_expired(self) -> bool:
        """Verificar si el permiso ha expirado."""
        return self.expires_at is not None and self.expires_at < datetime.utcnow()
    
    def revoke(self, revoked_by: str, reason: Optional[str] = None):
        """Revocar el permiso."""
        self.revoked_at = datetime.utcnow()
        self.revoked_by = revoked_by
        self.is_active = False
        if reason:
            self.reason = f"{self.reason or ''} | REVOKED: {reason}"


class AuditLog(TimestampMixin, table=True):
    """
    Log de auditoría para cambios en permisos y roles.
    """
    
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: Optional[int] = Field(default=None, foreign_key="users.id")
    
    # Acción
    action: str = Field(max_length=50, index=True)  # CREATE, UPDATE, DELETE, GRANT, REVOKE
    entity_type: str = Field(max_length=50, index=True)  # USER, ROLE, PERMISSION, USER_ROLE, etc.
    entity_id: Optional[int] = Field(default=None)
    
    # Detalles
    old_values: Optional[str] = Field(default=None, description="JSON con valores anteriores")
    new_values: Optional[str] = Field(default=None, description="JSON con valores nuevos")
    description: Optional[str] = Field(default=None, max_length=500)
    
    # Contexto
    ip_address: Optional[str] = Field(default=None, max_length=45)
    user_agent: Optional[str] = Field(default=None, max_length=500)
    session_id: Optional[str] = Field(default=None, max_length=100)
    
    # Relación
    user: Optional[User] = Relationship(back_populates="audit_logs")


# =============================================================================
# VISTAS Y FUNCIONES AUXILIARES
# =============================================================================

class UserEffectivePermissionView(SQLModel):
    """Vista de permisos efectivos por usuario."""
    user_id: int
    username: str
    permission_id: int
    permission_name: str
    category: str
    resource_type: Optional[str]
    action: Optional[str]
    scope: Optional[str]
    source_type: str  # 'role' o 'direct'
    source_name: str


def create_permission_key(name: str, resource_type: Optional[str] = None, 
                         action: Optional[str] = None, scope: Optional[str] = None) -> str:
    """Crear clave única para permiso."""
    parts = [name]
    if resource_type:
        parts.append(resource_type)
    if action:
        parts.append(action)
    if scope:
        parts.append(scope)
    return ":".join(parts)


def validate_permission_context(resource_type: Optional[str], action: Optional[str], 
                               scope: Optional[str]) -> bool:
    """Validar contexto de permiso."""
    # Si se especifica resource_type, debe haber action
    if resource_type and not action:
        return False
    
    # Validaciones específicas por tipo de recurso
    if resource_type == ResourceType.APPLICATION.value and not scope:
        return False  # Aplicaciones requieren app_id en scope
    
    if resource_type == ResourceType.COUNTRY.value and not scope:
        return False  # Países requieren country_code en scope
    
    return True
