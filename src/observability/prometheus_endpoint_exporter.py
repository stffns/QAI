#!/usr/bin/env python3
"""
Enhanced Prometheus Exporter con métricas por endpoint - QA Intelligence.

Extiende el exporter actual con métricas granulares por endpoint.
"""

import time
import threading
from typing import Dict, Any, List, Optional
from prometheus_client import Counter, Gauge, Histogram, start_http_server, CollectorRegistry, REGISTRY

# Setup path for imports
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), "..", ".."))

from database.repositories.unit_of_work import create_unit_of_work_factory
from database.repositories.performance_test_executions import PerformanceTestExecutionRepository
from database.repositories.performance_endpoint_results_repository import PerformanceEndpointResultsRepository
from database.models.performance_test_executions import ExecutionStatus
from database.models.performance_endpoint_results import PerformanceEndpointResults
from config import get_settings
from src.logging_config import get_logger

logger = get_logger("PrometheusEndpointExporter")

class EndpointMetricsExporter:
    """Exporter de métricas de Prometheus con datos granulares por endpoint."""
    
    def __init__(self, port: int = 9400, poll_interval: int = 10):
        self.port = port
        self.poll_interval = poll_interval
        self.settings = get_settings()
        self.uow_factory = create_unit_of_work_factory(self.settings.database.url)
        
        # Registry dedicado para evitar conflictos
        self.registry = CollectorRegistry()
        
        # Métricas de ejecuciones (existentes)
        self.executions_total = Gauge(
            'qa_perf_executions_total',
            'Total performance test executions by status (cumulative)',
            ['status'],
            registry=self.registry
        )
        
        self.executions_current = Gauge(
            'qa_perf_executions_current',
            'Current performance test executions by status',
            ['status'],
            registry=self.registry
        )
        
        # 🎯 NUEVAS MÉTRICAS POR ENDPOINT
        # Gauge de requests por endpoint - Fixed from Counter to avoid semantics violation
        self.endpoint_requests_total = Gauge(
            'qa_perf_endpoint_requests_total',
            'Total requests per endpoint (cumulative from database)',
            ['endpoint', 'method', 'status'],  # status = success/failed
            registry=self.registry
        )
        
        # Gauge de estado actual por endpoint
        self.endpoint_requests_current = Gauge(
            'qa_perf_endpoint_requests_current',
            'Current requests per endpoint from latest execution',
            ['endpoint', 'method', 'status'],
            registry=self.registry
        )
        
        # Histogram de response times por endpoint
        self.endpoint_response_time = Histogram(
            'qa_perf_endpoint_response_time_ms',
            'Response time distribution by endpoint',
            ['endpoint', 'method'],
            buckets=[10, 50, 100, 250, 500, 1000, 2000, 5000, 10000],  # ms
            registry=self.registry
        )
        
        # Gauge de métricas específicas por endpoint
        self.endpoint_p95_response_time = Gauge(
            'qa_perf_endpoint_p95_response_time_ms',
            'P95 response time by endpoint',
            ['endpoint', 'method'],
            registry=self.registry
        )
        
        self.endpoint_error_rate = Gauge(
            'qa_perf_endpoint_error_rate_percent',
            'Error rate percentage by endpoint',
            ['endpoint', 'method'],
            registry=self.registry
        )
        
        self.endpoint_throughput = Gauge(
            'qa_perf_endpoint_rps',
            'Requests per second by endpoint',
            ['endpoint', 'method'],
            registry=self.registry
        )
        
        # Gauge de performance grade por endpoint
        self.endpoint_performance_grade = Gauge(
            'qa_perf_endpoint_performance_grade',
            'Performance grade by endpoint (A=4, B=3, C=2, D=1, F=0)',
            ['endpoint', 'method', 'grade'],
            registry=self.registry
        )
        
        # 📊 MÉTRICAS AGREGADAS NUEVAS
        # Distribution de endpoints por status
        self.endpoints_by_status = Gauge(
            'qa_perf_endpoints_by_status_total',
            'Number of endpoints by performance status',
            ['status'],  # excellent/good/average/poor/failed
            registry=self.registry
        )
        
        # SLA compliance por endpoint (si implementamos SLA en el futuro)
        self.endpoint_sla_compliance = Gauge(
            'qa_perf_endpoint_sla_compliance',
            'SLA compliance by endpoint (1=pass, 0=fail)',
            ['endpoint', 'method'],
            registry=self.registry
        )
        
        # Thread para polling
        self._stop_event = threading.Event()
        self._metrics_thread = None
        
        logger.info(f"EndpointMetricsExporter initialized on port {port} with {poll_interval}s polling")
    
    def start(self):
        """Iniciar el exporter y servidor HTTP."""
        try:
            # Inicializar métricas
            self._collect_initial_metrics()
            
            # Iniciar servidor HTTP con registry dedicado
            start_http_server(self.port, registry=self.registry)
            logger.info(f"✅ Prometheus endpoint metrics server started on http://localhost:{self.port}/metrics")
            
            # Iniciar thread de polling
            self._metrics_thread = threading.Thread(target=self._polling_loop, daemon=True)
            self._metrics_thread.start()
            logger.info(f"🔄 Metrics polling started (every {self.poll_interval}s)")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to start endpoint metrics exporter: {e}")
            return False
    
    def stop(self):
        """Detener el exporter."""
        self._stop_event.set()
        if self._metrics_thread:
            self._metrics_thread.join(timeout=5)
        logger.info("📊 Prometheus endpoint metrics exporter stopped")
    
    def _polling_loop(self):
        """Loop principal de polling de métricas."""
        while not self._stop_event.wait(self.poll_interval):
            try:
                self._collect_all_metrics()
            except Exception as e:
                logger.error(f"Error collecting metrics: {e}")
    
    def _collect_initial_metrics(self):
        """Recolectar métricas iniciales para evitar scrape vacío."""
        try:
            self._collect_execution_metrics()
            self._collect_endpoint_metrics()
            logger.info("📊 Initial metrics collected successfully")
        except Exception as e:
            logger.warning(f"Failed to collect initial metrics: {e}")
    
    def _collect_all_metrics(self):
        """Recolectar todas las métricas."""
        try:
            self._collect_execution_metrics()
            self._collect_endpoint_metrics()
            
        except Exception as e:
            logger.error(f"Error in metrics collection: {e}")
    
    def _collect_execution_metrics(self):
        """Recolectar métricas de ejecuciones (existente)."""
        try:
            with self.uow_factory.create_scope() as uow:
                repo = uow.get_repository(PerformanceTestExecutionRepository)
                
                # Reset current gauges
                for status in [ExecutionStatus.PENDING, ExecutionStatus.RUNNING, ExecutionStatus.COMPLETED, ExecutionStatus.FAILED]:
                    executions = repo.find_by_status(status)
                    count = len(executions)
                    
                    self.executions_current.labels(status=status.value).set(count)
                    
                    # For terminal states, use gauge for database synchronization
                    # Note: Using Gauge instead of Counter because we're syncing from database state,
                    # not counting real-time events. Counters should only increment on actual events.
                    # This follows Prometheus best practices for metric semantics.
                    if status in [ExecutionStatus.COMPLETED, ExecutionStatus.FAILED]:
                        self.executions_total.labels(status=status.value).set(count)
                            
        except Exception as e:
            logger.error(f"Error collecting execution metrics: {e}")
    
    def _collect_endpoint_metrics(self):
        """🎯 Recolectar métricas granulares por endpoint."""
        try:
            with self.uow_factory.create_scope() as uow:
                # Get all endpoint results
                from sqlmodel import select
                stmt = select(PerformanceEndpointResults)
                endpoint_results = list(uow.session.exec(stmt).all())
                
                if not endpoint_results:
                    logger.debug("No endpoint results found")
                    return
                
                # Clear current gauges
                self._clear_endpoint_gauges()
                
                # Aggregate data by endpoint
                endpoint_aggregates = self._aggregate_endpoint_data(endpoint_results)
                
                # Update metrics
                self._update_endpoint_metrics(endpoint_aggregates)
                
                # Update distribution metrics
                self._update_distribution_metrics(endpoint_results)
                
                logger.debug(f"📊 Updated metrics for {len(endpoint_aggregates)} unique endpoints")
                
        except Exception as e:
            logger.error(f"Error collecting endpoint metrics: {e}")
    
    def _clear_endpoint_gauges(self):
        """Limpiar gauges de endpoints para evitar métricas obsoletas."""
        try:
            # Clear gauge metrics (not counters, as they are monotonic)
            self.endpoint_requests_current.clear()
            self.endpoint_p95_response_time.clear()
            self.endpoint_error_rate.clear()
            self.endpoint_throughput.clear()
            self.endpoint_performance_grade.clear()
            self.endpoint_sla_compliance.clear()
            self.endpoints_by_status.clear()
        except Exception as e:
            logger.warning(f"Error clearing endpoint gauges: {e}")
    
    def _aggregate_endpoint_data(self, endpoint_results: List[PerformanceEndpointResults]) -> Dict[str, Dict[str, Any]]:
        """Agregar datos por endpoint único."""
        aggregates = {}
        
        for result in endpoint_results:
            key = f"{result.http_method}:{result.endpoint_name}"
            
            if key not in aggregates:
                aggregates[key] = {
                    'endpoint': result.endpoint_name,
                    'method': result.http_method,
                    'total_requests': 0,
                    'successful_requests': 0,
                    'failed_requests': 0,
                    'total_response_time': 0.0,
                    'max_p95_response_time': 0.0,
                    'total_rps': 0.0,
                    'execution_count': 0,
                    'grades': {'A': 0, 'B': 0, 'C': 0, 'D': 0, 'F': 0},
                    'latest_execution': result.created_at,
                    'latest_result': result
                }
            
            agg = aggregates[key]
            
            # Accumulate totals
            agg['total_requests'] += result.total_requests
            agg['successful_requests'] += result.successful_requests
            agg['failed_requests'] += result.failed_requests
            agg['execution_count'] += 1
            
            # Track maximums
            if result.p95_response_time:
                agg['max_p95_response_time'] = max(agg['max_p95_response_time'], result.p95_response_time)
            
            if result.requests_per_second:
                agg['total_rps'] += result.requests_per_second
            
            # Track performance grades
            grade = result.performance_grade
            if grade in agg['grades']:
                agg['grades'][grade] += 1
            
            # Keep latest execution data
            if result.created_at and (not agg['latest_execution'] or result.created_at > agg['latest_execution']):
                agg['latest_execution'] = result.created_at
                agg['latest_result'] = result
        
        return aggregates
    
    def _update_endpoint_metrics(self, aggregates: Dict[str, Dict[str, Any]]):
        """Actualizar métricas de Prometheus con datos agregados."""
        for key, agg in aggregates.items():
            endpoint = agg['endpoint']
            method = agg['method']
            latest = agg['latest_result']
            
            # 📊 Request totals using Gauge for database synchronization
            self.endpoint_requests_total.labels(
                endpoint=endpoint, method=method, status='success'
            ).set(agg['successful_requests'])
            
            self.endpoint_requests_total.labels(
                endpoint=endpoint, method=method, status='failed'
            ).set(agg['failed_requests'])
            
            # Current gauges (from latest execution)
            self.endpoint_requests_current.labels(
                endpoint=endpoint, method=method, status='success'
            ).set(latest.successful_requests)
            
            self.endpoint_requests_current.labels(
                endpoint=endpoint, method=method, status='failed'
            ).set(latest.failed_requests)
            
            # 📈 Response time metrics
            if latest.p95_response_time:
                self.endpoint_p95_response_time.labels(
                    endpoint=endpoint, method=method
                ).set(latest.p95_response_time)
            
            # 🎯 Error rate
            error_rate = (agg['failed_requests'] / agg['total_requests'] * 100) if agg['total_requests'] > 0 else 0
            self.endpoint_error_rate.labels(
                endpoint=endpoint, method=method
            ).set(error_rate)
            
            # 🚀 Throughput (average RPS)
            avg_rps = agg['total_rps'] / agg['execution_count'] if agg['execution_count'] > 0 else 0
            self.endpoint_throughput.labels(
                endpoint=endpoint, method=method
            ).set(avg_rps)
            
            # 🏆 Performance grade (latest)
            grade_value = self._grade_to_numeric(latest.performance_grade)
            self.endpoint_performance_grade.labels(
                endpoint=endpoint, method=method, grade=latest.performance_grade or 'UNKNOWN'
            ).set(grade_value)
            
            # 📋 SLA compliance (placeholder - implement based on business rules)
            sla_compliance = 1 if error_rate < 5.0 and (latest.p95_response_time or 0) < 1000 else 0
            self.endpoint_sla_compliance.labels(
                endpoint=endpoint, method=method
            ).set(sla_compliance)
            
            # 📊 Response time histogram simulation
            if latest.avg_response_time:
                # Simulate histogram buckets based on avg response time
                self._update_response_time_histogram(endpoint, method, latest.avg_response_time, latest.total_requests)
    
    def _update_distribution_metrics(self, endpoint_results: List[PerformanceEndpointResults]):
        """Actualizar métricas de distribución."""
        grade_counts = {'A': 0, 'B': 0, 'C': 0, 'D': 0, 'F': 0, 'UNKNOWN': 0}
        
        for result in endpoint_results:
            grade = result.performance_grade or 'UNKNOWN'
            if grade in grade_counts:
                grade_counts[grade] += 1
        
        # Update distribution gauges
        for status, count in grade_counts.items():
            self.endpoints_by_status.labels(status=status.lower()).set(count)
    
    def _grade_to_numeric(self, grade: Optional[str]) -> float:
        """Convertir grade a valor numérico para Prometheus."""
        grade_map = {'A': 4.0, 'B': 3.0, 'C': 2.0, 'D': 1.0, 'F': 0.0}
        return grade_map.get(grade, -1.0)  # -1 for unknown
    
    def _update_response_time_histogram(self, endpoint: str, method: str, avg_time: float, request_count: int):
        """Simular datos de histogram para response times."""
        try:
            # Simulate histogram distribution based on average
            # This is a simplified approach - ideally we'd have raw response time data
            histogram = self.endpoint_response_time.labels(endpoint=endpoint, method=method)
            
            # Simulate request distribution across buckets
            for _ in range(min(request_count, 100)):  # Limit simulation for performance
                histogram.observe(avg_time)
                
        except Exception as e:
            logger.warning(f"Error updating response time histogram: {e}")

