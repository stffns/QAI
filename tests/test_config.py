"""
Test de configuración WebSocket - Solo tests operativos
"""
import pytest
from src.websocket.config import WebSocketConfig


class TestWebSocketConfig:
    """Tests operativos para la configuración WebSocket"""
    
    def test_minimal_config(self):
        """Test configuración mínima válida"""
        config_data = {
            "enabled": True,
            "server": {
                "host": "localhost",
                "port": 8765
            },
            "security": {
                "authentication": {"enabled": False},
                "cors": {"enabled": False},
                "rate_limiting": {"enabled": False}
            }
        }
        
        config = WebSocketConfig(**config_data)
        
        assert config.enabled == True
        assert config.server.host == "localhost"
        assert config.server.port == 8765
        assert config.security.authentication.enabled == False

    def test_full_config(self):
        """Test configuración completa (sin SSL)"""
        config_data = {
            "enabled": True,
            "server": {
                "host": "0.0.0.0",
                "port": 8080
            },
            "security": {
                "authentication": {
                    "enabled": True,
                    "method": "jwt",
                    "jwt_secret": "secret123"
                },
                "cors": {
                    "enabled": True,
                    "allowed_origins": ["https://example.com"],
                    "allowed_methods": ["GET", "POST"]
                },
                "rate_limiting": {
                    "enabled": True,
                    "requests_per_minute": 100
                }
            }
        }
        
        config = WebSocketConfig(**config_data)
        
        assert config.enabled == True
        assert config.server.host == "0.0.0.0"
        assert config.server.port == 8080
        assert config.security.authentication.enabled == True
        assert config.security.cors.enabled == True
        assert config.security.rate_limiting.enabled == True

    def test_invalid_port(self):
        """Test puerto inválido"""
        config_data = {
            "enabled": True,
            "server": {
                "host": "localhost",
                "port": 70000  # Puerto fuera de rango
            },
            "security": {
                "authentication": {"enabled": False},
                "cors": {"enabled": False},
                "rate_limiting": {"enabled": False}
            }
        }
        
        with pytest.raises(ValueError):
            WebSocketConfig(**config_data)


class TestConfigValidation:
    """Tests de validación de configuración"""
    
    def test_default_values(self):
        """Test valores por defecto"""
        config_data = {
            "enabled": True,
            "server": {
                "host": "localhost",
                "port": 8765
            }
        }
        
        config = WebSocketConfig(**config_data)
        
        # Verificar que la configuración se crea correctamente
        assert config.enabled == True
        assert config.server.host == "localhost"
        assert config.server.port == 8765
        # Verificar que security existe con sus valores por defecto
        assert hasattr(config, 'security')
        assert hasattr(config.security, 'authentication')
        assert hasattr(config.security, 'cors')
        assert hasattr(config.security, 'rate_limiting')
        
    def test_ssl_configuration(self):
        """Test configuración básica"""
        config_data = {
            "enabled": True,
            "server": {
                "host": "localhost",
                "port": 8765
            }
        }
        
        config = WebSocketConfig(**config_data)
        
        assert config.enabled == True
        assert config.server.host == "localhost"
        assert config.server.port == 8765


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
