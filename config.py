#!/usr/bin/env python3
"""
Configuración centralizada para los agentes de chat
Usa archivos YAML y variables de entorno para configuración
"""

import os
from typing import Any, Dict, List

import yaml
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()


class ConfigManager:
    """Gestor de configuración que combina YAML y variables de entorno"""

    def __init__(self, config_file: str = "agent_config.yaml"):
        self.config_file = config_file
        self._config = self._load_config()
        self._ensure_directories()

    def _load_config(self) -> Dict[str, Any]:
        """Carga la configuración desde el archivo YAML"""
        try:
            with open(self.config_file, "r", encoding="utf-8") as f:
                config = yaml.safe_load(f)
            return config or {}
        except FileNotFoundError:
            print(f"⚠️  Archivo de configuración {self.config_file} no encontrado")
            return self._get_default_config()
        except yaml.YAMLError as e:
            print(f"❌ Error al leer configuración YAML: {e}")
            return self._get_default_config()

    def _get_default_config(self) -> Dict[str, Any]:
        """Configuración por defecto si no existe el archivo YAML"""
        return {
            "model": {"provider": "openai", "id": "gpt-3.5-turbo", "temperature": 0.7},
            "database": {
                "url": "sqlite:///./data/qa_intelligence.db",
                "paths": {
                    "conversations": "data/chat_conversations.db",
                    "knowledge": "data/agno_knowledge.db",
                },
            },
            "tools": {
                "web_search": True,
                "python_execution": True,
                "file_operations": False,
            },
            "interface": {
                "terminal": {"show_tool_calls": True, "enable_markdown": True},
                "playground": {"enabled": True, "port": 7777},
            },
        }

    def _ensure_directories(self):
        """Crea los directorios necesarios"""
        data_dir = self.get("environment.data_directory", "data")
        logs_dir = self.get("environment.logs_directory", "logs")

        for directory in [data_dir, logs_dir]:
            os.makedirs(directory, exist_ok=True)

        # Crear directorios específicos de bases de datos
        db_paths = self.get("database.paths", {})
        for path in db_paths.values():
            if isinstance(path, str) and "/" in path:
                dir_path = os.path.dirname(path)
                os.makedirs(dir_path, exist_ok=True)

    def get(self, key: str, default: Any = None) -> Any:
        """
        Obtiene un valor de configuración usando notación de punto
        Ejemplo: config.get("model.provider") -> "openai"
        """
        keys = key.split(".")
        value = self._config

        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default

        return value

    def set(self, key: str, value: Any):
        """Establece un valor de configuración"""
        keys = key.split(".")
        config = self._config

        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]

        config[keys[-1]] = value

    def get_api_key(self) -> str:
        """Obtiene la API key según el proveedor configurado"""
        provider = self.get("model.provider", "openai")

        if provider == "openai":
            key = os.getenv("OPENAI_API_KEY")
            if not key:
                raise ValueError("OPENAI_API_KEY no configurada en .env")
            return key
        elif provider == "azure":
            key = os.getenv("AZURE_API_KEY")
            if not key:
                raise ValueError("AZURE_API_KEY no configurada en .env")
            return key
        elif provider == "deepseek":
            key = os.getenv("DEEPSEEK_API_KEY")
            if not key:
                raise ValueError("DEEPSEEK_API_KEY no configurada en .env")
            return key
        else:
            raise ValueError(f"Proveedor no soportado: {provider}")

    def get_model_config(self) -> Dict[str, Any]:
        """Obtiene la configuración completa del modelo"""
        return {
            "provider": self.get("model.provider", "openai"),
            "id": self.get("model.id", "gpt-3.5-turbo"),
            "temperature": self.get("model.temperature", 0.7),
            "max_tokens": self.get("model.max_tokens"),
            "api_key": self.get_api_key(),
        }

    def get_database_config(self) -> Dict[str, Any]:
        """Obtiene la configuración de base de datos usando .env como fuente principal"""
        # Usar variables del .env como fuente principal
        conversations_path = os.getenv(
            "QA_AGENT_DB_PATH",
            self.get("database.paths.conversations", "data/qa_conversations.db"),
        )

        return {
            "url": os.getenv(
                "DB_URL",
                self.get("database.url", "sqlite:///./data/qa_intelligence.db"),
            ),
            "conversations_path": conversations_path,
            "knowledge_path": os.getenv(
                "QA_KNOWLEDGE_DB_PATH",
                self.get("database.paths.knowledge", "data/agno_knowledge.db"),
            ),
            "rag_path": os.getenv(
                "QA_RAG_DB_PATH",
                self.get("database.paths.rag", "data/qa_intelligence_rag.db"),
            ),
            "data_dir": os.getenv("QA_DATA_DIR", "data"),
        }

    def get_agent_instructions(self) -> List[str]:
        """Obtiene las instrucciones del agente"""
        return self.get(
            "agent.instructions",
            [
                "Eres un asistente de IA útil y amigable.",
                "Responde de manera clara y concisa.",
                "Mantén un tono profesional pero accesible.",
            ],
        )

    def get_enabled_tools(self) -> Dict[str, bool]:
        """Obtiene qué herramientas están habilitadas"""
        return {
            "web_search": self.get("tools.web_search", True),
            "python_execution": self.get("tools.python_execution", True),
            "file_operations": self.get("tools.file_operations", False),
            "calculator": self.get("tools.calculator", True),
        }

    def get_interface_config(self) -> Dict[str, Any]:
        """Obtiene configuración de interfaz"""
        return {
            "show_tool_calls": self.get("interface.terminal.show_tool_calls", True),
            "enable_markdown": self.get("interface.terminal.enable_markdown", True),
            "playground_enabled": self.get("interface.playground.enabled", True),
            "playground_port": self.get("interface.playground.port", 7777),
        }

    def get_reasoning_config(self) -> Dict[str, Any]:
        """Get reasoning configuration"""
        return {
            "enabled": self.get("reasoning.enabled", False),
            "type": self.get("reasoning.type", "tools"),
            "model_id": self.get("reasoning.model_id", "o3-mini"),
            "add_instructions": self.get("reasoning.add_instructions", True),
            "show_full_reasoning": self.get("reasoning.show_full_reasoning", True),
            "stream_intermediate_steps": self.get(
                "reasoning.stream_intermediate_steps", True
            ),
        }

    def validate_config(self) -> bool:
        """Valida que la configuración sea correcta"""
        try:
            # Validar API key
            self.get_api_key()

            # Validar modelo
            model_config = self.get_model_config()
            if not model_config["id"]:
                raise ValueError("ID del modelo no configurado")

            # Validar directorios
            self._ensure_directories()

            return True
        except Exception as e:
            print(f"❌ Error de validación: {e}")
            return False

    def print_summary(self):
        """Imprime un resumen de la configuración"""
        model_config = self.get_model_config()
        db_config = self.get_database_config()
        tools = self.get_enabled_tools()
        interface = self.get_interface_config()

        print("📋 Configuración Actual")
        print("=" * 50)
        print(f"🤖 Modelo: {model_config['provider']} / {model_config['id']}")
        print(f"🌡️  Temperatura: {model_config['temperature']}")
        print(
            f"🔑 API Key: {'✅ Configurada' if self.get_api_key() else '❌ Faltante'}"
        )
        print()
        print("🗄️  Bases de Datos:")
        print(f"   Principal: {db_config['url']}")
        print(f"   Chat: {db_config['conversations_path']}")
        print(f"   Conocimiento: {db_config['knowledge_path']}")
        print()
        print("�️  Herramientas:")
        for tool, enabled in tools.items():
            status = "✅" if enabled else "❌"
            print(f"   {tool}: {status}")
        print()
        print("🖥️  Interfaz:")
        print(f"   Markdown: {'✅' if interface['enable_markdown'] else '❌'}")
        print(f"   Tool calls: {'✅' if interface['show_tool_calls'] else '❌'}")
        print(f"   Playground: {'✅' if interface['playground_enabled'] else '❌'}")
        print("=" * 50)

    def save_config(self):
        """Guarda la configuración actual al archivo YAML"""
        try:
            with open(self.config_file, "w", encoding="utf-8") as f:
                yaml.dump(
                    self._config,
                    f,
                    default_flow_style=False,
                    allow_unicode=True,
                    indent=2,
                )
            print(f"✅ Configuración guardada en {self.config_file}")
        except Exception as e:
            print(f"❌ Error al guardar configuración: {e}")


# Instancia global de configuración
config = ConfigManager()


def get_config() -> ConfigManager:
    """Función helper para obtener la configuración"""
    return config


if __name__ == "__main__":
    # Test de configuración
    config = get_config()
    config.print_summary()

    if config.validate_config():
        print("✅ Configuración válida y lista para usar")
    else:
        print("❌ Hay problemas en la configuración")
