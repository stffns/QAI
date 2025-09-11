#!/usr/bin/env python3
"""
OpenAI Health Monitor

Monitor de salud de los servicios de OpenAI para detectar intermitencias
y proporcionar información sobre el estado del servicio.
"""

import asyncio
import time
import json
import httpx
import os
import sys
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from pathlib import Path
import logging
from dataclasses import dataclass, asdict
from enum import Enum

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ServiceStatus(Enum):
    """Status levels for OpenAI services"""
    HEALTHY = "healthy"
    DEGRADED = "degraded" 
    OUTAGE = "outage"
    UNKNOWN = "unknown"


@dataclass
class HealthCheck:
    """Individual health check result"""
    timestamp: str
    service: str
    status: ServiceStatus
    response_time: float
    error: Optional[str] = None
    details: Optional[Dict[str, Any]] = None


@dataclass
class ServiceHealth:
    """Overall service health summary"""
    service_name: str
    status: ServiceStatus
    last_checked: str
    uptime_percentage: float
    avg_response_time: float
    recent_checks: List[HealthCheck]
    incidents: List[Dict[str, Any]]


class OpenAIHealthMonitor:
    """
    Monitor OpenAI API health and detect intermittent issues
    """
    
    def __init__(self, data_dir: str = "data/monitoring"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        self.health_file = self.data_dir / "openai_health.json"
        self.incidents_file = self.data_dir / "openai_incidents.json"
        
        # Monitoring configuration
        self.check_interval = 30  # seconds
        self.max_response_time = 10.0  # seconds
        self.failure_threshold = 3  # consecutive failures to declare degraded
        self.recovery_threshold = 2  # consecutive successes to declare healthy
        
        # Health tracking
        self.health_history: List[HealthCheck] = []
        self.current_status = ServiceStatus.UNKNOWN
        self.consecutive_failures = 0
        self.consecutive_successes = 0
        self.incidents: List[Dict[str, Any]] = []
        
        # Load existing data
        self._load_health_data()
    
    def _load_health_data(self):
        """Load existing health data from files"""
        try:
            if self.health_file.exists():
                with open(self.health_file, 'r') as f:
                    data = json.load(f)
                    # Convert loaded data back to HealthCheck objects
                    history_data = data.get('history', [])
                    self.health_history = []
                    for check_data in history_data:
                        # Convert status string back to enum
                        if 'status' in check_data and isinstance(check_data['status'], str):
                            check_data['status'] = ServiceStatus(check_data['status'])
                        self.health_history.append(HealthCheck(**check_data))
                    
                    self.current_status = ServiceStatus(data.get('status', 'unknown'))
            
            if self.incidents_file.exists():
                with open(self.incidents_file, 'r') as f:
                    self.incidents = json.load(f)
                    
        except Exception as e:
            logger.error(f"Error loading health data: {e}")
    
    def _save_health_data(self):
        """Save health data to files"""
        try:
            # Keep only last 24 hours of data
            cutoff = datetime.now() - timedelta(hours=24)
            cutoff_str = cutoff.isoformat()
            
            recent_history = [
                check for check in self.health_history 
                if check.timestamp >= cutoff_str
            ]
            
            # Convert ServiceStatus enum to string for JSON serialization
            serializable_history = []
            for check in recent_history:
                check_dict = asdict(check)
                check_dict['status'] = check.status.value  # Convert enum to string
                serializable_history.append(check_dict)
            
            health_data = {
                'status': self.current_status.value,
                'last_updated': datetime.now().isoformat(),
                'history': serializable_history
            }
            
            with open(self.health_file, 'w') as f:
                json.dump(health_data, f, indent=2)
            
            with open(self.incidents_file, 'w') as f:
                json.dump(self.incidents, f, indent=2)
                
        except Exception as e:
            logger.error(f"Error saving health data: {e}")
    
    async def check_openai_api(self) -> HealthCheck:
        """Perform a health check against OpenAI API"""
        start_time = time.time()
        timestamp = datetime.now().isoformat()
        
        try:
            # Get OpenAI API key from environment
            api_key = os.getenv('OPENAI_API_KEY')
            
            if not api_key:
                # Try to load from config as fallback
                try:
                    sys.path.append(os.path.join(os.path.dirname(__file__), "..", ".."))
                    import yaml
                    config_path = os.path.join(os.path.dirname(__file__), "..", "..", "agent_config.yaml")
                    if os.path.exists(config_path):
                        with open(config_path, 'r') as f:
                            config = yaml.safe_load(f)
                            api_key = config.get('model', {}).get('api_key')
                except Exception as e:
                    logger.debug(f"Could not load config file: {e}")
                    pass
            
            if not api_key:
                return HealthCheck(
                    timestamp=timestamp,
                    service="openai_api",
                    status=ServiceStatus.UNKNOWN,
                    response_time=0.0,
                    error="No API key configured"
                )
            
            # Test API with a minimal request
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": "gpt-5-mini",
                        "messages": [{"role": "user", "content": "test"}],
                        "max_tokens": 1
                    }
                )
                
                response_time = time.time() - start_time
                
                if response.status_code == 200:
                    status = ServiceStatus.HEALTHY
                    if response_time > self.max_response_time:
                        status = ServiceStatus.DEGRADED
                        
                    return HealthCheck(
                        timestamp=timestamp,
                        service="openai_api",
                        status=status,
                        response_time=response_time,
                        details={"status_code": response.status_code}
                    )
                else:
                    return HealthCheck(
                        timestamp=timestamp,
                        service="openai_api", 
                        status=ServiceStatus.DEGRADED,
                        response_time=response_time,
                        error=f"HTTP {response.status_code}: {response.text[:200]}",
                        details={"status_code": response.status_code}
                    )
                    
        except asyncio.TimeoutError:
            return HealthCheck(
                timestamp=timestamp,
                service="openai_api",
                status=ServiceStatus.OUTAGE,
                response_time=time.time() - start_time,
                error="Request timeout"
            )
        except Exception as e:
            return HealthCheck(
                timestamp=timestamp,
                service="openai_api",
                status=ServiceStatus.OUTAGE,
                response_time=time.time() - start_time,
                error=str(e)
            )
    
    def _update_status(self, check: HealthCheck):
        """Update overall service status based on health check"""
        previous_status = self.current_status
        
        if check.status == ServiceStatus.HEALTHY:
            self.consecutive_failures = 0
            self.consecutive_successes += 1
            
            if self.consecutive_successes >= self.recovery_threshold:
                self.current_status = ServiceStatus.HEALTHY
        else:
            self.consecutive_successes = 0
            self.consecutive_failures += 1
            
            if self.consecutive_failures >= self.failure_threshold:
                if check.status == ServiceStatus.OUTAGE:
                    self.current_status = ServiceStatus.OUTAGE
                else:
                    self.current_status = ServiceStatus.DEGRADED
        
        # Log status changes and create incidents
        if previous_status != self.current_status:
            incident = {
                "timestamp": check.timestamp,
                "type": "status_change",
                "from_status": previous_status.value,
                "to_status": self.current_status.value,
                "trigger_check": asdict(check)
            }
            self.incidents.append(incident)
            
            logger.warning(f"OpenAI status changed: {previous_status.value} → {self.current_status.value}")
    
    def get_health_summary(self) -> ServiceHealth:
        """Get current health summary"""
        # Calculate uptime percentage (last 24 hours)
        cutoff = datetime.now() - timedelta(hours=24)
        recent_checks = [
            check for check in self.health_history
            if datetime.fromisoformat(check.timestamp) >= cutoff
        ]
        
        if recent_checks:
            healthy_checks = len([
                check for check in recent_checks 
                if check.status == ServiceStatus.HEALTHY
            ])
            uptime_percentage = (healthy_checks / len(recent_checks)) * 100
            
            response_times = [
                check.response_time for check in recent_checks
                if check.response_time > 0
            ]
            avg_response_time = sum(response_times) / len(response_times) if response_times else 0
        else:
            uptime_percentage = 0
            avg_response_time = 0
        
        return ServiceHealth(
            service_name="OpenAI API",
            status=self.current_status,
            last_checked=self.health_history[-1].timestamp if self.health_history else "Never",
            uptime_percentage=uptime_percentage,
            avg_response_time=avg_response_time,
            recent_checks=recent_checks[-10:],  # Last 10 checks
            incidents=self.incidents[-5:]  # Last 5 incidents
        )
    
    def get_status_message(self) -> str:
        """Get user-friendly status message"""
        summary = self.get_health_summary()
        
        status_messages = {
            ServiceStatus.HEALTHY: "🟢 OpenAI services are operating normally",
            ServiceStatus.DEGRADED: "🟡 OpenAI services may be experiencing intermittent issues", 
            ServiceStatus.OUTAGE: "🔴 OpenAI services are currently unavailable",
            ServiceStatus.UNKNOWN: "⚪ OpenAI service status is unknown"
        }
        
        base_message = status_messages.get(self.current_status, "❓ Unknown status")
        
        if summary.uptime_percentage < 100:
            base_message += f" (Uptime: {summary.uptime_percentage:.1f}%)"
        
        if summary.avg_response_time > self.max_response_time:
            base_message += f" (Slow responses: {summary.avg_response_time:.1f}s avg)"
        
        return base_message
    
    async def run_continuous_monitoring(self):
        """Run continuous monitoring loop"""
        logger.info("Starting OpenAI health monitoring...")
        
        while True:
            try:
                # Perform health check
                check = await self.check_openai_api()
                self.health_history.append(check)
                
                # Update status
                self._update_status(check)
                
                # Save data
                self._save_health_data()
                
                # Log status
                status_emoji = {
                    ServiceStatus.HEALTHY: "🟢",
                    ServiceStatus.DEGRADED: "🟡", 
                    ServiceStatus.OUTAGE: "🔴",
                    ServiceStatus.UNKNOWN: "⚪"
                }
                
                emoji = status_emoji.get(check.status, "❓")
                logger.info(f"{emoji} OpenAI Health: {check.status.value} ({check.response_time:.2f}s)")
                
                if check.error:
                    logger.warning(f"Health check error: {check.error}")
                
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
            
            # Wait for next check
            await asyncio.sleep(self.check_interval)
    
    async def run_single_check(self) -> Dict[str, Any]:
        """Run a single health check and return results"""
        check = await self.check_openai_api()
        self.health_history.append(check)
        self._update_status(check)
        self._save_health_data()
        
        summary = self.get_health_summary()
        
        # Convert enum values to strings for JSON serialization
        check_dict = asdict(check)
        check_dict['status'] = check.status.value
        
        summary_dict = asdict(summary)
        summary_dict['status'] = summary.status.value
        
        # Convert status in recent_checks
        for recent_check in summary_dict.get('recent_checks', []):
            if 'status' in recent_check and hasattr(recent_check['status'], 'value'):
                recent_check['status'] = recent_check['status'].value
        
        return {
            "status": self.current_status.value,
            "message": self.get_status_message(),
            "last_check": check_dict,
            "summary": summary_dict
        }


async def main():
    """Main function for standalone monitoring"""
    import argparse
    
    parser = argparse.ArgumentParser(description="OpenAI Health Monitor")
    parser.add_argument("--continuous", action="store_true", help="Run continuous monitoring")
    parser.add_argument("--check", action="store_true", help="Run single health check")
    parser.add_argument("--status", action="store_true", help="Show current status")
    
    args = parser.parse_args()
    
    monitor = OpenAIHealthMonitor()
    
    if args.continuous:
        await monitor.run_continuous_monitoring()
    elif args.check:
        result = await monitor.run_single_check()
        print(json.dumps(result, indent=2))
    elif args.status:
        summary = monitor.get_health_summary()
        print(f"Status: {monitor.get_status_message()}")
        print(f"Uptime: {summary.uptime_percentage:.1f}%")
        print(f"Avg Response Time: {summary.avg_response_time:.2f}s")
        if summary.incidents:
            print(f"Recent incidents: {len(summary.incidents)}")
    else:
        result = await monitor.run_single_check()
        print(result["message"])


if __name__ == "__main__":
    asyncio.run(main())
