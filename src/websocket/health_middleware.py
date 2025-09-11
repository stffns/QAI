#!/usr/bin/env python3
"""
WebSocket Health Middleware

Middleware para agregar información de salud de OpenAI a los mensajes del WebSocket,
especialmente cuando hay errores que podrían estar relacionados con problemas del servicio.
"""

import asyncio
import logging
from typing import Dict, Any, Optional
from datetime import datetime

# Import our health check script
try:
    from scripts.check_openai_health import check_openai_health, get_status_message_for_user
except ImportError:
    import sys
    import os
    sys.path.append(os.path.join(os.path.dirname(__file__), "..", ".."))
    from scripts.check_openai_health import check_openai_health, get_status_message_for_user

logger = logging.getLogger(__name__)


class HealthAwareErrorHandler:
    """
    Handler de errores que incluye información de salud de OpenAI
    cuando es relevante para el problema del usuario.
    """
    
    def __init__(self):
        self._last_health_check = None
        self._cached_health_info = None
        self._cache_duration = 30  # Cache health info for 30 seconds
        
    async def _get_health_info(self, force_refresh: bool = False) -> Optional[Dict[str, Any]]:
        """Obtener información de salud, usando cache cuando sea apropiado"""
        try:
            now = datetime.now()
            
            # Use cached info if available and recent (unless force refresh)
            if (not force_refresh and 
                self._cached_health_info and 
                self._last_health_check and
                (now - self._last_health_check).total_seconds() < self._cache_duration):
                return self._cached_health_info
            
            # Perform health check
            health_info = await check_openai_health()
            self._cached_health_info = health_info
            self._last_health_check = now
            
            return health_info
            
        except Exception as e:
            logger.warning(f"Could not check OpenAI health: {e}")
            return None
    
    async def enhance_error_with_health_info(
        self, 
        error_message: str, 
        error_details: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Mejorar un mensaje de error con información de salud de OpenAI si es relevante
        """
        
        # Determine if this error might be related to OpenAI issues
        error_keywords = [
            'timeout', 'connection', 'api', 'openai', 'request failed',
            'service unavailable', 'internal server error', 'rate limit',
            'authentication', 'quota', 'model', 'completion'
        ]
        
        error_text_lower = error_message.lower()
        might_be_openai_related = any(keyword in error_text_lower for keyword in error_keywords)
        
        enhanced_error = {
            "original_error": error_message,
            "timestamp": datetime.now().isoformat(),
            "error_details": error_details or {},
            "openai_health_checked": False
        }
        
        # Only check OpenAI health if error might be related
        if might_be_openai_related:
            health_info = await self._get_health_info()
            
            if health_info:
                enhanced_error.update({
                    "openai_health_checked": True,
                    "openai_status": health_info.get('status', 'unknown'),
                    "openai_message": health_info.get('message', ''),
                    "service_suggestion": health_info.get('suggestion'),
                    "can_make_requests": health_info.get('can_make_requests', True)
                })
                
                # Add contextual information based on status
                status = health_info.get('status', 'unknown')
                
                if status == 'outage':
                    enhanced_error["likely_cause"] = "OpenAI service outage"
                    enhanced_error["user_message"] = (
                        "🔴 This error appears to be related to OpenAI service issues. "
                        f"{health_info.get('message', '')} "
                        "Please try again in a few minutes."
                    )
                elif status == 'degraded':
                    enhanced_error["likely_cause"] = "OpenAI service degradation"
                    enhanced_error["user_message"] = (
                        "🟡 This error may be related to intermittent OpenAI service issues. "
                        f"{health_info.get('message', '')} "
                        "Try refreshing your request."
                    )
                elif status == 'unknown' and not health_info.get('can_make_requests', True):
                    enhanced_error["likely_cause"] = "OpenAI configuration issue"
                    enhanced_error["user_message"] = (
                        "⚪ Cannot verify OpenAI service status. "
                        "This may be a configuration issue. "
                        f"{health_info.get('suggestion', '')}"
                    )
                else:
                    # OpenAI appears healthy, so error is likely something else
                    enhanced_error["likely_cause"] = "Non-OpenAI related issue"
                    enhanced_error["user_message"] = (
                        "OpenAI services appear to be working normally, "
                        "so this error is likely due to another cause."
                    )
        else:
            # Error doesn't appear to be OpenAI related
            enhanced_error["user_message"] = "This appears to be a technical issue not related to OpenAI services."
        
        return enhanced_error
    
    async def create_service_status_message(self) -> Dict[str, Any]:
        """
        Crear un mensaje de estado de servicio para responder a consultas sobre el estado
        """
        health_info = await self._get_health_info(force_refresh=True)
        
        if not health_info:
            return {
                "type": "service_status",
                "timestamp": datetime.now().isoformat(),
                "status": "unknown",
                "message": "⚪ Unable to check OpenAI service status at this time",
                "user_message": "Cannot determine the current status of OpenAI services."
            }
        
        user_message = get_status_message_for_user(health_info)
        
        return {
            "type": "service_status",
            "timestamp": datetime.now().isoformat(),
            "status": health_info.get('status', 'unknown'),
            "message": health_info.get('message', ''),
            "user_message": user_message,
            "can_make_requests": health_info.get('can_make_requests', True),
            "response_time": health_info.get('response_time', 0),
            "last_checked": health_info.get('timestamp'),
            "suggestion": health_info.get('suggestion')
        }


# Global instance for use throughout the application
health_aware_error_handler = HealthAwareErrorHandler()


async def enhance_websocket_error(error_message: str, error_details: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Function helper para mejorar errores del WebSocket con información de salud
    """
    return await health_aware_error_handler.enhance_error_with_health_info(error_message, error_details)


async def get_service_status_for_websocket() -> Dict[str, Any]:
    """
    Function helper para obtener estado de servicio para WebSocket
    """
    return await health_aware_error_handler.create_service_status_message()


def should_check_openai_health(error_message: str) -> bool:
    """
    Determinar si un error amerita verificar la salud de OpenAI
    """
    error_keywords = [
        'timeout', 'connection', 'api', 'openai', 'request failed',
        'service unavailable', 'internal server error', 'rate limit',
        'authentication', 'quota', 'model', 'completion', 'failed to process'
    ]
    
    error_text_lower = error_message.lower()
    return any(keyword in error_text_lower for keyword in error_keywords)


if __name__ == "__main__":
    async def test_health_middleware():
        """Test the health middleware functionality"""
        handler = HealthAwareErrorHandler()
        
        # Test with OpenAI-related error
        print("Testing OpenAI-related error:")
        enhanced = await handler.enhance_error_with_health_info(
            "OpenAI API request failed with timeout"
        )
        print(f"Enhanced error: {enhanced}")
        
        print("\nTesting service status:")
        status = await handler.create_service_status_message()
        print(f"Service status: {status}")
    
    asyncio.run(test_health_middleware())
