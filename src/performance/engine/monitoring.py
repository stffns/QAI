"""
Engine Monitoring - Real-time Gatling output monitoring

Handles real-time monitoring of Gatling execution:
- Log file parsing and analysis
- Progress tracking and metrics extraction
- Error detection and handling
- Callback-based event notification

Extracted from performance_engine_v2_enhanced.py
"""

import logging
import subprocess
import threading
import time
import re
from pathlib import Path
from typing import List, Optional, Callable

from .models import ExecutionStatus, ProgressInfo

# Configure logging
logger = logging.getLogger(__name__)


class GatlingOutputMonitor:
    """
    Monitor inteligente del output de Gatling con callbacks
    """
    
    def __init__(self, execution_id: str, log_file_path: str):
        self.execution_id = execution_id
        self.log_file_path = Path(log_file_path)
        self.is_monitoring = False
        self.process: Optional[subprocess.Popen] = None
        self.progress_info = ProgressInfo(
            phase=ExecutionStatus.SUBMITTED,
            percentage=0.0,
            waiting=0,
            active=0,
            done=0,
            total=0,
            current_rps=0.0,
            total_requests=0,
            successful_requests=0,
            failed_requests=0,
            mean_response_time=0.0,
            message=""
        )
        
        # Callbacks para el engine
        self.on_progress_update: Optional[Callable[[str, ProgressInfo], None]] = None
        self.on_completion: Optional[Callable[[str, ProgressInfo], None]] = None
        self.on_error: Optional[Callable[[str, str, ProgressInfo], None]] = None
        
        # Patrones regex optimizados
        self.patterns = {
            'progress_bar': re.compile(r'\[([#\s]+)\]\s+(\d+\.?\d*)%'),
            'user_stats': re.compile(r'waiting:\s+(\d+)\s+/\s+active:\s+(\d+)\s+/\s+done:\s+(\d+)'),
            'request_stats': re.compile(r'>\s+Global\s+\|\s+(\d+)\s+\|\s+(\d+)\s+\|\s+(\d+)'),
            'mean_response_time': re.compile(r'>\s+mean response time \(ms\)\s+\|\s+(\d+\.?\d*)'),
            'p95_response_time': re.compile(r'>\s+response time 95th percentile \(ms\)\s+\|\s+([0-9,.]+)'),
            'throughput': re.compile(r'>\s+mean throughput \(rps\)\s+\|\s+(\d+\.?\d*)'),
            'build_failure': re.compile(r'\[INFO\]\s+BUILD FAILURE'),
            'build_success': re.compile(r'\[INFO\]\s+BUILD SUCCESS'),
            'error_message': re.compile(r'\[ERROR\](.+)'),
            'parsing_logs': re.compile(r'Parsing log file\(s\)\.{3}'),
            'generating_reports': re.compile(r'Generating reports\.{3}'),
            'reports_generated': re.compile(r'Reports generated, please open the following file: (.+)'),
            'simulation_running': re.compile(r'\[INFO\] Running simulation (.+)'),
            'gatling_failed': re.compile(r'Gatling simulation assertions failed')
        }
    
    def start_monitoring(self, command: List[str], cwd: str) -> bool:
        """Inicia ejecución con monitorización en tiempo real"""
        try:
            # Crear directorio para log
            self.log_file_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Comando con tee para captura dual
            shell_command = ' '.join(command) + f' 2>&1 | tee {self.log_file_path}'
            
            logger.info(f"Starting Gatling with enhanced monitoring: {shell_command}")
            
            # Ejecutar con shell para usar tee
            self.process = subprocess.Popen(
                shell_command,
                shell=True,
                cwd=cwd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                universal_newlines=True
            )
            
            # Iniciar monitorización en hilo separado
            self.is_monitoring = True
            monitor_thread = threading.Thread(
                target=self._monitor_output, 
                name=f"GatlingMonitor-{self.execution_id[:8]}", 
                daemon=True
            )
            monitor_thread.start()
            
            return True
            
        except Exception as e:
            logger.error(f"Error starting monitoring: {e}")
            return False
    
    def _monitor_output(self):
        """Monitoriza el archivo de log en tiempo real"""
        logger.info(f"🔍 Enhanced monitoring started for {self.execution_id}")
        
        last_position = 0
        stable_count = 0
        max_stable_checks = 6  # 30 segundos sin cambios
        
        while self.is_monitoring:
            try:
                if self.log_file_path.exists():
                    current_size = self.log_file_path.stat().st_size
                    
                    if current_size > last_position:
                        # Hay nuevos datos - procesar
                        stable_count = 0
                        new_lines = self._read_new_lines(last_position)
                        last_position = current_size
                        
                        # Procesar cada línea nueva
                        for line in new_lines:
                            if line.strip():
                                self._process_log_line(line.strip())
                        
                        # Notificar progreso
                        if self.on_progress_update:
                            self.on_progress_update(self.execution_id, self.progress_info)
                            
                    else:
                        # Sin cambios - verificar si terminó
                        stable_count += 1
                        if stable_count >= max_stable_checks:
                            if self._check_process_completion():
                                break
                            
                time.sleep(5)  # Check every 5 seconds
                
            except Exception as e:
                logger.error(f"Monitor error: {e}")
                time.sleep(5)
        
        logger.info(f"🏁 Enhanced monitoring finished for {self.execution_id}")
    
    def _read_new_lines(self, from_position: int) -> List[str]:
        """Lee nuevas líneas desde posición específica"""
        try:
            with open(self.log_file_path, 'r', encoding='utf-8', errors='ignore') as f:
                f.seek(from_position)
                new_content = f.read()
                return new_content.split('\n') if new_content else []
        except Exception as e:
            logger.warning(f"Error reading log file: {e}")
            return []
    
    def _process_log_line(self, line: str):
        """Procesa línea del log para extraer información"""
        if not line.strip():
            return
            
        # Detectar fase actual
        if self.patterns['simulation_running'].search(line):
            self.progress_info.phase = ExecutionStatus.RUNNING
            logger.info(f"📊 Phase: RUNNING")
            
        elif self.patterns['parsing_logs'].search(line):
            self.progress_info.phase = ExecutionStatus.PARSING
            logger.info(f"📊 Phase: PARSING")
            
        elif self.patterns['generating_reports'].search(line):
            self.progress_info.phase = ExecutionStatus.GENERATING_REPORTS
            logger.info(f"📊 Phase: GENERATING_REPORTS")
            
        # Detectar completion exitoso
        reports_match = self.patterns['reports_generated'].search(line)
        if reports_match:
            self.progress_info.phase = ExecutionStatus.COMPLETED
            report_path = reports_match.group(1).strip()
            self.progress_info.message = f"Report generated: {report_path}"
            logger.info(f"✅ COMPLETED - Report: {report_path}")
            
            if self.on_completion:
                self.on_completion(self.execution_id, self.progress_info)
            self.is_monitoring = False
            return
        
        # Detectar errores
        if self.patterns['build_failure'].search(line) or self.patterns['gatling_failed'].search(line):
            self.progress_info.phase = ExecutionStatus.FAILED
            logger.warning(f"❌ BUILD FAILURE detected")
            
        error_match = self.patterns['error_message'].search(line)
        if error_match:
            error_msg = error_match.group(1).strip()
            self.progress_info.message = f"Error: {error_msg}"
            logger.warning(f"🚨 ERROR: {error_msg}")
            
            if self.on_error:
                self.on_error(self.execution_id, error_msg, self.progress_info)
            
            # Errores críticos detienen monitorización
            if 'FAILURE' in line or 'failed' in error_msg.lower():
                self.progress_info.phase = ExecutionStatus.FAILED
                self.is_monitoring = False
                return
        
        # Extraer métricas de progreso
        progress_match = self.patterns['progress_bar'].search(line)
        if progress_match:
            self.progress_info.percentage = float(progress_match.group(2))
            
        user_stats_match = self.patterns['user_stats'].search(line)
        if user_stats_match:
            self.progress_info.waiting = int(user_stats_match.group(1))
            self.progress_info.active = int(user_stats_match.group(2))
            self.progress_info.done = int(user_stats_match.group(3))
            
        request_stats_match = self.patterns['request_stats'].search(line)
        if request_stats_match:
            self.progress_info.total_requests = int(request_stats_match.group(1))
            self.progress_info.successful_requests = int(request_stats_match.group(2))
            self.progress_info.failed_requests = int(request_stats_match.group(3))
            
        # Extraer métricas de rendimiento
        response_time_match = self.patterns['mean_response_time'].search(line)
        if response_time_match:
            try:
                self.progress_info.mean_response_time = float(response_time_match.group(1))
            except ValueError:
                pass
        
        p95_match = self.patterns['p95_response_time'].search(line)
        if p95_match:
            try:
                val = p95_match.group(1).replace(',', '')
                self.progress_info.p95_response_time = float(val)
            except ValueError:
                pass
        
        throughput_match = self.patterns['throughput'].search(line)
        if throughput_match:
            try:
                self.progress_info.current_rps = float(throughput_match.group(1))
            except ValueError:
                pass
    
    def _check_process_completion(self) -> bool:
        """Verifica si el proceso terminó"""
        if self.process and self.process.poll() is not None:
            logger.info(f"✅ Process completed with code: {self.process.returncode}")
            
            if self.process.returncode == 0:
                self.progress_info.phase = ExecutionStatus.COMPLETED
            else:
                self.progress_info.phase = ExecutionStatus.FAILED
                
            if self.on_completion:
                self.on_completion(self.execution_id, self.progress_info)
            return True
        return False
    
    def cancel_execution(self) -> bool:
        """Cancela la ejecución"""
        try:
            if self.process and self.process.poll() is None:
                logger.info(f"🛑 Cancelling execution {self.execution_id}")
                self.process.terminate()
                time.sleep(2)
                if self.process.poll() is None:
                    self.process.kill()
                self.is_monitoring = False
                self.progress_info.phase = ExecutionStatus.CANCELLED
                return True
        except Exception as e:
            logger.error(f"Error cancelling execution: {e}")
        return False
    
    def get_current_progress(self) -> ProgressInfo:
        """Retorna progreso actual"""
        return self.progress_info
