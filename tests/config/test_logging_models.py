"""
Tests unitarios para config/models/logging.py

Este módulo contiene tests para la configuración avanzada de logging
basada en la estructura real de LoggingConfig.
"""

import os
import pytest
from unittest.mock import patch
from pydantic import ValidationError

from config.models.logging import LoggingConfig, LogLevel


class TestLogLevel:
    """Tests para la clase LogLevel"""
    
    def test_standard_log_levels(self):
        """Test niveles de log estándar"""
        assert LogLevel.DEBUG == "DEBUG"
        assert LogLevel.INFO == "INFO"
        assert LogLevel.WARNING == "WARNING"
        assert LogLevel.ERROR == "ERROR"
        assert LogLevel.CRITICAL == "CRITICAL"
    
    def test_loguru_specific_levels(self):
        """Test niveles específicos de Loguru"""
        assert LogLevel.TRACE == "TRACE"
        assert LogLevel.SUCCESS == "SUCCESS"
    
    def test_all_levels_method(self):
        """Test método all_levels"""
        available_levels = LogLevel.all_levels()
        expected_levels = {"TRACE", "DEBUG", "INFO", "SUCCESS", "WARNING", "ERROR", "CRITICAL"}
        assert available_levels == expected_levels


class TestLoggingConfig:
    """Tests para LoggingConfig basados en la estructura real"""
    
    def test_default_values(self):
        """Test valores por defecto"""
        with patch.dict(os.environ, {}, clear=True):
            config = LoggingConfig()
            
            assert config.level == "INFO"
            assert config.enable_file_logging is True
            assert config.enable_console_logging is True
            assert config.enable_json_logs is False
            assert config.log_file == "logs/qa_intelligence.log"
            assert config.max_file_size == "10 MB"
            assert config.backup_count == 5
    
    @patch.dict(os.environ, {
        "LOG_LEVEL": "DEBUG",
        "LOG_ENABLE_FILE": "false",
        "LOG_ENABLE_CONSOLE": "true",
        "LOG_FILE": "./custom/logs/app.log",
        "LOG_MAX_SIZE": "50 MB",
        "LOG_BACKUP_COUNT": "10"
    })
    def test_environment_variables_loading(self):
        """Test carga desde variables de entorno"""
        config = LoggingConfig()
        
        assert config.level == "DEBUG"
        assert config.enable_file_logging is False
        assert config.enable_console_logging is True
        assert config.log_file == "./custom/logs/app.log"
        assert config.max_file_size == "50 MB"
        assert config.backup_count == 10
    
    def test_programmatic_initialization(self):
        """Test inicialización programática"""
        config = LoggingConfig(
            level="DEBUG",
            enable_file_logging=True,
            enable_console_logging=True,
            log_file="./logs/test.log",
            max_file_size="20 MB",
            backup_count=7
        )
        
        assert config.level == "DEBUG"
        assert config.enable_file_logging is True
        assert config.enable_console_logging is True
        assert config.log_file == "./logs/test.log"
        assert config.max_file_size == "20 MB"
        assert config.backup_count == 7
    
    def test_backup_count_validation(self):
        """Test validación de cantidad de backups"""
        # Valores válidos
        config = LoggingConfig(backup_count=0)
        assert config.backup_count == 0
        
        config = LoggingConfig(backup_count=10)
        assert config.backup_count == 10
        
        # Valores inválidos
        with pytest.raises(ValidationError):
            LoggingConfig(backup_count=-1)
        
        with pytest.raises(ValidationError):
            LoggingConfig(backup_count=101)
    
    def test_json_format_configuration(self):
        """Test configuración de formato JSON"""
        config = LoggingConfig()
        
        assert isinstance(config.json_format, dict)
        expected_keys = {
            "timestamp", "level", "logger", "function", 
            "line", "message", "process", "thread"
        }
        assert set(config.json_format.keys()) == expected_keys
    
    def test_custom_format_configuration(self):
        """Test configuración de formato personalizado"""
        custom_format = "{time} | {level} | {message}"
        config = LoggingConfig(format=custom_format)
        assert config.format == custom_format
    
    def test_json_logging_configuration(self):
        """Test configuración de logging JSON"""
        config = LoggingConfig(
            enable_json_logs=True,
            json_log_file="./logs/app.json"
        )
        
        assert config.enable_json_logs is True
        assert config.json_log_file == "./logs/app.json"
    
    def test_console_level_override(self):
        """Test override de nivel para consola"""
        config = LoggingConfig(
            level="INFO",
            console_level="DEBUG"
        )
        
        assert config.level == "INFO"
        assert config.console_level == "DEBUG"


