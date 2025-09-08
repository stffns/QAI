#!/usr/bin/env python3
"""
Performance Engine V2 - Batch Execution Engine
Componente principal del engine de rendimiento para ejecuciones batch con monitorización en tiempo real
"""

import json
import csv
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Any

try:
    from src.logging_config import get_logger
except ImportError:
    import sys
    import os
    sys.path.append(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
    from src.logging_config import get_logger

from .models import (
    ExecutionStatus, 
    ProgressInfo, 
    BatchExecutionResult, 
    ExecutionStatusResponse,
    PerformanceEngineException
)
from .monitoring import GatlingOutputMonitor

logger = get_logger("PerformanceEngine")


def _create_empty_status_response(execution_id: str, status: ExecutionStatus, submitted_at: str = "", message: str = "") -> ExecutionStatusResponse:
    """Helper para crear ExecutionStatusResponse con valores por defecto"""
    return ExecutionStatusResponse(
        execution_id=execution_id,
        status=status,
        submitted_at=submitted_at,
        started_at=None,
        completed_at=None,
        progress_percentage=0.0,
        current_phase=status.value,
        message=message,
        waiting_users=0,
        active_users=0,
        completed_users=0,
        total_requests=0,
        successful_requests=0,
        failed_requests=0,
        mean_response_time=0.0,
        p95_response_time=None,
        current_rps=0.0,
        report_path=None,
        error_details=None
    )


def _progress_to_status_response(execution_id: str, progress: ProgressInfo, submitted_at: str, completed_at: Optional[str] = None, message: str = "") -> ExecutionStatusResponse:
    """Convierte ProgressInfo a ExecutionStatusResponse"""
    return ExecutionStatusResponse(
        execution_id=execution_id,
        status=progress.phase,
        submitted_at=submitted_at,
        started_at=None,
        completed_at=completed_at,
        progress_percentage=progress.percentage,
        current_phase=progress.phase.value,
        message=message or f"Real-time monitoring active - {progress.phase.value}",
        waiting_users=progress.waiting,
        active_users=progress.active,
        completed_users=progress.done,
        total_requests=progress.total_requests,
        successful_requests=progress.successful_requests,
        failed_requests=progress.failed_requests,
        mean_response_time=progress.mean_response_time,
        p95_response_time=None,
        current_rps=progress.current_rps,
        report_path=progress.report_path,
        error_details=progress.error_message
    )


class PerformanceEngineV2:
    """
    Performance Engine V2 con monitorización avanzada en tiempo real
    """
    
    def __init__(self, gatling_path: Optional[str] = None):
        if gatling_path is None:
            # Auto-detect gatling path
            current_dir = Path(__file__).parent.parent.parent.parent
            self.gatling_path = current_dir / "tools" / "gatling"
        else:
            self.gatling_path = Path(gatling_path)
        
        # Validar que existe
        if not self.gatling_path.exists():
            raise PerformanceEngineException(f"Gatling path not found: {self.gatling_path}")
        
        # Storage para execuciones activas
        self.active_executions: Dict[str, GatlingOutputMonitor] = {}
        self.execution_history: Dict[str, ExecutionStatusResponse] = {}
        
        logger.info(f"PerformanceEngineV2 initialized with gatling_path: {self.gatling_path}")
    
    def submit_simulation(self, config_json) -> BatchExecutionResult:
        """
        Envía simulación para ejecución batch con monitorización avanzada
        """
        execution_id = str(uuid.uuid4())
        submitted_at = datetime.now(timezone.utc).isoformat()
        
        try:
            # Parse configuration - accept both dict and JSON string
            if isinstance(config_json, dict):
                config = config_json
            else:
                config = json.loads(config_json)
            simulation_config = config.get("simulation_config", {})
            
            # Estimar duración
            duration_seconds = simulation_config.get("test_parameters", {}).get("duration_seconds", 60)
            estimated_duration = max(1, duration_seconds // 60)
            
            # Crear monitor
            log_file_path = f"/tmp/gatling_monitor_{execution_id}.log"
            monitor = GatlingOutputMonitor(execution_id, log_file_path)
            
            # Configurar callbacks del monitor
            monitor.on_progress_update = self._on_progress_update
            monitor.on_completion = self._on_completion
            monitor.on_error = self._on_error
            
            # Generar archivos necesarios y obtener nombre de CSV
            csv_filename = self._generate_csv_file(execution_id, config.get("endpoints", []))
            
            # Construir comando Gatling usando el CSV generado
            command = self._build_gatling_command(config, execution_id, csv_filename)
            
            # Iniciar ejecución con monitorización
            if monitor.start_monitoring(command, str(self.gatling_path)):
                # Registrar ejecución activa
                self.active_executions[execution_id] = monitor
                
                # Crear registro inicial en historial
                self.execution_history[execution_id] = _create_empty_status_response(
                    execution_id, ExecutionStatus.SUBMITTED, submitted_at, "Execution submitted with enhanced monitoring"
                )
                
                return BatchExecutionResult(
                    execution_id=execution_id,
                    status=ExecutionStatus.SUBMITTED,
                    submitted_at=submitted_at,
                    estimated_duration_minutes=estimated_duration,
                    message="Simulation submitted successfully with real-time monitoring"
                )
            else:
                raise PerformanceEngineException("Failed to start enhanced monitoring")
                
        except Exception as e:
            logger.error(f"Error submitting simulation: {e}")
            raise PerformanceEngineException(f"Simulation submission failed: {str(e)}")
    
    def get_execution_status(self, execution_id: str) -> ExecutionStatusResponse:
        """
        Obtiene estado actual con información de progreso en tiempo real
        """
        # Verificar en execuciones activas primero
        if execution_id in self.active_executions:
            monitor = self.active_executions[execution_id]
            progress = monitor.get_current_progress()
            
            # Obtener submitted_at del historial
            stored = self.execution_history.get(execution_id)
            submitted_at = stored.submitted_at if stored else ""
            
            return _progress_to_status_response(
                execution_id, progress, submitted_at or "", None, f"Real-time monitoring active - {progress.phase.value}"
            )
        
        # Verificar en historial
        if execution_id in self.execution_history:
            return self.execution_history[execution_id]
        
        # No encontrado
        raise PerformanceEngineException(f"Execution {execution_id} not found")
    
    def cancel_execution(self, execution_id: str) -> bool:
        """Cancela ejecución activa"""
        if execution_id in self.active_executions:
            monitor = self.active_executions[execution_id]
            if monitor.cancel_execution():
                # Obtener submitted_at del historial
                stored = self.execution_history.get(execution_id)
                submitted_at = stored.submitted_at if stored else ""
                
                # Mover a historial
                self.execution_history[execution_id] = _create_empty_status_response(
                    execution_id, ExecutionStatus.CANCELLED, submitted_at or "", "Execution cancelled by user"
                )
                self.execution_history[execution_id].completed_at = datetime.now(timezone.utc).isoformat()
                
                del self.active_executions[execution_id]
                return True
        return False
    
    def list_executions(self, limit: int = 10) -> List[ExecutionStatusResponse]:
        """Lista ejecuciones recientes"""
        all_executions = []
        
        # Agregar execuciones activas
        for execution_id, monitor in self.active_executions.items():
            progress = monitor.get_current_progress()
            # Obtener submitted_at del historial
            stored = self.execution_history.get(execution_id)
            submitted_at = stored.submitted_at if stored else ""
            
            all_executions.append(_progress_to_status_response(
                execution_id, progress, submitted_at or "", None, f"Active - {progress.phase.value}"
            ))
        
        # Agregar historial
        for execution_id, status in self.execution_history.items():
            if execution_id not in self.active_executions:
                all_executions.append(status)
        
        # Ordenar por fecha y limitar
        all_executions.sort(key=lambda x: x.submitted_at or "", reverse=True)
        return all_executions[:limit]
    
    # Callbacks para monitorización
    def _on_progress_update(self, execution_id: str, progress: ProgressInfo):
        """Callback de actualización de progreso"""
        logger.info(f"📊 Progress {execution_id[:8]}: {progress.phase.value} - {progress.percentage}% - {progress.total_requests} requests")
    
    def _on_completion(self, execution_id: str, progress: ProgressInfo):
        """Callback de finalización"""
        logger.info(f"🎉 Completed {execution_id[:8]}: {progress.total_requests} requests, {progress.successful_requests} successful")
        
        # Mover de activo a historial
        if execution_id in self.active_executions:
            # Obtener submitted_at del historial
            stored = self.execution_history.get(execution_id)
            submitted_at = stored.submitted_at if stored else ""
            
            self.execution_history[execution_id] = _progress_to_status_response(
                execution_id, progress, submitted_at or "", 
                datetime.now(timezone.utc).isoformat(), "Execution completed successfully"
            )
            self.execution_history[execution_id].progress_percentage = 100.0
            
            del self.active_executions[execution_id]
    
    def _on_error(self, execution_id: str, error_msg: str, progress: ProgressInfo):
        """Callback de error"""
        logger.error(f"🚨 Error {execution_id[:8]}: {error_msg}")
        
        # Mover a historial con error
        if execution_id in self.active_executions:
            # Obtener submitted_at del historial
            stored = self.execution_history.get(execution_id)
            submitted_at = stored.submitted_at if stored else ""
            
            self.execution_history[execution_id] = _progress_to_status_response(
                execution_id, progress, submitted_at or "", 
                datetime.now(timezone.utc).isoformat(), "Execution failed"
            )
            self.execution_history[execution_id].status = ExecutionStatus.FAILED
            self.execution_history[execution_id].error_details = error_msg
            
            del self.active_executions[execution_id]
    
    def _generate_csv_file(self, execution_id: str, endpoints: List[Dict]) -> str:
        """Genera archivo CSV para endpoints"""
        csv_filename = f"endpoints_{int(time.time())}.csv"
        csv_path = self.gatling_path / "src" / "test" / "resources" / csv_filename
        
        csv_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(csv_path, 'w', newline='') as csvfile:
            fieldnames = ['name', 'url', 'method', 'headers']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            
            for endpoint in endpoints:
                headers_str = json.dumps(endpoint.get('headers', {}))
                writer.writerow({
                    'name': endpoint.get('name', 'API Request'),
                    'url': endpoint.get('url', '/'),
                    'method': endpoint.get('method', 'GET'),
                    'headers': headers_str
                })
        
        logger.info(f"Generated CSV file: {csv_path}")
        return csv_filename
    
    def _build_gatling_command(self, config: Dict, execution_id: str, csv_filename: str) -> List[str]:
        """Construye comando Gatling optimizado"""
        simulation_config = config.get("simulation_config", {})
        test_params = simulation_config.get("test_parameters", {})
        
        # Headers como string
        headers = config.get("headers", {})
        headers_parts = []
        for key, value in headers.items():
            headers_parts.append(f"{key}:{value}")
        headers_str = ",".join(headers_parts)
        
        command = [
            "./mvnw", "gatling:test",
            f"-Dgatling.simulationClass=example.UniversalSimulation",
            f"-DbaseUrl={simulation_config.get('base_url', 'https://api.example.com')}",
            f"-Dvu={test_params.get('virtual_users', 1)}",
            f"-Dduration={test_params.get('duration_seconds', 60)}",
            f"-Drps={test_params.get('rps', 1.0)}",
            f"-DfeederType=csv",
            f"-DcsvFile={csv_filename}",
            f"-Dheaders={headers_str}"
        ]
        
        return command
    
    def get_engine_status(self) -> Dict[str, Any]:
        """Estado del engine"""
        return {
            "active_executions": len(self.active_executions),
            "total_executions": len(self.execution_history) + len(self.active_executions),
            "gatling_path": str(self.gatling_path),
            "monitoring_active": len(self.active_executions) > 0
        }
