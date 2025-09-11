"""
Enhanced Prometheus metrics for OpenAI health and process monitoring.

Extends the existing Prometheus setup to include:
- OpenAI service health status
- Long-running process detection
- Process cleanup metrics
- WebSocket connection health
"""

import time
import psutil
import os
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from prometheus_client import Counter, Gauge, Histogram, Info, CollectorRegistry

try:
    from src.monitoring.openai_health_monitor import OpenAIHealthMonitor, ServiceStatus
    from config import get_settings
    from database.repositories.unit_of_work import create_unit_of_work_factory
    from database.repositories.performance_test_executions import PerformanceTestExecutionRepository
    from database.models.performance_test_executions import ExecutionStatus
except ImportError:
    import sys
    import os
    sys.path.append(os.path.join(os.path.dirname(__file__), "..", ".."))
    from src.monitoring.openai_health_monitor import OpenAIHealthMonitor, ServiceStatus
    from config import get_settings
    from database.repositories.unit_of_work import create_unit_of_work_factory
    from database.repositories.performance_test_executions import PerformanceTestExecutionRepository
    from database.models.performance_test_executions import ExecutionStatus


# Use dedicated registry to avoid conflicts
HEALTH_REGISTRY = CollectorRegistry()

# OpenAI Health Metrics
OPENAI_STATUS = Gauge(
    "openai_service_status",
    "OpenAI service status (0=unknown, 1=healthy, 2=degraded, 3=outage)",
    registry=HEALTH_REGISTRY
)

OPENAI_RESPONSE_TIME = Gauge(
    "openai_response_time_seconds",
    "OpenAI API response time in seconds",
    registry=HEALTH_REGISTRY
)

OPENAI_UPTIME_PERCENTAGE = Gauge(
    "openai_uptime_percentage",
    "OpenAI service uptime percentage",
    registry=HEALTH_REGISTRY
)

OPENAI_HEALTH_CHECKS_TOTAL = Counter(
    "openai_health_checks_total",
    "Total number of OpenAI health checks performed",
    labelnames=("status",),
    registry=HEALTH_REGISTRY
)

# Process Health Metrics
LONG_RUNNING_PROCESSES = Gauge(
    "qa_long_running_processes",
    "Number of QA processes running longer than threshold",
    labelnames=("process_type", "threshold_minutes"),
    registry=HEALTH_REGISTRY
)

STUCK_EXECUTIONS = Gauge(
    "qa_stuck_executions",
    "Number of executions stuck in non-terminal states beyond normal duration",
    labelnames=("status", "age_category"),
    registry=HEALTH_REGISTRY
)

PROCESS_CLEANUP_OPERATIONS = Counter(
    "qa_process_cleanup_operations_total",
    "Total number of process cleanup operations",
    labelnames=("operation_type", "success"),
    registry=HEALTH_REGISTRY
)

# WebSocket Health Metrics
WEBSOCKET_CONNECTIONS = Gauge(
    "qa_websocket_connections_active",
    "Number of active WebSocket connections",
    registry=HEALTH_REGISTRY
)

WEBSOCKET_MESSAGES_FAILED = Counter(
    "qa_websocket_messages_failed_total",
    "Total number of failed WebSocket messages",
    labelnames=("failure_type",),
    registry=HEALTH_REGISTRY
)

# System Resource Metrics
SYSTEM_CPU_USAGE = Gauge(
    "qa_system_cpu_usage_percent",
    "Current CPU usage percentage for QA processes",
    registry=HEALTH_REGISTRY
)

SYSTEM_MEMORY_USAGE = Gauge(
    "qa_system_memory_usage_bytes",
    "Current memory usage in bytes for QA processes",
    registry=HEALTH_REGISTRY
)


