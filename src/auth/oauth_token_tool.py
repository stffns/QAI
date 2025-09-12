#!/usr/bin/env python3
"""
OAuth Token Generator Tool para QA Intelligence Agent

Herramienta integrada con el esquema QAI para generar tokens OAuth reales
desde configuración en base de datos para pruebas de carga Gatling.

Uso desde el agente QAI:
    from src.auth.oauth_token_tool import OAuthTokenTool

    tool = OAuthTokenTool()

    # Listar configuraciones disponibles
    configs = tool.list_available_configurations()

    # Generar token real
    result = tool.generate_token("EVA", "STA", "RO")

Uso directo:
    python src/auth/oauth_token_tool.py --list
    python src/auth/oauth_token_tool.py EVA STA RO
"""

import os
import sys
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

# Agregar el path del proyecto
sys.path.append(os.path.join(os.path.dirname(__file__), "..", ".."))

try:
    from src.auth.real_oauth_from_database import RealOAuthFromDatabase
except ImportError:
    # Fallback para ejecución directa
    import os
    import sys

    sys.path.append(os.path.join(os.path.dirname(__file__), "..", ".."))
    from src.auth.real_oauth_from_database import RealOAuthFromDatabase


class OAuthTokenTool:
    """
    Herramienta OAuth integrada con QA Intelligence Agent

    Genera tokens OAuth reales desde configuración en base de datos
    para pruebas automatizadas y de carga (Gatling).

    Estructura de datos integrada:
    - oauth_users -> mapping_id (app_environment_country_mappings)
    - oauth_jwks -> environment_id (environments_master)
    - oauth_app_clients -> mapping_id (app_environment_country_mappings) ⭐
    """

    def __init__(self):
        """Inicializar herramienta OAuth"""
        self.oauth_generator = RealOAuthFromDatabase()
        self.config_loader = self.oauth_generator.db_loader  # DatabaseOAuthConfigLoader

    def list_available_configurations(self) -> List[Dict[str, Any]]:
        """
        Listar todas las configuraciones OAuth disponibles

        Returns:
            Lista de configuraciones con estructura:
            {
                'config_key': 'EVA STA RO',
                'app_code': 'EVA',
                'env_code': 'STA',
                'country_code': 'RO',
                'app_name': 'EVA App',
                'env_name': 'Staging',
                'country_name': 'Romania',
                'user_email': 'qa.auto.soco.ro+2@gmail.com',
                'client_id': '84d70f23-df50-4ed2-9d60-...',
                'is_complete': True
            }
        """

        try:
            # Obtener configuraciones desde BD
            db_configs = self.config_loader.list_available_configurations()

            formatted_configs = []

            for config in db_configs:
                # Verificar si la configuración está completa
                is_complete = all(
                    [
                        config.get("user_email"),
                        config.get("client_id"),
                        config.get("jwk_key_id"),
                    ]
                )

                formatted_config = {
                    "config_key": f"{config['app_code']} {config['env_code']} {config['country_code']}",
                    "app_code": config["app_code"],
                    "env_code": config["env_code"],
                    "country_code": config["country_code"],
                    "app_name": config["app_name"],
                    "env_name": config["env_name"],
                    "country_name": config["country_name"],
                    "user_email": config.get("user_email"),
                    "client_id": config.get("client_id"),
                    "jwk_key_id": config.get("jwk_key_id"),
                    "is_complete": is_complete,
                    "description": f"{config['app_name']} | {config['env_name']} | {config['country_name']}",
                }

                formatted_configs.append(formatted_config)

            return formatted_configs

        except Exception as e:
            print(f"❌ Error listando configuraciones: {e}")
            return []

    def generate_token(
        self, app_code: str, env_code: str, country_code: str
    ) -> Dict[str, Any]:
        """
        Generar token OAuth real para configuración específica

        Args:
            app_code: Código de aplicación (EVA, SCIK, etc.)
            env_code: Código de ambiente (STA, PRO, etc.)
            country_code: Código de país (RO, US, etc.)

        Returns:
            Resultado con estructura:
            {
                'success': True/False,
                'access_token': 'token_string',
                'token_type': 'Bearer',
                'expires_in': 1800,
                'configuration': {...},
                'generated_at': 'ISO_timestamp',
                'error': 'error_message' (si success=False)
            }
        """

        try:
            # Generar token usando sistema híbrido
            result = self.oauth_generator.get_real_token(
                app_code, env_code, country_code
            )

            # Agregar metadatos adicionales
            result["expires_in"] = 1800  # 30 minutos por defecto
            result["tool_version"] = "1.0.0"
            result["integration"] = "QA Intelligence Agent"

            return result

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "generated_at": datetime.now(timezone.utc).isoformat(),
            }

    def validate_configuration(
        self, app_code: str, env_code: str, country_code: str
    ) -> Dict[str, Any]:
        """
        Validar si existe configuración OAuth para parámetros dados

        Args:
            app_code: Código de aplicación
            env_code: Código de ambiente
            country_code: Código de país

        Returns:
            {
                'is_valid': True/False,
                'config_exists': True/False,
                'missing_components': [],
                'config_details': {...}
            }
        """

        try:
            # Cargar configuración desde BD
            config = self.config_loader.load_oauth_configuration(
                app_code, env_code, country_code
            )

            if not config:
                return {
                    "is_valid": False,
                    "config_exists": False,
                    "missing_components": ["mapping_not_found"],
                    "config_details": None,
                }

            # Verificar componentes requeridos
            missing_components = []

            if not config.get("user"):
                missing_components.append("oauth_user")

            if not config.get("jwk"):
                missing_components.append("oauth_jwk")

            if not config.get("client"):
                missing_components.append("oauth_app_client")

            is_valid = len(missing_components) == 0

            return {
                "is_valid": is_valid,
                "config_exists": True,
                "missing_components": missing_components,
                "config_details": {
                    "app": f"{config['app_name']} ({config['app_code']})",
                    "environment": f"{config['env_name']} ({config['env_code']})",
                    "country": f"{config['country_name']} ({config['country_code']})",
                    "mapping_id": config["mapping_id"],
                    "has_user": bool(config.get("user")),
                    "has_jwk": bool(config.get("jwk")),
                    "has_client": bool(config.get("client")),
                },
            }

        except Exception as e:
            return {
                "is_valid": False,
                "config_exists": False,
                "missing_components": ["error"],
                "error": str(e),
            }

    def get_gatling_authorization_header(
        self, app_code: str, env_code: str, country_code: str
    ) -> str:
        """
        Generar header Authorization listo para Gatling

        Args:
            app_code: Código de aplicación
            env_code: Código de ambiente
            country_code: Código de país

        Returns:
            String con formato "Bearer {access_token}"

        Raises:
            ValueError: Si no se puede generar el token
        """

        result = self.generate_token(app_code, env_code, country_code)

        if not result["success"]:
            raise ValueError(f"No se pudo generar token: {result.get('error')}")

        return f"Bearer {result['access_token']}"


