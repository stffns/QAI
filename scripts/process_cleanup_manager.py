#!/usr/bin/env python3
"""
Process Cleanup and Recovery Tool

Herramienta para detectar y limpiar procesos que se quedaron en estados inconsistentes
debido a intermitencias de OpenAI u otros problemas.
"""

import asyncio
import json
import time
import psutil
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional

try:
    from config import get_settings
    from database.repositories.unit_of_work import create_unit_of_work_factory
    from database.repositories.performance_test_executions import PerformanceTestExecutionRepository
    from database.models.performance_test_executions import ExecutionStatus
    from src.observability.health_prometheus_exporter import HealthMetricsCollector
except ImportError:
    import sys
    import os
    sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
    from config import get_settings
    from database.repositories.unit_of_work import create_unit_of_work_factory
    from database.repositories.performance_test_executions import PerformanceTestExecutionRepository
    from database.models.performance_test_executions import ExecutionStatus
    from src.observability.health_prometheus_exporter import HealthMetricsCollector


class ProcessCleanupManager:
    """Manager para limpiar procesos y execuciones en estado inconsistente"""
    
    def __init__(self):
        self.settings = get_settings()
        self.uow_factory = None
        try:
            if self.settings.database.url:
                self.uow_factory = create_unit_of_work_factory(self.settings.database.url)
        except Exception as e:
            print(f"⚠️ Could not create database connection: {e}")
        
        self.health_collector = HealthMetricsCollector()
    
    def find_qa_processes(self) -> List[Dict[str, Any]]:
        """Encontrar todos los procesos relacionados con QA"""
        qa_processes = []
        
        for proc in psutil.process_iter(['pid', 'name', 'cmdline', 'create_time', 'status', 'cpu_percent', 'memory_info']):
            try:
                cmdline = ' '.join(proc.info['cmdline'] or [])
                if any(keyword in cmdline.lower() for keyword in 
                       ['qa_agent', 'websocket_server', 'run_qa_agent', 'start_all_services', 
                        'prometheus_exporter', 'health_prometheus']):
                    
                    process_info = proc.info.copy()
                    process_info['age_minutes'] = (datetime.now() - datetime.fromtimestamp(proc.info['create_time'])).total_seconds() / 60
                    process_info['cmdline_str'] = cmdline
                    qa_processes.append(process_info)
                    
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue
        
        return qa_processes
    
    def analyze_stuck_executions(self) -> Dict[str, Any]:
        """Analizar execuciones que podrían estar atascadas"""
        if not self.uow_factory:
            return {"error": "No database connection available"}
        
        try:
            with self.uow_factory.create_scope() as uow:
                repo = uow.get_repository(PerformanceTestExecutionRepository)
                current_time = datetime.now()
                
                analysis = {
                    "pending_executions": [],
                    "running_executions": [],
                    "stuck_executions": [],
                    "total_stuck": 0
                }
                
                # Thresholds for different states
                stuck_threshold = current_time - timedelta(hours=2)  # 2 hours
                warning_threshold = current_time - timedelta(minutes=30)  # 30 minutes
                
                for status in [ExecutionStatus.PENDING, ExecutionStatus.RUNNING]:
                    executions = repo.find_by_status(status)
                    
                    for execution in executions:
                        exec_info = {
                            "id": execution.id,
                            "execution_id": execution.execution_id,
                            "status": execution.status.value,
                            "created_at": execution.created_at.isoformat() if execution.created_at else None,
                            "start_time": execution.start_time.isoformat() if execution.start_time else None,
                            "execution_name": execution.execution_name,
                            "age_minutes": 0,
                            "is_stuck": False,
                            "is_warning": False
                        }
                        
                        if execution.created_at:
                            age_minutes = (current_time - execution.created_at).total_seconds() / 60
                            exec_info["age_minutes"] = age_minutes
                            
                            if execution.created_at < stuck_threshold:
                                exec_info["is_stuck"] = True
                                analysis["stuck_executions"].append(exec_info)
                                analysis["total_stuck"] += 1
                            elif execution.created_at < warning_threshold:
                                exec_info["is_warning"] = True
                        
                        if status == ExecutionStatus.PENDING:
                            analysis["pending_executions"].append(exec_info)
                        else:
                            analysis["running_executions"].append(exec_info)
                
                return analysis
                
        except Exception as e:
            return {"error": f"Error analyzing executions: {str(e)}"}
    
    def cleanup_stuck_executions(self, dry_run: bool = True) -> Dict[str, Any]:
        """Limpiar execuciones atascadas"""
        if not self.uow_factory:
            return {"error": "No database connection available"}
        
        result = {
            "cleaned_up": 0,
            "errors": 0,
            "executions_cleaned": [],
            "dry_run": dry_run
        }
        
        try:
            with self.uow_factory.create_scope() as uow:
                repo = uow.get_repository(PerformanceTestExecutionRepository)
                current_time = datetime.now()
                stuck_threshold = current_time - timedelta(hours=2)
                
                for status in [ExecutionStatus.PENDING, ExecutionStatus.RUNNING]:
                    executions = repo.find_by_status(status)
                    
                    for execution in executions:
                        try:
                            if (execution.created_at and 
                                execution.created_at < stuck_threshold):
                                
                                exec_info = {
                                    "id": execution.id,
                                    "execution_id": execution.execution_id,
                                    "original_status": execution.status.value,
                                    "age_hours": (current_time - execution.created_at).total_seconds() / 3600,
                                    "execution_name": execution.execution_name
                                }
                                
                                if not dry_run:
                                    # Mark as failed with cleanup message using update_status and update_metrics
                                    repo.update_status(
                                        execution_id=execution.execution_id,
                                        status=ExecutionStatus.FAILED,
                                        end_time=current_time,
                                        updated_by="process_cleanup_manager"
                                    )
                                    
                                    # Add error details
                                    error_message = f"Execution stuck in {status.value} state for over 2 hours - automatically cleaned up by process manager"
                                    repo.update_metrics(execution.execution_id, {
                                        "error_details": {"cleanup_reason": error_message, "cleanup_time": current_time.isoformat()}
                                    })
                                
                                result["executions_cleaned"].append(exec_info)
                                result["cleaned_up"] += 1
                                
                        except Exception as e:
                            result["errors"] += 1
                            print(f"Error cleaning execution {execution.id}: {e}")
            
            return result
            
        except Exception as e:
            return {"error": f"Error during cleanup: {str(e)}"}
    
    def kill_zombie_processes(self, dry_run: bool = True) -> Dict[str, Any]:
        """Eliminar procesos zombie o que no responden"""
        result = {
            "killed": 0,
            "errors": 0,
            "processes_killed": [],
            "dry_run": dry_run
        }
        
        qa_processes = self.find_qa_processes()
        
        for proc_info in qa_processes:
            try:
                # Check if process is actually running and responsive
                pid = proc_info['pid']
                
                try:
                    proc = psutil.Process(pid)
                    
                    # Check if process is zombie
                    if proc_info.get('status') == psutil.STATUS_ZOMBIE:
                        if not dry_run:
                            proc.terminate()
                            time.sleep(2)
                            if proc.is_running():
                                proc.kill()
                        
                        result["processes_killed"].append({
                            "pid": pid,
                            "name": proc_info.get('name'),
                            "reason": "zombie_process",
                            "age_minutes": proc_info.get('age_minutes', 0)
                        })
                        result["killed"] += 1
                    
                    # Check if process is very old and might be stuck
                    elif proc_info.get('age_minutes', 0) > 300:  # 5 hours
                        cpu_percent = proc_info.get('cpu_percent', 0) or 0
                        
                        # If process is old and not using CPU, it might be stuck
                        if cpu_percent < 1.0:  # Less than 1% CPU
                            if not dry_run:
                                proc.terminate()
                                time.sleep(5)
                                if proc.is_running():
                                    proc.kill()
                            
                            result["processes_killed"].append({
                                "pid": pid,
                                "name": proc_info.get('name'),
                                "reason": "old_inactive_process",
                                "age_minutes": proc_info.get('age_minutes', 0),
                                "cpu_percent": cpu_percent
                            })
                            result["killed"] += 1
                    
                except psutil.NoSuchProcess:
                    # Process already died
                    continue
                    
            except Exception as e:
                result["errors"] += 1
                print(f"Error handling process {proc_info.get('pid')}: {e}")
        
        return result
    
    async def generate_health_report(self) -> Dict[str, Any]:
        """Generar reporte completo de salud del sistema"""
        report = {
            "timestamp": datetime.now().isoformat(),
            "qa_processes": self.find_qa_processes(),
            "execution_analysis": self.analyze_stuck_executions(),
            "system_health": {},
            "recommendations": []
        }
        
        # Get system health from collector
        try:
            await self.health_collector.collect_openai_health_metrics()
            self.health_collector.collect_process_health_metrics()
            report["system_health"]["openai_status"] = "collected"
        except Exception as e:
            report["system_health"]["error"] = str(e)
        
        # Generate recommendations
        if report["execution_analysis"].get("total_stuck", 0) > 0:
            report["recommendations"].append("🧹 Consider running cleanup to remove stuck executions")
        
        if len([p for p in report["qa_processes"] if p.get("age_minutes", 0) > 120]) > 2:
            report["recommendations"].append("🔄 Multiple old processes detected - consider restarting services")
        
        return report