class HealthMetricsCollector:
    """Collector for health and process metrics"""
    
    def __init__(self):
        self.health_monitor = OpenAIHealthMonitor()
        self.process_thresholds = {
            "websocket": 30,  # 30 minutes
            "qa_agent": 60,   # 60 minutes
            "test_execution": 15  # 15 minutes
        }
        
    async def collect_openai_health_metrics(self):
        """Collect OpenAI health status metrics"""
        try:
            # Use the health monitor directly
            result = await self.health_monitor.run_single_check()
            health_status = {
                "status": result.get("status", "unknown"),
                "response_time": 0
            }
            
            # Try to get response time from last check
            if result.get("last_check"):
                health_status["response_time"] = result["last_check"].get("response_time", 0)
            
            # Map status to numeric values
            status_mapping = {
                "healthy": 1,
                "degraded": 2,
                "outage": 3,
                "unknown": 0
            }
            
            status = health_status.get("status", "unknown")
            OPENAI_STATUS.set(status_mapping.get(status, 0))
            OPENAI_RESPONSE_TIME.set(health_status.get("response_time", 0))
            
            # Increment health check counter
            OPENAI_HEALTH_CHECKS_TOTAL.labels(status=status).inc()
            
            # Get uptime from monitor if available
            try:
                summary = self.health_monitor.get_health_summary()
                OPENAI_UPTIME_PERCENTAGE.set(summary.uptime_percentage)
            except Exception:
                pass
                
        except Exception as e:
            # If health check fails, record as unknown
            OPENAI_STATUS.set(0)
            OPENAI_HEALTH_CHECKS_TOTAL.labels(status="error").inc()
            print(f"Error collecting OpenAI health metrics: {e}")
    
    def collect_process_health_metrics(self):
        """Collect process health and detect long-running processes"""
        try:
            current_time = datetime.now()
            
            # Find QA-related processes
            qa_processes = []
            for proc in psutil.process_iter(['pid', 'name', 'cmdline', 'create_time', 'cpu_percent', 'memory_info']):
                try:
                    cmdline = ' '.join(proc.info['cmdline'] or [])
                    if any(keyword in cmdline.lower() for keyword in 
                           ['qa_agent', 'websocket_server', 'run_qa_agent', 'start_all_services']):
                        qa_processes.append(proc.info)
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            
            # Analyze process ages
            long_running_counts = {}
            total_cpu = 0
            total_memory = 0
            
            for proc_info in qa_processes:
                try:
                    create_time = datetime.fromtimestamp(proc_info['create_time'])
                    age_minutes = (current_time - create_time).total_seconds() / 60
                    
                    total_cpu += proc_info.get('cpu_percent', 0) or 0
                    memory_info = proc_info.get('memory_info')
                    if memory_info:
                        total_memory += memory_info.rss
                    
                    # Categorize process type
                    cmdline = ' '.join(proc_info.get('cmdline', []))
                    process_type = "other"
                    if "websocket" in cmdline.lower():
                        process_type = "websocket"
                    elif "qa_agent" in cmdline.lower():
                        process_type = "qa_agent"
                    elif "start_all_services" in cmdline.lower():
                        process_type = "service_manager"
                    
                    # Check thresholds
                    for threshold_name, threshold_minutes in self.process_thresholds.items():
                        if age_minutes > threshold_minutes:
                            key = f"{process_type}_{threshold_name}"
                            long_running_counts[key] = long_running_counts.get(key, 0) + 1
                            
                except Exception:
                    continue
            
            # Update metrics
            for key, count in long_running_counts.items():
                process_type, threshold = key.rsplit('_', 1)
                threshold_minutes = self.process_thresholds.get(threshold, 30)
                LONG_RUNNING_PROCESSES.labels(
                    process_type=process_type,
                    threshold_minutes=str(threshold_minutes)
                ).set(count)
            
            # Update system resource metrics
            SYSTEM_CPU_USAGE.set(total_cpu)
            SYSTEM_MEMORY_USAGE.set(total_memory)
            
        except Exception as e:
            print(f"Error collecting process metrics: {e}")
    
    def collect_execution_health_metrics(self, uow_factory):
        """Collect metrics about stuck executions"""
        if not uow_factory:
            return
            
        try:
            with uow_factory.create_scope() as uow:
                repo = uow.get_repository(PerformanceTestExecutionRepository)
                current_time = datetime.now()
                
                # Define age categories (in minutes)
                age_categories = {
                    "fresh": 5,      # 0-5 minutes
                    "normal": 15,    # 5-15 minutes
                    "stale": 60,     # 15-60 minutes
                    "stuck": 999999  # 60+ minutes
                }
                
                # Check PENDING and RUNNING executions
                for status in [ExecutionStatus.PENDING, ExecutionStatus.RUNNING]:
                    executions = repo.find_by_status(status)
                    
                    # Categorize by age
                    age_counts = {category: 0 for category in age_categories.keys()}
                    
                    for execution in executions:
                        try:
                            if execution.created_at:
                                age_minutes = (current_time - execution.created_at).total_seconds() / 60
                                
                                # Find appropriate age category
                                for category, max_age in age_categories.items():
                                    if age_minutes < max_age:
                                        age_counts[category] += 1
                                        break
                                else:
                                    age_counts["stuck"] += 1
                        except Exception:
                            continue
                    
                    # Update metrics
                    for category, count in age_counts.items():
                        STUCK_EXECUTIONS.labels(
                            status=status.value.lower(),
                            age_category=category
                        ).set(count)
                        
        except Exception as e:
            print(f"Error collecting execution health metrics: {e}")
    
    def cleanup_stuck_processes(self, uow_factory):
        """Identify and optionally cleanup stuck processes"""
        cleanup_count = 0
        error_count = 0
        
        try:
            # Check for executions stuck for more than 2 hours
            if uow_factory:
                with uow_factory.create_scope() as uow:
                    repo = uow.get_repository(PerformanceTestExecutionRepository)
                    current_time = datetime.now()
                    stuck_threshold = current_time - timedelta(hours=2)
                    
                    # Find stuck executions
                    for status in [ExecutionStatus.PENDING, ExecutionStatus.RUNNING]:
                        executions = repo.find_by_status(status)
                        
                        for execution in executions:
                            try:
                                if (execution.created_at and 
                                    execution.created_at < stuck_threshold):
                                    
                                    # Mark as failed with appropriate message
                                    execution.status = ExecutionStatus.FAILED
                                    execution.error_message = f"Execution stuck in {status.value} state for over 2 hours - automatically cleaned up"
                                    execution.completed_at = current_time
                                    
                                    repo.update(execution)
                                    cleanup_count += 1
                                    
                            except Exception as e:
                                error_count += 1
                                print(f"Error cleaning up execution {execution.id}: {e}")
            
            # Record cleanup metrics
            PROCESS_CLEANUP_OPERATIONS.labels(
                operation_type="stuck_execution_cleanup",
                success="true"
            ).inc(cleanup_count)
            
            if error_count > 0:
                PROCESS_CLEANUP_OPERATIONS.labels(
                    operation_type="stuck_execution_cleanup",
                    success="false"
                ).inc(error_count)
                
        except Exception as e:
            PROCESS_CLEANUP_OPERATIONS.labels(
                operation_type="stuck_execution_cleanup",
                success="false"
            ).inc(1)
            print(f"Error in cleanup process: {e}")
        
        return cleanup_count, error_count