def main():
    """Punto de entrada principal."""
    print("🚀 Starting Enhanced Prometheus Endpoint Exporter...")
    
    exporter = EndpointMetricsExporter(port=9401, poll_interval=10)  # Different port to avoid conflicts
    
    if exporter.start():
        print("✅ Endpoint metrics exporter started successfully!")
        print("📊 Metrics available at: http://localhost:9401/metrics")
        print()
        print("🎯 NEW ENDPOINT METRICS:")
        print("  • qa_perf_endpoint_requests_total - Total requests per endpoint")
        print("  • qa_perf_endpoint_requests_current - Current requests per endpoint")
        print("  • qa_perf_endpoint_p95_response_time_ms - P95 response time per endpoint")
        print("  • qa_perf_endpoint_error_rate_percent - Error rate per endpoint")
        print("  • qa_perf_endpoint_rps - Throughput per endpoint")
        print("  • qa_perf_endpoint_performance_grade - Performance grade per endpoint")
        print("  • qa_perf_endpoint_sla_compliance - SLA compliance per endpoint")
        print("  • qa_perf_endpoints_by_status_total - Distribution by performance status")
        print()
        print("🏷️  Labels: endpoint, method, status, grade")
        print("🔄 Updates every 10 seconds")
        print()
        print("Press Ctrl+C to stop...")
        
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n🛑 Stopping exporter...")
            exporter.stop()
            print("✅ Stopped successfully")
    else:
        print("❌ Failed to start exporter")
        return 1
    
    return 0

if __name__ == "__main__":
    import sys
    sys.exit(main())
