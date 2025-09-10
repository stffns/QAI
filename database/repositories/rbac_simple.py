"""
Repositorio RBAC Simplificado - Sistema de Permisos
=================================================

Implementación simplificada del repositorio RBAC que funciona con la estructura actual.

Author: QA Intelligence Team  
Date: 2025-09-08
"""

import sqlite3
from datetime import datetime
from typing import List, Optional, Dict, Any, Tuple
from contextlib import contextmanager


class RBACRepositorySimple:
    """Repositorio simplificado para gestión RBAC usando SQLite directo."""
    
    def __init__(self, db_path: str = "data/qa_intelligence.db"):
        self.db_path = db_path
    
    @contextmanager
    def get_connection(self):
        """Context manager para conexiones de base de datos."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row  # Para acceso por nombre de columna
        try:
            yield conn
        finally:
            conn.close()
    
    # =============================================================================
    # GESTIÓN DE ROLES Y PERMISOS (RBAC CORE)
    # =============================================================================
    
    def assign_permission_to_role(self, role_id: int, permission_id: int, 
                                 granted_by: Optional[str] = None) -> bool:
        """Asignar permiso a rol (RBAC completo)."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Verificar si ya existe
            cursor.execute("""
                SELECT id FROM role_permissions 
                WHERE role_id = ? AND permission_id = ? AND is_active = 1
            """, (role_id, permission_id))
            
            if cursor.fetchone():
                return False  # Ya existe
            
            # Crear asignación
            cursor.execute("""
                INSERT INTO role_permissions (role_id, permission_id, granted_by, granted_at, is_active)
                VALUES (?, ?, ?, datetime('now'), 1)
            """, (role_id, permission_id, granted_by))
            
            conn.commit()
            return True
    
    def revoke_permission_from_role(self, role_id: int, permission_id: int) -> bool:
        """Revocar permiso de rol."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                UPDATE role_permissions 
                SET is_active = 0 
                WHERE role_id = ? AND permission_id = ? AND is_active = 1
            """, (role_id, permission_id))
            
            conn.commit()
            return cursor.rowcount > 0
    
    def get_role_permissions(self, role_id: int) -> List[Dict[str, Any]]:
        """Obtener permisos de un rol."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT p.id, p.name, p.description, p.category, 
                       p.resource_type, p.action, p.scope,
                       rp.granted_at, rp.granted_by
                FROM permissions p
                JOIN role_permissions rp ON p.id = rp.permission_id
                WHERE rp.role_id = ? AND rp.is_active = 1 AND p.is_active = 1
                ORDER BY p.category, p.name
            """, (role_id,))
            
            return [dict(row) for row in cursor.fetchall()]
    
    def assign_role_to_user(self, user_id: int, role_id: int, 
                           assigned_by: Optional[str] = None) -> bool:
        """Asignar rol a usuario."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Verificar si ya existe
            cursor.execute("""
                SELECT 1 FROM user_roles 
                WHERE user_id = ? AND role_id = ? AND is_active = 1
            """, (user_id, role_id))
            
            if cursor.fetchone():
                return False  # Ya existe
            
            # Crear asignación
            cursor.execute("""
                INSERT OR REPLACE INTO user_roles 
                (user_id, role_id, assigned_at, assigned_by, is_active)
                VALUES (?, ?, datetime('now'), ?, 1)
            """, (user_id, role_id, assigned_by))
            
            conn.commit()
            return True
    
    def get_user_effective_permissions(self, user_id: int) -> List[Dict[str, Any]]:
        """Obtener todos los permisos efectivos del usuario."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Permisos por roles + permisos directos
            cursor.execute("""
                SELECT DISTINCT 
                    p.id as permission_id,
                    p.name as permission_name,
                    p.category,
                    p.resource_type,
                    p.action,
                    p.scope,
                    'role' as source_type,
                    r.name as source_name
                FROM permissions p
                JOIN role_permissions rp ON p.id = rp.permission_id AND rp.is_active = 1
                JOIN roles r ON rp.role_id = r.id AND r.is_active = 1
                JOIN user_roles ur ON r.id = ur.role_id AND ur.is_active = 1
                WHERE ur.user_id = ?
                  AND p.is_active = 1
                
                UNION
                
                SELECT DISTINCT
                    p.id as permission_id,
                    p.name as permission_name,
                    p.category,
                    p.resource_type,
                    p.action,
                    p.scope,
                    'direct' as source_type,
                    'user_permission' as source_name
                FROM permissions p
                JOIN user_permissions up ON p.id = up.permission_id
                WHERE up.user_id = ?
                  AND up.is_active = 1
                  AND up.revoked_at IS NULL
                  AND p.is_active = 1
                
                ORDER BY category, permission_name
            """, (user_id, user_id))
            
            return [dict(row) for row in cursor.fetchall()]
    
    def user_has_permission(self, user_id: int, permission_name: str, 
                           resource_type: Optional[str] = None,
                           action: Optional[str] = None) -> bool:
        """Verificar si usuario tiene permiso específico."""
        permissions = self.get_user_effective_permissions(user_id)
        
        for perm in permissions:
            if perm['permission_name'] == permission_name:
                # Verificar contexto si se especifica
                if resource_type and perm['resource_type'] != resource_type:
                    continue
                if action and perm['action'] != action:
                    continue
                return True
        
        return False
    
    # =============================================================================
    # GESTIÓN DE DATOS MAESTROS
    # =============================================================================
    
    def get_all_roles(self) -> List[Dict[str, Any]]:
        """Obtener todos los roles."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT id, name, description, parent_role_id, 
                       is_system_role, priority, is_active,
                       created_at, updated_at
                FROM roles 
                WHERE is_active = 1
                ORDER BY priority DESC, name
            """)
            
            return [dict(row) for row in cursor.fetchall()]
    
    def get_all_permissions(self) -> List[Dict[str, Any]]:
        """Obtener todos los permisos."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT id, name, description, category, 
                       resource_type, action, scope,
                       is_system_permission, is_active,
                       created_at
                FROM permissions 
                WHERE is_active = 1
                ORDER BY category, name
            """)
            
            return [dict(row) for row in cursor.fetchall()]
    
    def get_user_roles(self, user_id: int) -> List[Dict[str, Any]]:
        """Obtener roles de un usuario."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT r.id, r.name, r.description, 
                       ur.assigned_at, ur.assigned_by
                FROM roles r
                JOIN user_roles ur ON r.id = ur.role_id
                WHERE ur.user_id = ? AND ur.is_active = 1 AND r.is_active = 1
                ORDER BY r.name
            """, (user_id,))
            
            return [dict(row) for row in cursor.fetchall()]
    
    # =============================================================================
    # MIGRACIÓN Y UTILIDADES
    # =============================================================================
    
    def migrate_existing_permissions_to_roles(self) -> Dict[str, int]:
        """Migrar permisos directos existentes a sistema basado en roles."""
        stats = {"migrated": 0, "skipped": 0, "errors": 0}
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Obtener asignaciones directas existentes
            cursor.execute("""
                SELECT DISTINCT up.user_id, up.permission_id, ur.role_id
                FROM user_permissions up
                JOIN user_roles ur ON up.user_id = ur.user_id
                WHERE up.is_active = 1 AND ur.is_active = 1
            """)
            
            user_permissions = cursor.fetchall()
            
            for user_id, permission_id, role_id in user_permissions:
                try:
                    # Verificar si el rol ya tiene este permiso
                    cursor.execute("""
                        SELECT 1 FROM role_permissions 
                        WHERE role_id = ? AND permission_id = ?
                    """, (role_id, permission_id))
                    
                    if not cursor.fetchone():
                        # Asignar permiso al rol
                        cursor.execute("""
                            INSERT INTO role_permissions 
                            (role_id, permission_id, granted_at, granted_by, is_active)
                            VALUES (?, ?, datetime('now'), 'migration', 1)
                        """, (role_id, permission_id))
                        stats["migrated"] += 1
                    else:
                        stats["skipped"] += 1
                        
                except Exception:
                    stats["errors"] += 1
            
            conn.commit()
        
        return stats
    
    def get_rbac_status(self) -> Dict[str, Any]:
        """Obtener estado del sistema RBAC."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Contar registros
            counts = {}
            tables = ['users', 'roles', 'permissions', 'user_roles', 'role_permissions', 'user_permissions']
            
            for table in tables:
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                counts[table] = cursor.fetchone()[0]
            
            # Estadísticas adicionales
            cursor.execute("SELECT COUNT(*) FROM role_permissions WHERE is_active = 1")
            active_role_permissions = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM user_permissions WHERE is_active = 1")
            active_user_permissions = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(DISTINCT user_id) FROM user_roles WHERE is_active = 1")
            users_with_roles = cursor.fetchone()[0]
            
            return {
                "counts": counts,
                "active_role_permissions": active_role_permissions,
                "active_user_permissions": active_user_permissions,
                "users_with_roles": users_with_roles,
                "rbac_implemented": active_role_permissions > 0
            }


# =============================================================================
# FUNCIONES DE UTILIDAD
# =============================================================================

def create_rbac_repository(db_path: str = "data/qa_intelligence.db") -> RBACRepositorySimple:
    """Factory para crear instancia del repositorio RBAC."""
    return RBACRepositorySimple(db_path)


def initialize_default_rbac_permissions():
    """Inicializar permisos por defecto en el sistema RBAC."""
    repo = create_rbac_repository()
    
    # Definir permisos por rol por defecto
    default_assignments = {
        "SUPER_ADMIN": [
            "database_admin", "manage_users", "create_agents", "system_monitoring"
        ],
        "admin": [
            "manage_users", "manage_master_data", "view_all_reports"
        ],
        "qa_engineer": [
            "manage_configs", "execute_performance_tests", "manage_slas"
        ],
        "viewer": [
            "view_all_reports"
        ]
    }
    
    stats = {"assigned": 0, "skipped": 0, "errors": 0}
    
    # Asignar permisos a roles
    for role_name, permission_names in default_assignments.items():
        # Obtener ID del rol
        with repo.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM roles WHERE name = ?", (role_name,))
            role_result = cursor.fetchone()
            
            if not role_result:
                continue
                
            role_id = role_result[0]
            
            for permission_name in permission_names:
                # Obtener ID del permiso
                cursor.execute("SELECT id FROM permissions WHERE name = ?", (permission_name,))
                perm_result = cursor.fetchone()
                
                if not perm_result:
                    continue
                
                permission_id = perm_result[0]
                
                # Asignar permiso al rol
                try:
                    if repo.assign_permission_to_role(role_id, permission_id, "system_init"):
                        stats["assigned"] += 1
                    else:
                        stats["skipped"] += 1
                except Exception:
                    stats["errors"] += 1
    
    return stats