async def collect_all_health_metrics(uow_factory=None):
    """Collect all health metrics"""
    collector = HealthMetricsCollector()
    
    # Collect OpenAI health metrics
    await collector.collect_openai_health_metrics()
    
    # Collect process health metrics
    collector.collect_process_health_metrics()
    
    # Collect execution health metrics
    collector.collect_execution_health_metrics(uow_factory)
    
    return collector


def run_health_metrics_exporter(port: int = 9401):
    """Run the health metrics exporter"""
    from prometheus_client import start_http_server
    import asyncio
    
    settings = get_settings()
    uow_factory = None
    
    try:
        if settings.database.url:
            uow_factory = create_unit_of_work_factory(settings.database.url)
    except Exception as e:
        print(f"Could not create UOW factory: {e}")
    
    # Start HTTP server with health registry
    start_http_server(port, registry=HEALTH_REGISTRY)
    print(f"🏥 Health metrics exporter started on port {port}")
    print(f"📊 Metrics available at http://localhost:{port}/metrics")
    
    async def metrics_loop():
        while True:
            try:
                collector = await collect_all_health_metrics(uow_factory)
                
                # Perform cleanup every 30 minutes
                if int(time.time()) % 1800 == 0:  # Every 30 minutes
                    cleanup_count, error_count = collector.cleanup_stuck_processes(uow_factory)
                    if cleanup_count > 0:
                        print(f"🧹 Cleaned up {cleanup_count} stuck executions")
                    if error_count > 0:
                        print(f"⚠️ {error_count} errors during cleanup")
                
            except Exception as e:
                print(f"Error in metrics collection: {e}")
            
            await asyncio.sleep(30)  # Collect every 30 seconds
    
    # Run the async loop
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(metrics_loop())
    except KeyboardInterrupt:
        print("🛑 Health metrics exporter stopped")
    finally:
        loop.close()


if __name__ == "__main__":
    run_health_metrics_exporter()
