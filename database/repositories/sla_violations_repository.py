"""
SLA Violations Repository - Manejo de violaciones de SLA
"""

import sqlite3
from typing import List, Dict, Any, Optional
from datetime import datetime
import json

class SlaViolationsRepository:
    """Repositorio para operaciones de violaciones SLA"""
    
    def __init__(self, db_path: str = "data/qa_intelligence.db"):
        """
        Inicializar repositorio SLA Violations
        
        Args:
            db_path: Ruta a la base de datos principal
        """
        self.db_path = db_path
    
    def get_connection(self) -> sqlite3.Connection:
        """Obtener conexión a la base de datos"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row  # Para acceso por nombre de columna
        conn.execute("PRAGMA foreign_keys = ON")  # Habilitar foreign keys
        return conn
    
    def create_violation(self, sla_id: int, command_text: str, violation_type: str,
                        requested_value: str = None, sla_limit: str = None,
                        risk_score: int = None) -> int:
        """
        Crear nueva violación SLA
        
        Args:
            sla_id: ID del SLA violado
            command_text: Comando que causó la violación
            violation_type: Tipo de violación (concurrency, duration, rps, etc.)
            requested_value: Valor solicitado que excede límite
            sla_limit: Límite SLA que se viola
            risk_score: Puntuación de riesgo (1-100)
            
        Returns:
            ID de la violación creada
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO sla_violations 
                (sla_id, command_text, violation_type, requested_value, 
                 sla_limit, risk_score, execution_status, detected_at)
                VALUES (?, ?, ?, ?, ?, ?, 'pending', ?)
            """, (
                sla_id, command_text, violation_type, requested_value,
                sla_limit, risk_score, datetime.now()
            ))
            
            return cursor.lastrowid
    
    def approve_violation(self, violation_id: int, approved_by: str, 
                         approval_reason: str) -> bool:
        """
        Aprobar violación SLA
        
        Args:
            violation_id: ID de la violación
            approved_by: Usuario que aprueba
            approval_reason: Justificación de la aprobación
            
        Returns:
            True si se aprobó correctamente
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                UPDATE sla_violations 
                SET execution_status = 'approved',
                    approved_by = ?,
                    approval_reason = ?
                WHERE id = ? AND execution_status = 'pending'
            """, (approved_by, approval_reason, violation_id))
            
            return cursor.rowcount > 0
    
    def deny_violation(self, violation_id: int, approved_by: str, 
                      denial_reason: str) -> bool:
        """
        Denegar violación SLA
        
        Args:
            violation_id: ID de la violación
            approved_by: Usuario que deniega
            denial_reason: Razón de la denegación
            
        Returns:
            True si se denegó correctamente
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                UPDATE sla_violations 
                SET execution_status = 'denied',
                    approved_by = ?,
                    approval_reason = ?,
                    resolved_at = ?
                WHERE id = ? AND execution_status = 'pending'
            """, (approved_by, denial_reason, datetime.now(), violation_id))
            
            return cursor.rowcount > 0
    
    def execute_violation(self, violation_id: int) -> bool:
        """
        Marcar violación como ejecutada
        
        Args:
            violation_id: ID de la violación
            
        Returns:
            True si se marcó como ejecutada
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                UPDATE sla_violations 
                SET execution_status = 'executed'
                WHERE id = ? AND execution_status = 'approved'
            """, (violation_id,))
            
            return cursor.rowcount > 0
    
    def resolve_violation(self, violation_id: int) -> bool:
        """
        Resolver/cerrar violación
        
        Args:
            violation_id: ID de la violación
            
        Returns:
            True si se resolvió correctamente
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                UPDATE sla_violations 
                SET execution_status = 'resolved',
                    resolved_at = ?
                WHERE id = ? AND execution_status IN ('executed', 'denied')
            """, (datetime.now(), violation_id))
            
            return cursor.rowcount > 0
    
    def get_violation_by_id(self, violation_id: int) -> Optional[Dict]:
        """
        Obtener violación por ID
        
        Args:
            violation_id: ID de la violación
            
        Returns:
            Datos de la violación o None
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT v.*, s.app_name, s.environment, s.endpoint_pattern
                FROM sla_violations v
                LEFT JOIN performance_slas s ON v.sla_id = s.id
                WHERE v.id = ?
            """, (violation_id,))
            
            row = cursor.fetchone()
            return dict(row) if row else None
    
    def get_pending_violations(self) -> List[Dict]:
        """
        Obtener violaciones pendientes de aprobación
        
        Returns:
            Lista de violaciones pendientes
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT v.*, s.app_name, s.environment, s.endpoint_pattern
                FROM sla_violations v
                LEFT JOIN performance_slas s ON v.sla_id = s.id
                WHERE v.execution_status = 'pending'
                ORDER BY v.detected_at DESC
            """)
            
            return [dict(row) for row in cursor.fetchall()]
    
    def get_violations_by_sla(self, sla_id: int, limit: int = 50) -> List[Dict]:
        """
        Obtener violaciones por SLA específico
        
        Args:
            sla_id: ID del SLA
            limit: Límite de resultados
            
        Returns:
            Lista de violaciones del SLA
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM sla_violations
                WHERE sla_id = ?
                ORDER BY detected_at DESC
                LIMIT ?
            """, (sla_id, limit))
            
            return [dict(row) for row in cursor.fetchall()]
    
    def get_violations_by_type(self, violation_type: str, 
                              start_date: datetime = None,
                              end_date: datetime = None) -> List[Dict]:
        """
        Obtener violaciones por tipo
        
        Args:
            violation_type: Tipo de violación
            start_date: Fecha inicio (opcional)
            end_date: Fecha fin (opcional)
            
        Returns:
            Lista de violaciones del tipo especificado
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            query = "SELECT * FROM sla_violations WHERE violation_type = ?"
            params = [violation_type]
            
            if start_date:
                query += " AND detected_at >= ?"
                params.append(start_date)
            
            if end_date:
                query += " AND detected_at <= ?"
                params.append(end_date)
            
            query += " ORDER BY detected_at DESC"
            
            cursor.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]
    
    def get_audit_report(self, start_date: datetime = None, 
                        end_date: datetime = None) -> Dict[str, Any]:
        """
        Generar reporte de auditoría de violaciones
        
        Args:
            start_date: Fecha inicio (opcional)
            end_date: Fecha fin (opcional)
            
        Returns:
            Reporte de auditoría completo
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Filtros de fecha
            date_filter = ""
            params = []
            
            if start_date or end_date:
                date_conditions = []
                if start_date:
                    date_conditions.append("detected_at >= ?")
                    params.append(start_date)
                if end_date:
                    date_conditions.append("detected_at <= ?")
                    params.append(end_date)
                date_filter = " WHERE " + " AND ".join(date_conditions)
            
            # Total de violaciones
            cursor.execute(f"SELECT COUNT(*) FROM sla_violations{date_filter}", params)
            total_violations = cursor.fetchone()[0]
            
            # Por estado
            cursor.execute(f"""
                SELECT execution_status, COUNT(*) 
                FROM sla_violations{date_filter}
                GROUP BY execution_status
            """, params)
            by_status = dict(cursor.fetchall())
            
            # Por tipo
            cursor.execute(f"""
                SELECT violation_type, COUNT(*) 
                FROM sla_violations{date_filter}
                GROUP BY violation_type
            """, params)
            by_type = dict(cursor.fetchall())
            
            # Riesgo promedio
            cursor.execute(f"""
                SELECT AVG(risk_score) 
                FROM sla_violations{date_filter}
                WHERE risk_score IS NOT NULL
            """, params)
            avg_risk = cursor.fetchone()[0] or 0
            
            return {
                "total_violations": total_violations,
                "by_status": by_status,
                "by_type": by_type,
                "average_risk_score": round(avg_risk, 2),
                "period": {
                    "start": start_date.isoformat() if start_date else None,
                    "end": end_date.isoformat() if end_date else None
                }
            }
    
    def get_violations_status(self) -> Dict[str, Any]:
        """
        Obtener estado general del sistema de violaciones
        
        Returns:
            Estado del sistema
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Contar total
            cursor.execute("SELECT COUNT(*) FROM sla_violations")
            total = cursor.fetchone()[0]
            
            # Contar pendientes
            cursor.execute("SELECT COUNT(*) FROM sla_violations WHERE execution_status = 'pending'")
            pending = cursor.fetchone()[0]
            
            # SLAs con violaciones
            cursor.execute("SELECT COUNT(DISTINCT sla_id) FROM sla_violations")
            slas_with_violations = cursor.fetchone()[0]
            
            # Total SLAs
            cursor.execute("SELECT COUNT(*) FROM performance_slas")
            total_slas = cursor.fetchone()[0]
            
            return {
                "database_path": self.db_path,
                "total_violations": total,
                "pending_violations": pending,
                "slas_with_violations": slas_with_violations,
                "total_slas": total_slas,
                "status": "active" if total > 0 else "ready"
            }

def create_sla_violations_repository(db_path: str = "data/qa_intelligence.db") -> SlaViolationsRepository:
    """
    Factory function para crear repositorio SLA Violations
    
    Args:
        db_path: Ruta a la base de datos principal
        
    Returns:
        Instancia de SlaViolationsRepository
    """
    return SlaViolationsRepository(db_path)