async def main():
    """Función principal del script de cleanup"""
    import argparse
    
    parser = argparse.ArgumentParser(description="QA Process Cleanup and Recovery Tool")
    parser.add_argument("--action", choices=["report", "cleanup", "kill-zombies", "auto"], 
                       default="report", help="Action to perform")
    parser.add_argument("--dry-run", action="store_true", default=True,
                       help="Perform dry run (default: True)")
    parser.add_argument("--force", action="store_true", 
                       help="Actually perform cleanup operations (disables dry-run)")
    parser.add_argument("--json", action="store_true", help="Output in JSON format")
    
    args = parser.parse_args()
    
    if args.force:
        args.dry_run = False
    
    manager = ProcessCleanupManager()
    
    if args.action == "report":
        print("🔍 Generating health report...")
        report = await manager.generate_health_report()
        
        if args.json:
            print(json.dumps(report, indent=2))
        else:
            print(f"📊 QA System Health Report - {report['timestamp']}")
            print("=" * 60)
            
            print(f"\n🔧 QA Processes: {len(report['qa_processes'])}")
            for proc in report['qa_processes']:
                status_emoji = "🟢" if proc.get('age_minutes', 0) < 30 else "🟡" if proc.get('age_minutes', 0) < 120 else "🔴"
                print(f"  {status_emoji} PID {proc['pid']}: {proc.get('name', 'unknown')} ({proc.get('age_minutes', 0):.1f}m)")
            
            exec_analysis = report['execution_analysis']
            if not exec_analysis.get('error'):
                print(f"\n📋 Executions:")
                print(f"  🔄 Running: {len(exec_analysis.get('running_executions', []))}")
                print(f"  ⏳ Pending: {len(exec_analysis.get('pending_executions', []))}")
                print(f"  🚫 Stuck: {exec_analysis.get('total_stuck', 0)}")
            
            if report['recommendations']:
                print("\n💡 Recommendations:")
                for rec in report['recommendations']:
                    print(f"  {rec}")
    
    elif args.action == "cleanup":
        print(f"🧹 Cleaning up stuck executions (dry_run={args.dry_run})...")
        result = manager.cleanup_stuck_executions(dry_run=args.dry_run)
        
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            if result.get('error'):
                print(f"❌ Error: {result['error']}")
            else:
                print(f"✅ Cleaned up {result['cleaned_up']} executions")
                if result['errors'] > 0:
                    print(f"⚠️ {result['errors']} errors occurred")
                
                for exec_info in result['executions_cleaned']:
                    print(f"  🧹 Execution {exec_info['id']}: {exec_info['original_status']} -> FAILED ({exec_info['age_hours']:.1f}h old)")
    
    elif args.action == "kill-zombies":
        print(f"☠️ Killing zombie processes (dry_run={args.dry_run})...")
        result = manager.kill_zombie_processes(dry_run=args.dry_run)
        
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            if result.get('error'):
                print(f"❌ Error: {result['error']}")
            else:
                print(f"✅ Killed {result['killed']} processes")
                if result['errors'] > 0:
                    print(f"⚠️ {result['errors']} errors occurred")
                
                for proc_info in result['processes_killed']:
                    print(f"  ☠️ PID {proc_info['pid']}: {proc_info['name']} - {proc_info['reason']}")
    
    elif args.action == "auto":
        print("🤖 Running automatic cleanup...")
        
        # Generate report first
        report = await manager.generate_health_report()
        
        # Auto cleanup if there are stuck executions
        if report['execution_analysis'].get('total_stuck', 0) > 0:
            print(f"🧹 Found {report['execution_analysis']['total_stuck']} stuck executions, cleaning up...")
            cleanup_result = manager.cleanup_stuck_executions(dry_run=args.dry_run)
            print(f"✅ Cleaned up {cleanup_result.get('cleaned_up', 0)} executions")
        
        # Kill zombies if any
        zombie_result = manager.kill_zombie_processes(dry_run=args.dry_run)
        if zombie_result.get('killed', 0) > 0:
            print(f"☠️ Killed {zombie_result['killed']} zombie/stuck processes")
        
        print("🤖 Automatic cleanup completed")


if __name__ == "__main__":
    asyncio.run(main())
