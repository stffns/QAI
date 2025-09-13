"""
Tests unitarios para config/settings.py

Este módulo contiene tests para la clase principal Settings que orquesta
toda la configuración del sistema QA Intelligence.

Los tests cubren:
- Integración YAML + variables de entorno
- Validación de configuración completa
- Overrides de configuración
- Casos de error y recuperación
- Métodos utilitarios
"""

import os
import tempfile
import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path
from typing import Dict, Any
import yaml

from pydantic import ValidationError

from config.settings import Settings
from config.models.core import ModelConfig, DatabaseConfig, ToolsConfig


class TestSettings:
    """Tests comprehensivos para la clase Settings"""
    
    def test_default_initialization(self):
        """Test inicialización con valores por defecto"""
        with patch.dict(os.environ, {}, clear=True):
            settings = Settings()
            
            # Verificar que todos los componentes se inicializan
            assert isinstance(settings.model, ModelConfig)
            assert isinstance(settings.database, DatabaseConfig)
            assert isinstance(settings.tools, ToolsConfig)
            
            # Verificar valores por defecto
            assert settings.model.provider == "openai"
            assert settings.database.url == "sqlite:///./data/qa_intelligence.db"
            assert settings.tools.enabled is True
    
    @patch.dict(os.environ, {
        "MODEL_PROVIDER": "azure",
        "MODEL_ID": "gpt-4",
        "MODEL_TEMPERATURE": "0.8",
        "DB_URL": "postgresql://test:test@localhost/testdb",
        "TOOLS_ENABLED": "false"
    })
    def test_environment_variables_override(self):
        """Test que las variables de entorno sobreescriben defaults"""
        settings = Settings()
        
        # Verificar overrides de modelo
        assert settings.model.provider == "azure"
        assert settings.model.id == "gpt-4"
        assert settings.model.temperature == 0.8
        
        # Verificar overrides de base de datos
        assert settings.database.url == "postgresql://test:test@localhost/testdb"
        
        # Verificar overrides de herramientas
        assert settings.tools.enabled is False
    
    def test_yaml_configuration_loading(self):
        """Test carga de configuración desde archivo YAML"""
        yaml_content = {
            "model": {
                "provider": "deepseek",
                "id": "deepseek-chat",
                "temperature": 0.3
            },
            "database": {
                "url": "sqlite:///./test.db",
                "pool_size": 10
            },
            "tools": {
                "enabled": True,
                "default_timeout": 45
            }
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(yaml_content, f)
            yaml_path = f.name
        
        try:
            # Simular la carga de YAML
            with patch.object(Settings, '_load_yaml_config', return_value=yaml_content):
                settings = Settings()
                
                # Verificar que se aplicaron los valores del YAML
                assert settings.model.provider == "deepseek"
                assert settings.model.id == "deepseek-chat"
                assert settings.model.temperature == 0.3
                assert settings.database.pool_size == 10
                assert settings.tools.default_timeout == 45
        finally:
            os.unlink(yaml_path)
    
    def test_environment_over_yaml_priority(self):
        """Test que env vars tienen prioridad sobre YAML"""
        yaml_content = {
            "model": {
                "provider": "openai",
                "temperature": 0.5
            }
        }
        
        with patch.dict(os.environ, {"MODEL_TEMPERATURE": "0.9"}):
            with patch.object(Settings, '_load_yaml_config', return_value=yaml_content):
                settings = Settings()
                
                # ENV var debe sobreescribir YAML
                assert settings.model.temperature == 0.9
                assert settings.model.provider == "openai"  # Del YAML
    
    def test_invalid_yaml_handling(self):
        """Test manejo de YAML inválido"""
        with patch('builtins.open', side_effect=FileNotFoundError):
            # Debería usar defaults cuando no hay YAML
            settings = Settings()
            assert isinstance(settings.model, ModelConfig)
    
    def test_nested_configuration_validation(self):
        """Test validación de configuración anidada"""
        # Configuración inválida debería lanzar ValidationError
        with patch.dict(os.environ, {"MODEL_TEMPERATURE": "3.0"}):  # Fuera de rango
            with pytest.raises(ValidationError, match="Temperature must be between"):
                Settings()
    
    def test_configuration_serialization(self):
        """Test serialización de configuración completa"""
        settings = Settings()
        
        # Serializar a diccionario
        config_dict = settings.model_dump()
        
        assert isinstance(config_dict, dict)
        assert "model" in config_dict
        assert "database" in config_dict
        assert "tools" in config_dict
        
        # Verificar estructura anidada
        assert "provider" in config_dict["model"]
        assert "url" in config_dict["database"]
        assert "enabled" in config_dict["tools"]
    
    def test_settings_reload(self):
        """Test recarga de configuración"""
        # Crear settings inicial
        with patch.dict(os.environ, {"MODEL_TEMPERATURE": "0.5"}):
            settings = Settings()
            assert settings.model.temperature == 0.5
        
        # Cambiar env var y crear nuevas settings
        with patch.dict(os.environ, {"MODEL_TEMPERATURE": "0.8"}):
            new_settings = Settings()
            assert new_settings.model.temperature == 0.8
    
    def test_partial_configuration_updates(self):
        """Test actualizaciones parciales de configuración"""
        settings = Settings()
        original_provider = settings.model.provider
        
        # Actualizar solo un campo
        partial_config = {"model": {"temperature": 0.9}}
        
        with patch.object(Settings, '_load_yaml_config', return_value=partial_config):
            updated_settings = Settings()
            
            # Campo actualizado debe cambiar, otros mantener valores
            assert updated_settings.model.temperature == 0.9
            assert updated_settings.model.provider == original_provider


class TestSettingsIntegration:
    """Tests de integración para Settings con otros componentes"""
    
    def test_model_config_integration(self):
        """Test integración con ModelConfig"""
        with patch.dict(os.environ, {
            "MODEL_PROVIDER": "openai",
            "MODEL_API_KEY": "test-key-123456789"
        }):
            settings = Settings()
            model_config = settings.model
            
            # Verificar que ModelConfig funciona correctamente
            provider_config = model_config.get_provider_config()
            assert provider_config["api_key"] == "test-key-123456789"
            assert "model" in provider_config
    
    def test_database_config_integration(self):
        """Test integración con DatabaseConfig"""
        with patch.dict(os.environ, {"DB_URL": "sqlite:///test.db"}):
            settings = Settings()
            db_config = settings.database
            
            # Verificar que DatabaseConfig funciona correctamente
            connection_string = db_config.get_connection_string()
            assert connection_string == "sqlite:///test.db"
    
    def test_tools_config_integration(self):
        """Test integración con ToolsConfig"""
        settings = Settings()
        tools_config = settings.tools
        
        # Verificar que ToolsConfig tiene herramientas por defecto
        assert len(tools_config.tools) > 0
        
        # Verificar métodos de ToolsConfig
        enabled_tools = tools_config.get_enabled_tools()
        assert isinstance(enabled_tools, list)
        
        web_search = tools_config.get_tool_config("web_search")
        assert web_search is not None
    
    def test_cross_component_validation(self):
        """Test validación entre componentes"""
        # Configuración que podría tener conflictos entre componentes
        yaml_content = {
            "model": {"provider": "azure"},
            "tools": {"enabled": True}
        }
        
        # Azure sin base_url debería fallar en ModelConfig
        with patch.object(Settings, '_load_yaml_config', return_value=yaml_content):
            with pytest.raises(ValidationError, match="Azure provider requires base_url"):
                Settings()


class TestSettingsUtilities:
    """Tests para métodos utilitarios de Settings"""
    
    def test_settings_methods(self):
        """Test métodos disponibles en Settings"""
        settings = Settings()
        
        # Verificar que Settings tiene los métodos esperados
        assert hasattr(settings, 'model_post_init')
        assert hasattr(settings, '_load_yaml_config')
        assert hasattr(settings, '_update_from_yaml')
        
        # Test serialización 
        config_dict = settings.model_dump()
        assert isinstance(config_dict, dict)
        assert "model" in config_dict
    
    def test_settings_validation_methods(self):
        """Test métodos de validación en Settings"""
        settings = Settings()
        
        # Test que la configuración es válida
        assert isinstance(settings.model, ModelConfig)
        assert isinstance(settings.database, DatabaseConfig)
        assert isinstance(settings.tools, ToolsConfig)
    
    def test_configuration_export(self):
        """Test exportación de configuración"""
        settings = Settings()
        
        # Exportar configuración a diferentes formatos
        dict_export = settings.model_dump()
        assert isinstance(dict_export, dict)
        
        # Verificar que se pueden excluir campos sensibles
        safe_export = settings.model_dump(exclude={"model": {"api_key"}})
        assert "api_key" not in safe_export.get("model", {})


class TestYamlConfigurationFiles:
    """Tests específicos para archivos de configuración YAML"""
    
    def test_agent_config_yaml_structure(self):
        """Test estructura del archivo agent_config.yaml real"""
        agent_config_path = Path(__file__).parent.parent.parent / "agent_config.yaml"
        
        if agent_config_path.exists():
            with open(agent_config_path, 'r') as f:
                config_data = yaml.safe_load(f)
            
            # Verificar estructura esperada
            assert isinstance(config_data, dict)
            
            # Verificar secciones principales
            if "model" in config_data:
                assert isinstance(config_data["model"], dict)
            
            if "database" in config_data:
                assert isinstance(config_data["database"], dict)
            
            if "tools" in config_data:
                assert isinstance(config_data["tools"], dict)
    
    def test_yaml_validation_against_models(self):
        """Test que YAML real es válido contra los modelos"""
        agent_config_path = Path(__file__).parent.parent.parent / "agent_config.yaml"
        
        if agent_config_path.exists():
            # Cargar YAML real y validar que Settings puede procesarlo
            try:
                with patch('config.settings.Path.exists', return_value=True):
                    with patch('builtins.open') as mock_open:
                        with open(agent_config_path, 'r') as real_file:
                            content = real_file.read()
                        mock_open.return_value.__enter__.return_value.read.return_value = content
                        
                        # Esto debería funcionar sin errores
                        settings = Settings()
                        assert isinstance(settings, Settings)
            except Exception as e:
                pytest.fail(f"YAML real no es válido: {e}")


class TestConfigurationEdgeCases:
    """Tests para casos límite y situaciones especiales"""
    
    def test_empty_environment(self):
        """Test comportamiento con entorno completamente vacío"""
        # Limpiar todas las variables de entorno relacionadas
        env_vars_to_clear = [
            key for key in os.environ.keys() 
            if key.startswith(('MODEL_', 'DB_', 'TOOLS_', 'LOG_', 'OPENAI_'))
        ]
        
        with patch.dict(os.environ, {}, clear=True):
            settings = Settings()
            
            # Debería usar valores por defecto
            assert settings.model.provider == "openai"
            assert settings.database.url.startswith("sqlite://")
            assert settings.tools.enabled is True
    
    def test_malformed_environment_values(self):
        """Test manejo de valores malformados en env vars"""
        with patch.dict(os.environ, {
            "MODEL_TEMPERATURE": "invalid_float",
            "DB_POOL_SIZE": "not_an_integer",
            "TOOLS_ENABLED": "maybe"
        }):
            # Debería manejar valores inválidos apropiadamente
            with pytest.raises(ValidationError):
                Settings()
    
    def test_missing_required_fields(self):
        """Test comportamiento con campos requeridos faltantes"""
        # Para Azure que requiere base_url
        with patch.dict(os.environ, {
            "MODEL_PROVIDER": "azure",
            "MODEL_API_KEY": "test-key-123456789"
            # Falta MODEL_BASE_URL
        }):
            with pytest.raises(ValidationError, match="Azure provider requires base_url"):
                Settings()
    
    def test_configuration_with_all_fields(self):
        """Test configuración completa con todos los campos posibles"""
        complete_env = {
            "MODEL_PROVIDER": "openai",
            "MODEL_ID": "gpt-4",
            "MODEL_API_KEY": "test-key-123456789",
            "MODEL_TEMPERATURE": "0.7",
            "MODEL_MAX_TOKENS": "2048",
            "MODEL_TIMEOUT": "30",
            "MODEL_TOP_P": "1.0",
            "OPENAI_ORGANIZATION": "org-123",
            "OPENAI_PROJECT": "proj-456",
            "DB_URL": "sqlite:///test.db",
            "DB_POOL_SIZE": "20",
            "DB_MAX_OVERFLOW": "30",
            "DB_ECHO": "false",
            "TOOLS_ENABLED": "true",
            "TOOLS_TIMEOUT": "30",
            "TOOLS_MAX_CONCURRENT": "5",
            "TOOLS_SAFETY_MODE": "true"
        }
        
        with patch.dict(os.environ, complete_env):
            settings = Settings()
            
            # Verificar que todos los campos se cargaron correctamente
            assert settings.model.provider == "openai"
            assert settings.model.id == "gpt-4"
            assert settings.model.api_key == "test-key-123456789"
            assert settings.model.temperature == 0.7
            assert settings.model.max_tokens == 2048
            assert settings.model.organization == "org-123"
            assert settings.model.project == "proj-456"
            
            assert settings.database.url == "sqlite:///test.db"
            assert settings.database.pool_size == 20
            assert settings.database.echo is False
            
            assert settings.tools.enabled is True
            assert settings.tools.default_timeout == 30
            assert settings.tools.max_concurrent_tools == 5


# Fixtures para tests
@pytest.fixture
def sample_yaml_config():
    """Fixture con configuración YAML de ejemplo"""
    return {
        "model": {
            "provider": "openai",
            "id": "gpt-4",
            "temperature": 0.7
        },
        "database": {
            "url": "sqlite:///test.db"
        },
        "tools": {
            "enabled": True,
            "tools": [
                {"name": "web_search", "enabled": True},
                {"name": "calculator", "enabled": True}
            ]
        }
    }


@pytest.fixture
def temp_yaml_file(sample_yaml_config):
    """Fixture que crea archivo YAML temporal"""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        yaml.dump(sample_yaml_config, f)
        temp_path = f.name
    
    yield temp_path
    
    # Cleanup
    os.unlink(temp_path)


@pytest.fixture
def clean_environment():
    """Fixture que limpia variables de entorno para tests"""
    env_vars_to_clear = [
        key for key in os.environ.keys() 
        if key.startswith(('MODEL_', 'DB_', 'TOOLS_', 'LOG_', 'OPENAI_'))
    ]
    
    original_values = {}
    for var in env_vars_to_clear:
        if var in os.environ:
            original_values[var] = os.environ[var]
            del os.environ[var]
    
    yield
    
    # Restaurar valores originales
    for var, value in original_values.items():
        os.environ[var] = value