class TestLoggingConfigIntegration:
    """Tests de integración para LoggingConfig"""
    
    def test_complete_environment_configuration(self):
        """Test configuración completa con variables de entorno"""
        env_config = {
            "LOG_LEVEL": "DEBUG",
            "LOG_ENABLE_FILE": "true",
            "LOG_ENABLE_CONSOLE": "true",
            "LOG_ENABLE_JSON": "true",
            "LOG_FILE": "./logs/debug.log",
            "LOG_MAX_SIZE": "20 MB",
            "LOG_BACKUP_COUNT": "7",
            "LOG_CONSOLE_LEVEL": "INFO"
        }
        
        with patch.dict(os.environ, env_config):
            config = LoggingConfig()
            
            assert config.level == "DEBUG"
            assert config.enable_file_logging is True
            assert config.enable_console_logging is True
            assert config.enable_json_logs is True
            assert config.log_file == "./logs/debug.log"
            assert config.max_file_size == "20 MB"
            assert config.backup_count == 7
            assert config.console_level == "INFO"
    
    def test_configuration_serialization(self):
        """Test serialización de configuración"""
        config = LoggingConfig(
            level="INFO",
            enable_file_logging=True,
            enable_console_logging=True
        )
        
        config_dict = config.model_dump()
        
        assert isinstance(config_dict, dict)
        assert config_dict["level"] == "INFO"
        assert config_dict["enable_file_logging"] is True
        
        # Deserializar
        new_config = LoggingConfig(**config_dict)
        assert new_config.level == config.level
        assert new_config.enable_file_logging == config.enable_file_logging
    
    def test_boolean_environment_parsing(self):
        """Test parsing de booleanos desde env vars"""
        boolean_tests = [
            ("true", True),
            ("false", False),
            ("True", True),
            ("False", False),
            ("TRUE", True),
            ("FALSE", False)
        ]
        
        for env_value, expected in boolean_tests:
            with patch.dict(os.environ, {"LOG_ENABLE_FILE": env_value}):
                config = LoggingConfig()
                assert config.enable_file_logging == expected


class TestLoggingConfigValidation:
    """Tests de validación para LoggingConfig"""
    
    def test_multiple_output_configuration(self):
        """Test configuración con múltiples outputs"""
        config = LoggingConfig(
            enable_console_logging=False,
            enable_file_logging=False,
            enable_json_logs=False
        )
        
        assert config.enable_console_logging is False
        assert config.enable_file_logging is False
        assert config.enable_json_logs is False
    
    def test_file_path_configuration(self):
        """Test configuración de rutas de archivos"""
        valid_paths = [
            "./logs/app.log",
            "/tmp/app.log",
            "logs/app.log",
            "./custom/path/app.log"
        ]
        
        for path in valid_paths:
            config = LoggingConfig(log_file=path)
            assert config.log_file == path
    
    def test_size_format_variations(self):
        """Test diferentes formatos de tamaño"""
        size_variations = [
            "10MB", "10 MB", "10.5 MB", "1GB", "1 GB", 
            "500KB", "500 KB", "2.5GB", "100MB"
        ]
        
        for size in size_variations:
            config = LoggingConfig(max_file_size=size)
            assert config.max_file_size == size


# Fixtures para tests
@pytest.fixture
def sample_logging_config():
    """Fixture con configuración de logging de ejemplo"""
    return LoggingConfig(
        level="INFO",
        enable_file_logging=True,
        enable_console_logging=True,
        log_file="./logs/test.log",
        max_file_size="10 MB",
        backup_count=5
    )


@pytest.fixture
def json_logging_config():
    """Fixture con configuración JSON de ejemplo"""
    return LoggingConfig(
        level="DEBUG",
        enable_console_logging=True,
        enable_file_logging=True,
        enable_json_logs=True,
        log_file="./logs/app.log",
        json_log_file="./logs/app.json"
    )


@pytest.fixture
def clean_log_environment():
    """Fixture que limpia variables de entorno de logging"""
    log_vars = [key for key in os.environ.keys() if key.startswith('LOG_')]
    
    original_values = {}
    for var in log_vars:
        if var in os.environ:
            original_values[var] = os.environ[var]
            del os.environ[var]
    
    yield
    
    # Restaurar valores originales
    for var, value in original_values.items():
        os.environ[var] = value
