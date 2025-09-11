#!/usr/bin/env python3
"""
WebSocket Health Integration

Integra el monitor de salud de OpenAI con el servidor WebSocket para
proporcionar información de estado en tiempo real a los clientes.
"""

import asyncio
import json
import time
from typing import Dict, Any, Optional
from datetime import datetime, timedelta

try:
    from src.monitoring.openai_health_monitor import OpenAIHealthMonitor, ServiceStatus
except ImportError:
    import sys
    import os
    sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
    from monitoring.openai_health_monitor import OpenAIHealthMonitor, ServiceStatus


class WebSocketHealthIntegration:
    """
    Integración del monitor de salud con WebSocket para notificaciones en tiempo real
    """
    
    def __init__(self):
        self.monitor = OpenAIHealthMonitor()
        self.last_status = ServiceStatus.UNKNOWN
        self.last_notification = None
        self.notification_cooldown = 300  # 5 minutos entre notificaciones del mismo tipo
        
    async def get_health_status(self) -> Dict[str, Any]:
        """Obtener estado actual de salud para el cliente"""
        try:
            summary = self.monitor.get_health_summary()
            
            return {
                "type": "health_status",
                "timestamp": datetime.now().isoformat(),
                "openai_status": {
                    "status": summary.status.value,
                    "message": self.monitor.get_status_message(),
                    "uptime_percentage": summary.uptime_percentage,
                    "avg_response_time": summary.avg_response_time,
                    "last_checked": summary.last_checked
                },
                "health_details": {
                    "service_operational": summary.status == ServiceStatus.HEALTHY,
                    "intermittent_issues": summary.status == ServiceStatus.DEGRADED,
                    "service_down": summary.status == ServiceStatus.OUTAGE,
                    "recent_incidents": len(summary.incidents)
                }
            }
        except Exception as e:
            return {
                "type": "health_status",
                "timestamp": datetime.now().isoformat(),
                "error": f"Could not retrieve health status: {str(e)}",
                "openai_status": {
                    "status": "unknown",
                    "message": "⚪ Unable to determine OpenAI service status"
                }
            }
    
    async def check_for_status_changes(self) -> Optional[Dict[str, Any]]:
        """
        Verificar cambios de estado y devolver notificación si es necesario
        """
        try:
            # Ejecutar verificación de salud
            await self.monitor.run_single_check()
            current_status = self.monitor.current_status
            
            # Verificar si ha cambiado el estado
            if current_status != self.last_status:
                # Verificar cooldown para evitar spam
                now = time.time()
                if (self.last_notification is None or 
                    now - self.last_notification > self.notification_cooldown):
                    
                    self.last_notification = now
                    self.last_status = current_status
                    
                    # Crear notificación de cambio de estado
                    summary = self.monitor.get_health_summary()
                    
                    notification = {
                        "type": "service_alert",
                        "timestamp": datetime.now().isoformat(),
                        "alert_type": "status_change",
                        "message": self._get_status_change_message(current_status),
                        "openai_status": {
                            "status": current_status.value,
                            "message": self.monitor.get_status_message(),
                            "uptime_percentage": summary.uptime_percentage
                        },
                        "action_required": current_status in [ServiceStatus.DEGRADED, ServiceStatus.OUTAGE]
                    }
                    
                    return notification
                else:
                    # Actualizar estado sin notificación (cooldown activo)
                    self.last_status = current_status
            
            return None
            
        except Exception as e:
            return {
                "type": "service_alert", 
                "timestamp": datetime.now().isoformat(),
                "alert_type": "monitoring_error",
                "message": f"⚠️ Error monitoring OpenAI services: {str(e)}",
                "action_required": False
            }
    
    def _get_status_change_message(self, status: ServiceStatus) -> str:
        """Generar mensaje personalizado para cambio de estado"""
        messages = {
            ServiceStatus.HEALTHY: "✅ OpenAI services have recovered and are operating normally",
            ServiceStatus.DEGRADED: "⚠️ OpenAI services are experiencing intermittent issues. Some requests may fail or be slower than usual.",
            ServiceStatus.OUTAGE: "🚨 OpenAI services are currently unavailable. Please try again later.",
            ServiceStatus.UNKNOWN: "❓ Unable to determine OpenAI service status"
        }
        return messages.get(status, "OpenAI service status has changed")
    
    async def get_health_tips(self, status: ServiceStatus) -> Dict[str, Any]:
        """Proporcionar consejos basados en el estado del servicio"""
        tips = {
            ServiceStatus.HEALTHY: [
                "All systems operational - no action needed",
                "Response times are normal"
            ],
            ServiceStatus.DEGRADED: [
                "Try refreshing your request if it fails",
                "Responses may be slower than usual",
                "Consider retrying failed requests after a few minutes"
            ],
            ServiceStatus.OUTAGE: [
                "OpenAI services are temporarily unavailable",
                "Please wait a few minutes before trying again", 
                "Check https://status.openai.com for official updates"
            ],
            ServiceStatus.UNKNOWN: [
                "Unable to verify service status",
                "If you experience issues, they may be service-related"
            ]
        }
        
        return {
            "type": "health_tips",
            "timestamp": datetime.now().isoformat(),
            "status": status.value,
            "tips": tips.get(status, []),
            "external_status_page": "https://status.openai.com"
        }


# Función helper para integrar en el servidor WebSocket existente
async def add_health_monitoring_to_message(message: Dict[str, Any]) -> Dict[str, Any]:
    """
    Agregar información de salud a los mensajes del WebSocket si es apropiado
    """
    try:
        health_integration = WebSocketHealthIntegration()
        
        # Verificar si hay cambios de estado
        status_alert = await health_integration.check_for_status_changes()
        
        # Si es un mensaje de error o hay problemas de estado, agregar info de salud
        if (message.get("type") == "error" or 
            status_alert is not None or
            "error" in message.get("content", "").lower()):
            
            health_status = await health_integration.get_health_status()
            
            # Agregar información de salud al mensaje
            message["health_context"] = {
                "openai_status": health_status["openai_status"],
                "possible_service_issue": health_status["openai_status"]["status"] != "healthy",
                "status_page": "https://status.openai.com"
            }
            
            # Si hay una alerta de estado, incluirla
            if status_alert:
                message["service_alert"] = status_alert
        
        return message
        
    except Exception as e:
        # No fallar el mensaje original si hay problemas con el monitor
        message["health_monitoring_error"] = f"Could not check service health: {str(e)}"
        return message


# Función para obtener estado de salud bajo demanda
async def get_current_health_status() -> Dict[str, Any]:
    """Obtener estado de salud actual para responder a consultas explícitas"""
    try:
        health_integration = WebSocketHealthIntegration()
        return await health_integration.get_health_status()
    except Exception as e:
        return {
            "type": "health_status",
            "timestamp": datetime.now().isoformat(),
            "error": f"Health monitoring unavailable: {str(e)}",
            "openai_status": {
                "status": "unknown",
                "message": "⚪ Unable to determine service status"
            }
        }


if __name__ == "__main__":
    async def test_integration():
        """Test the health integration"""
        integration = WebSocketHealthIntegration()
        
        print("Testing health status...")
        status = await integration.get_health_status()
        print(json.dumps(status, indent=2))
        
        print("\nTesting status change detection...")
        change = await integration.check_for_status_changes()
        if change:
            print(json.dumps(change, indent=2))
        else:
            print("No status changes detected")
    
    asyncio.run(test_integration())