def main():
    """Función principal para uso directo desde CLI"""

    tool = OAuthTokenTool()

    if len(sys.argv) == 1:
        print(__doc__)
        return

    if sys.argv[1] == "--list":
        print("📋 CONFIGURACIONES OAUTH DISPONIBLES (QAI)")
        print("=" * 50)

        configs = tool.list_available_configurations()

        complete_configs = [c for c in configs if c["is_complete"]]
        incomplete_configs = [c for c in configs if not c["is_complete"]]

        if complete_configs:
            print("✅ CONFIGURACIONES COMPLETAS:")
            for config in complete_configs:
                print(f"   {config['config_key']} - {config['description']}")

        if incomplete_configs:
            print("\n⚠️ CONFIGURACIONES INCOMPLETAS:")
            for config in incomplete_configs:
                print(f"   {config['config_key']} - {config['description']}")
                missing = []
                if not config["user_email"]:
                    missing.append("usuario")
                if not config["client_id"]:
                    missing.append("client")
                if not config["jwk_key_id"]:
                    missing.append("jwk")
                print(f"      Faltan: {', '.join(missing)}")

        return

    if len(sys.argv) == 4:
        app_code, env_code, country_code = sys.argv[1:4]

        print(f"🎯 GENERANDO TOKEN OAUTH (QAI): {app_code} {env_code} {country_code}")
        print("=" * 60)

        # Validar configuración primero
        validation = tool.validate_configuration(app_code, env_code, country_code)

        if not validation["config_exists"]:
            print(
                f"❌ No existe configuración para {app_code} {env_code} {country_code}"
            )
            return

        if not validation["is_valid"]:
            print(f"❌ Configuración incompleta:")
            for component in validation["missing_components"]:
                print(f"   • Falta: {component}")
            return

        # Generar token
        result = tool.generate_token(app_code, env_code, country_code)

        if result["success"]:
            print(f"✅ TOKEN GENERADO EXITOSAMENTE")
            print(f"   🎯 Access Token: {result['access_token'][:40]}...")
            print(f"   📊 Token Type: {result['token_type']}")
            print(f"   🕐 Generated At: {result['generated_at']}")
            print(f"\n🚀 GATLING HEADER:")
            print(f"   Authorization: Bearer {result['access_token']}")
        else:
            print(f"❌ ERROR: {result['error']}")

        return

    print("❌ Uso incorrecto. Use --help para ayuda")
    print(__doc__)


if __name__ == "__main__":
    main()
