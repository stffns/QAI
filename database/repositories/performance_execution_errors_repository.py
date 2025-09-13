"""
Performance Execution Errors Repository - Repository pattern for execution startup failures

Repositorio para gestionar errores que impiden el inicio de simulaciones con:
- CRUD operations básicas
- Consultas por execution_id y error_type
- Análisis de patrones de falla
- Estadísticas de errores recurrentes
- Filtros por categoría y severidad
"""
from typing import List, Optional, Dict, Any
from sqlmodel import Session, select, func, and_, or_, col
from datetime import datetime, timedelta

from ..models.performance_execution_errors import PerformanceExecutionErrors, ExecutionErrorType
from .base import BaseRepository


class PerformanceExecutionErrorsRepository(BaseRepository[PerformanceExecutionErrors]):
    """Repository for managing performance execution startup errors"""
    
    def __init__(self, session: Session):
        super().__init__(session, PerformanceExecutionErrors)
    
    # ===== Basic CRUD Operations =====
    
    def get_by_execution_id(self, execution_id: str) -> List[PerformanceExecutionErrors]:
        """Get all errors for a specific execution"""
        statement = select(PerformanceExecutionErrors).where(
            PerformanceExecutionErrors.execution_id == execution_id
        ).order_by(col(PerformanceExecutionErrors.occurred_at).desc())
        
        return list(self.session.exec(statement).all())
    
    def get_by_error_type(self, error_type: ExecutionErrorType) -> List[PerformanceExecutionErrors]:
        """Get all errors of a specific type"""
        statement = select(PerformanceExecutionErrors).where(
            PerformanceExecutionErrors.error_type == error_type
        ).order_by(col(PerformanceExecutionErrors.occurred_at).desc())
        
        return list(self.session.exec(statement).all())
    
    def get_recent_errors(self, hours: int = 24) -> List[PerformanceExecutionErrors]:
        """Get errors from the last N hours"""
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        
        statement = select(PerformanceExecutionErrors).where(
            col(PerformanceExecutionErrors.occurred_at) >= cutoff_time
        ).order_by(col(PerformanceExecutionErrors.occurred_at).desc())
        
        return list(self.session.exec(statement).all())
    
    # ===== Analysis Methods =====
    
    def get_error_statistics(self, days: int = 7) -> Dict[str, Any]:
        """Get comprehensive error statistics for the last N days"""
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        # Get all errors in the period
        errors = self.session.exec(
            select(PerformanceExecutionErrors).where(
                col(PerformanceExecutionErrors.occurred_at) >= cutoff_date
            )
        ).all()
        
        if not errors:
            return {}
        
        # Calculate statistics
        total_errors = len(errors)
        error_types = {}
        severity_counts = {}
        category_counts = {}
        daily_counts = {}
        
        for error in errors:
            # Error type distribution
            error_type = error.error_type.value
            error_types[error_type] = error_types.get(error_type, 0) + 1
            
            # Severity distribution
            severity = error.severity_level
            severity_counts[severity] = severity_counts.get(severity, 0) + 1
            
            # Category distribution
            category = error.error_category
            category_counts[category] = category_counts.get(category, 0) + 1
            
            # Daily distribution
            day = error.occurred_at.date().isoformat()
            daily_counts[day] = daily_counts.get(day, 0) + 1
        
        return {
            'period_days': days,
            'total_errors': total_errors,
            'error_types': error_types,
            'severity_distribution': severity_counts,
            'category_distribution': category_counts,
            'daily_counts': daily_counts,
            'most_common_error': max(error_types, key=lambda k: error_types[k]) if error_types else None,
            'error_rate_per_day': total_errors / days
        }
    
    def get_most_frequent_errors(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get most frequent error patterns"""
        # Simplify to get error patterns by type and message
        errors = self.session.exec(select(PerformanceExecutionErrors)).all()
        
        # Group by error pattern manually
        patterns = {}
        for error in errors:
            key = (error.error_type.value, error.error_message[:100])
            if key not in patterns:
                patterns[key] = {
                    'error_type': error.error_type.value,
                    'message_pattern': error.error_message[:100],
                    'occurrence_count': 0,
                    'last_occurrence': error.occurred_at
                }
            patterns[key]['occurrence_count'] += 1
            if error.occurred_at > patterns[key]['last_occurrence']:
                patterns[key]['last_occurrence'] = error.occurred_at
        
        # Sort by occurrence count and limit
        sorted_patterns = sorted(patterns.values(), key=lambda x: x['occurrence_count'], reverse=True)
        
        # Format response
        return [
            {
                'error_type': pattern['error_type'],
                'message_pattern': pattern['message_pattern'],
                'occurrence_count': pattern['occurrence_count'],
                'last_occurrence': pattern['last_occurrence'].isoformat()
            }
            for pattern in sorted_patterns[:limit]
        ]
    
    def get_executions_with_errors(self, error_type: Optional[ExecutionErrorType] = None) -> List[str]:
        """Get list of execution IDs that have errors"""
        statement = select(PerformanceExecutionErrors.execution_id).distinct()
        
        if error_type:
            statement = statement.where(PerformanceExecutionErrors.error_type == error_type)
        
        results = self.session.exec(statement).all()
        return list(results)
    
    def get_error_trends(self, days: int = 30) -> Dict[str, List[Dict[str, Any]]]:
        """Get error trends by type over time"""
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        # Get all errors in the period
        errors = self.session.exec(
            select(PerformanceExecutionErrors).where(
                col(PerformanceExecutionErrors.occurred_at) >= cutoff_date
            ).order_by(col(PerformanceExecutionErrors.occurred_at).asc())
        ).all()
        
        # Group manually by error type and date
        trends = {}
        for error in errors:
            error_type = error.error_type.value
            error_date = error.occurred_at.date()
            
            if error_type not in trends:
                trends[error_type] = {}
            
            date_str = error_date.isoformat()
            if date_str not in trends[error_type]:
                trends[error_type][date_str] = 0
            
            trends[error_type][date_str] += 1
        
        # Convert to the expected format
        result = {}
        for error_type, date_counts in trends.items():
            result[error_type] = [
                {'date': date, 'count': count}
                for date, count in sorted(date_counts.items())
            ]
        
        return result
    
    # ===== Filtering Methods =====
    
    def get_errors_by_severity(self, severity: str) -> List[PerformanceExecutionErrors]:
        """Get errors by severity level"""
        all_errors = self.session.exec(select(PerformanceExecutionErrors)).all()
        
        return [error for error in all_errors if error.severity_level == severity]
    
    def get_errors_by_category(self, category: str) -> List[PerformanceExecutionErrors]:
        """Get errors by category (Configuration, Technical, Unknown)"""
        all_errors = self.session.exec(select(PerformanceExecutionErrors)).all()
        
        return [error for error in all_errors if error.error_category == category]
    
    def get_configuration_errors(self) -> List[PerformanceExecutionErrors]:
        """Get all configuration-related errors"""
        statement = select(PerformanceExecutionErrors).where(
            or_(
                PerformanceExecutionErrors.error_type == ExecutionErrorType.CONFIG_ERROR,
                PerformanceExecutionErrors.error_type == ExecutionErrorType.VALIDATION_ERROR
            )
        ).order_by(col(PerformanceExecutionErrors.occurred_at).desc())
        
        return list(self.session.exec(statement).all())
    
    def get_technical_errors(self) -> List[PerformanceExecutionErrors]:
        """Get all technical/infrastructure errors"""
        statement = select(PerformanceExecutionErrors).where(
            or_(
                PerformanceExecutionErrors.error_type == ExecutionErrorType.SETUP_ERROR,
                PerformanceExecutionErrors.error_type == ExecutionErrorType.INFRASTRUCTURE_ERROR
            )
        ).order_by(col(PerformanceExecutionErrors.occurred_at).desc())
        
        return list(self.session.exec(statement).all())
    
    def search_by_message(self, search_term: str) -> List[PerformanceExecutionErrors]:
        """Search errors by message content"""
        statement = select(PerformanceExecutionErrors).where(
            col(PerformanceExecutionErrors.error_message).like(f"%{search_term}%")
        ).order_by(col(PerformanceExecutionErrors.occurred_at).desc())
        
        return list(self.session.exec(statement).all())
    
    # ===== Bulk Operations =====
    
    def create_bulk_errors(
        self, 
        errors: List[PerformanceExecutionErrors]
    ) -> List[PerformanceExecutionErrors]:
        """Create multiple error records in bulk"""
        for error in errors:
            self.session.add(error)
        self.session.commit()
        
        for error in errors:
            self.session.refresh(error)
        
        return errors
    
    def delete_old_errors(self, days: int = 90) -> int:
        """Delete errors older than N days"""
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        old_errors = self.session.exec(
            select(PerformanceExecutionErrors).where(
                col(PerformanceExecutionErrors.occurred_at) < cutoff_date
            )
        ).all()
        
        count = len(old_errors)
        
        for error in old_errors:
            self.session.delete(error)
        
        self.session.commit()
        return count
    
    def delete_by_execution_id(self, execution_id: str) -> int:
        """Delete all errors for a specific execution"""
        errors = self.get_by_execution_id(execution_id)
        
        for error in errors:
            self.session.delete(error)
        
        self.session.commit()
        return len(errors)
    
    # ===== Pattern Analysis =====
    
    def find_similar_errors(
        self, 
        error: PerformanceExecutionErrors, 
        limit: int = 5
    ) -> List[PerformanceExecutionErrors]:
        """Find errors similar to the given error"""
        # Get errors of the same type
        candidates = self.get_by_error_type(error.error_type)
        
        # Filter for similar errors (excluding the error itself)
        similar = []
        for candidate in candidates:
            if candidate.id != error.id and error.is_similar_to(candidate):
                similar.append(candidate)
                if len(similar) >= limit:
                    break
        
        return similar
    
    def get_recurring_execution_errors(self, min_occurrences: int = 3) -> Dict[str, List[PerformanceExecutionErrors]]:
        """Get executions that have recurring errors"""
        # Get all errors and group by execution_id
        all_errors = self.session.exec(select(PerformanceExecutionErrors)).all()
        
        # Group by execution_id
        execution_groups = {}
        for error in all_errors:
            execution_id = error.execution_id
            if execution_id not in execution_groups:
                execution_groups[execution_id] = []
            execution_groups[execution_id].append(error)
        
        # Filter executions with minimum occurrences
        recurring = {}
        for execution_id, errors in execution_groups.items():
            if len(errors) >= min_occurrences:
                recurring[execution_id] = errors
        
        return recurring
    
    # ===== Utility Methods =====
    
    def get_unique_error_messages(self, error_type: Optional[ExecutionErrorType] = None) -> List[str]:
        """Get list of unique error message patterns"""
        statement = select(PerformanceExecutionErrors.error_message).distinct()
        
        if error_type:
            statement = statement.where(PerformanceExecutionErrors.error_type == error_type)
        
        results = self.session.exec(statement).all()
        return list(results)
    
    def get_execution_failure_summary(self, execution_id: str) -> Dict[str, Any]:
        """Get a comprehensive failure summary for an execution"""
        errors = self.get_by_execution_id(execution_id)
        
        if not errors:
            return {'execution_id': execution_id, 'has_errors': False}
        
        error_types = [error.error_type.value for error in errors]
        severities = [error.severity_level for error in errors]
        categories = [error.error_category for error in errors]
        
        return {
            'execution_id': execution_id,
            'has_errors': True,
            'error_count': len(errors),
            'error_types': list(set(error_types)),
            'severities': list(set(severities)),
            'categories': list(set(categories)),
            'first_error': errors[-1].occurred_at.isoformat() if errors else None,
            'last_error': errors[0].occurred_at.isoformat() if errors else None,
            'has_critical_errors': 'CRITICAL' in severities,
            'is_configuration_issue': any(error.is_configuration_related for error in errors),
            'is_technical_issue': any(error.is_technical_failure for error in errors)
        }
