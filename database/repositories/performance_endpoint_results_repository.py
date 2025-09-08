"""
Performance Endpoint Results Repository - Repository pattern for performance endpoint metrics

Repositorio para gestionar resultados de performance por endpoint con:
- CRUD operations básicas
- Consultas por execution_id
- Análisis de performance por endpoint
- Filtros por HTTP method y status
- Estadísticas y agregaciones
"""
from typing import List, Optional, Dict, Any
from sqlmodel import Session, select, func, and_, or_, col, Float
from datetime import datetime
from decimal import Decimal

from ..models.performance_endpoint_results import PerformanceEndpointResults
from .base import BaseRepository


class PerformanceEndpointResultsRepository(BaseRepository[PerformanceEndpointResults]):
    """Repository for Performance Endpoint Results with business logic"""
    
    def __init__(self, session: Session):
        super().__init__(session, PerformanceEndpointResults)
    
    # ===== CRUD Operations =====
    
    def create_endpoint_result(
        self,
        execution_id: str,
        endpoint_name: str,
        endpoint_url: Optional[str] = None,
        http_method: str = "GET",
        total_requests: int = 0,
        successful_requests: int = 0,
        failed_requests: int = 0,
        **kwargs
    ) -> PerformanceEndpointResults:
        """Create a new performance endpoint result"""
        endpoint_result = PerformanceEndpointResults(
            execution_id=execution_id,
            endpoint_name=endpoint_name,
            endpoint_url=endpoint_url,
            http_method=http_method,
            total_requests=total_requests,
            successful_requests=successful_requests,
            failed_requests=failed_requests,
            **kwargs
        )
        return self.save(endpoint_result)
    
    def update_endpoint_result(
        self,
        result_id: int,
        **updates
    ) -> Optional[PerformanceEndpointResults]:
        """Update an existing endpoint result"""
        endpoint_result = self.get_by_id(result_id)
        if not endpoint_result:
            return None
            
        if 'updated_at' not in updates:
            updates['updated_at'] = datetime.utcnow()
        
        for key, value in updates.items():
            if hasattr(endpoint_result, key):
                setattr(endpoint_result, key, value)
        
        return self.save(endpoint_result)
    
    # ===== Query Methods by Execution =====
    
    def get_by_execution_id(self, execution_id: str) -> List[PerformanceEndpointResults]:
        """Get all endpoint results for a specific execution"""
        statement = select(self.model_class).where(
            self.model_class.execution_id == execution_id
        ).order_by(self.model_class.endpoint_name)
        
        return list(self.session.exec(statement).all())
    
    def get_by_execution_and_endpoint(
        self, 
        execution_id: str, 
        endpoint_name: str
    ) -> Optional[PerformanceEndpointResults]:
        """Get specific endpoint result for an execution"""
        statement = select(self.model_class).where(
            and_(
                self.model_class.execution_id == execution_id,
                self.model_class.endpoint_name == endpoint_name
            )
        )
        
        return self.session.exec(statement).first()
    
    def get_by_execution_and_method(
        self, 
        execution_id: str, 
        http_method: str
    ) -> List[PerformanceEndpointResults]:
        """Get endpoint results by execution and HTTP method"""
        statement = select(self.model_class).where(
            and_(
                self.model_class.execution_id == execution_id,
                self.model_class.http_method == http_method.upper()
            )
        ).order_by(self.model_class.endpoint_name)
        
        return list(self.session.exec(statement).all())
    
    # ===== Analysis Methods =====
    
    def get_endpoints_with_high_error_rate(
        self, 
        execution_id: str, 
        min_error_rate: float = 5.0
    ) -> List[PerformanceEndpointResults]:
        """Get endpoints with error rate above threshold"""
        # Usamos col() para referenciar las columnas correctamente
        failed_col = col(PerformanceEndpointResults.failed_requests)
        total_col = col(PerformanceEndpointResults.total_requests)
        
        error_rate_calc = (func.cast(failed_col, Float) / func.cast(total_col, Float) * 100)
        
        statement = select(PerformanceEndpointResults).where(
            and_(
                PerformanceEndpointResults.execution_id == execution_id,
                PerformanceEndpointResults.total_requests > 0,
                error_rate_calc >= min_error_rate
            )
        ).order_by(error_rate_calc.desc())
        
        return list(self.session.exec(statement).all())
    
    def get_slowest_endpoints(
        self, 
        execution_id: str, 
        limit: int = 10
    ) -> List[PerformanceEndpointResults]:
        """Get slowest endpoints by p95 response time"""
        statement = select(PerformanceEndpointResults).where(
            and_(
                PerformanceEndpointResults.execution_id == execution_id,
                col(PerformanceEndpointResults.p95_response_time).is_not(None)
            )
        ).order_by(
            col(PerformanceEndpointResults.p95_response_time).desc()
        ).limit(limit)
        
        return list(self.session.exec(statement).all())
    
    def get_fastest_endpoints(
        self, 
        execution_id: str, 
        limit: int = 10
    ) -> List[PerformanceEndpointResults]:
        """Get fastest endpoints by p50 response time"""
        statement = select(PerformanceEndpointResults).where(
            and_(
                PerformanceEndpointResults.execution_id == execution_id,
                col(PerformanceEndpointResults.p50_response_time).is_not(None)
            )
        ).order_by(
            col(PerformanceEndpointResults.p50_response_time).asc()
        ).limit(limit)
        
        return list(self.session.exec(statement).all())
    
    def get_highest_throughput_endpoints(
        self, 
        execution_id: str, 
        limit: int = 10
    ) -> List[PerformanceEndpointResults]:
        """Get endpoints with highest RPS"""
        statement = select(PerformanceEndpointResults).where(
            and_(
                PerformanceEndpointResults.execution_id == execution_id,
                col(PerformanceEndpointResults.requests_per_second).is_not(None)
            )
        ).order_by(
            col(PerformanceEndpointResults.requests_per_second).desc()
        ).limit(limit)
        
        return list(self.session.exec(statement).all())
    
    # ===== Statistics Methods =====
    
    def get_execution_statistics(self, execution_id: str) -> Dict[str, Any]:
        """Get comprehensive statistics for an execution"""
        # Obtener todos los resultados para calcular estadísticas
        results = self.get_by_execution_id(execution_id)
        
        if not results:
            return {}
        
        total_requests = sum(r.total_requests for r in results)
        successful_requests = sum(r.successful_requests for r in results)
        failed_requests = sum(r.failed_requests for r in results)
        
        # Calcular promedios y máximos
        p50_times = [r.p50_response_time for r in results if r.p50_response_time]
        p95_times = [r.p95_response_time for r in results if r.p95_response_time]
        p99_times = [r.p99_response_time for r in results if r.p99_response_time]
        rps_values = [r.requests_per_second for r in results if r.requests_per_second]
        max_rps_values = [r.max_rps for r in results if r.max_rps]
        
        return {
            'total_endpoints': len(results),
            'total_requests': total_requests,
            'successful_requests': successful_requests,
            'failed_requests': failed_requests,
            'overall_error_rate': (
                (failed_requests / total_requests * 100) 
                if total_requests > 0 else 0
            ),
            'avg_p50_response_time': sum(p50_times) / len(p50_times) if p50_times else 0,
            'avg_p95_response_time': sum(p95_times) / len(p95_times) if p95_times else 0,
            'max_p99_response_time': max(p99_times) if p99_times else 0,
            'min_response_time': min(p50_times) if p50_times else 0,
            'avg_requests_per_second': sum(rps_values) / len(rps_values) if rps_values else 0,
            'peak_requests_per_second': max(max_rps_values) if max_rps_values else 0
        }
    
    def get_endpoint_trend_analysis(
        self, 
        execution_ids: List[str], 
        endpoint_name: str
    ) -> List[PerformanceEndpointResults]:
        """Get trend analysis for a specific endpoint across multiple executions"""
        statement = select(PerformanceEndpointResults).where(
            and_(
                col(PerformanceEndpointResults.execution_id).in_(execution_ids),
                PerformanceEndpointResults.endpoint_name == endpoint_name
            )
        ).order_by(PerformanceEndpointResults.execution_id)
        
        return list(self.session.exec(statement).all())
    
    def get_endpoint_performance_history(
        self, 
        endpoint_name: str, 
        limit: int = 50
    ) -> List[PerformanceEndpointResults]:
        """Get performance history for a specific endpoint"""
        statement = select(PerformanceEndpointResults).where(
            PerformanceEndpointResults.endpoint_name == endpoint_name
        ).order_by(
            col(PerformanceEndpointResults.created_at).desc()
        ).limit(limit)
        
        return list(self.session.exec(statement).all())
    
    def get_performance_trends(
        self, 
        endpoint_name: str, 
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Get performance trends for an endpoint across executions"""
        statement = select(PerformanceEndpointResults).where(
            PerformanceEndpointResults.endpoint_name == endpoint_name
        ).order_by(
            col(PerformanceEndpointResults.created_at).desc()
        ).limit(limit)
        
        results = self.session.exec(statement).all()
        
        return [
            {
                "execution_id": result.execution_id,
                "created_at": result.created_at,
                "total_requests": result.total_requests,
                "error_rate": result.error_rate,
                "p95_response_time": result.p95_response_time,
                "requests_per_second": result.requests_per_second,
                "performance_grade": result.performance_grade
            }
            for result in results
        ]
    
    # ===== Filtering Methods =====
    
    def get_endpoints_by_performance_grade(
        self, 
        execution_id: str, 
        grades: List[str]
    ) -> List[PerformanceEndpointResults]:
        """Get endpoints by performance grade (A, B, C, D, F)"""
        results = self.get_by_execution_id(execution_id)
        
        return [
            result for result in results 
            if result.performance_grade in grades
        ]
    
    def get_endpoints_with_issues(self, execution_id: str) -> Dict[str, List[PerformanceEndpointResults]]:
        """Get endpoints with various types of issues"""
        all_results = self.get_by_execution_id(execution_id)
        
        return {
            "high_error_rate": [
                r for r in all_results if r.error_rate >= 5.0
            ],
            "poor_performance": [
                r for r in all_results if r.performance_grade in ['D', 'F']
            ],
            "high_response_times": [
                r for r in all_results 
                if r.p95_response_time and r.p95_response_time > 2000
            ],
            "low_throughput": [
                r for r in all_results 
                if r.requests_per_second and r.requests_per_second < 10
            ]
        }
    
    # ===== Bulk Operations =====
    
    def create_bulk_results(
        self, 
        endpoint_results: List[PerformanceEndpointResults]
    ) -> List[PerformanceEndpointResults]:
        """Create multiple endpoint results in bulk"""
        for result in endpoint_results:
            self.session.add(result)
        self.session.commit()
        
        for result in endpoint_results:
            self.session.refresh(result)
        
        return endpoint_results
    
    def delete_by_execution_id(self, execution_id: str) -> int:
        """Delete all endpoint results for an execution"""
        results = self.get_by_execution_id(execution_id)
        
        for result in results:
            self.session.delete(result)
        
        self.session.commit()
        return len(results)
    
    # ===== Utility Methods =====
    
    def get_unique_endpoints(self, execution_id: str) -> List[str]:
        """Get list of unique endpoint names for an execution"""
        statement = select(col(PerformanceEndpointResults.endpoint_name)).where(
            PerformanceEndpointResults.execution_id == execution_id
        ).distinct()
        
        results = self.session.exec(statement).all()
        return list(results)
    
    def get_unique_http_methods(self, execution_id: str) -> List[str]:
        """Get list of unique HTTP methods for an execution"""
        statement = select(col(PerformanceEndpointResults.http_method)).where(
            PerformanceEndpointResults.execution_id == execution_id
        ).distinct()
        
        results = self.session.exec(statement).all()
        return list(results)
