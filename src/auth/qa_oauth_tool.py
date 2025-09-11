#!/usr/bin/env python3
"""
QA OAuth Token Tool - Herramienta integrada para el agente QA Intelligence

Esta herramienta proporciona generación de tokens OAuth reales usando
la base de datos integrada del proyecto QAI para pruebas de Gatling.

Características:
- Integración completa con esquema QAI existente
- Soporte para múltiples configuraciones app/environment/country
- Generación de tokens JWT reales con firma ES256
- Base de datos con relaciones FK consistentes
- Compatible con el sistema de testing de Gatling

Uso desde el agente QA:
    from src.auth.qa_oauth_tool import QAOAuthTool
    
    tool = QAOAuthTool()
    token = tool.get_token("EVA", "STA", "RO")
"""

import sys
import os
import sqlite3
import json
import hashlib
import secrets
import base64
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Union

# Importar librerías OAuth
from jose import jws

# Agregar el path del proyecto
sys.path.append(os.path.join(os.path.dirname(__file__), "..", ".."))

class QAOAuthTool:
    """
    Herramienta OAuth integrada para el agente QA Intelligence
    
    Proporciona acceso simplificado a la generación de tokens OAuth
    usando la base de datos integrada del proyecto QAI.
    """
    
    def __init__(self, db_path: str = "data/qa_intelligence.db"):
        """
        Inicializar la herramienta OAuth
        
        Args:
            db_path: Ruta a la base de datos QAI (default: data/qa_intelligence.db)
        """
        self.db_path = Path(db_path)
        if not self.db_path.exists():
            raise FileNotFoundError(f"QAI Database not found: {self.db_path}")
    
    def get_connection(self) -> sqlite3.Connection:
        """Obtener conexión a la base de datos QAI"""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        return conn
    
    def list_configurations(self) -> List[Dict]:
        """
        Listar todas las configuraciones OAuth disponibles
        
        Returns:
            Lista de configuraciones con información de completitud
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
            SELECT DISTINCT
                am.app_code,
                am.app_name,
                em.env_code,
                em.env_name,
                cm.country_code,
                cm.country_name,
                COUNT(ou.id) as user_count,
                COUNT(CASE WHEN oj.is_active = 1 THEN 1 END) as active_jwks,
                COUNT(CASE WHEN oac.is_active = 1 THEN 1 END) as active_clients,
                CASE 
                    WHEN COUNT(ou.id) > 0 AND 
                         COUNT(CASE WHEN oj.is_active = 1 THEN 1 END) > 0 AND
                         COUNT(CASE WHEN oac.is_active = 1 THEN 1 END) > 0 
                    THEN 1 ELSE 0 
                END as is_complete
            FROM app_environment_country_mappings aecm
            JOIN apps_master am ON aecm.application_id = am.id
            JOIN environments_master em ON aecm.environment_id = em.id
            JOIN countries_master cm ON aecm.country_id = cm.id
            LEFT JOIN oauth_users ou ON ou.mapping_id = aecm.id AND ou.is_active = 1
            LEFT JOIN oauth_jwks oj ON oj.environment_id = em.id
            LEFT JOIN oauth_app_clients oac ON oac.application_id = am.id AND oac.environment_id = em.id
            WHERE am.is_active = 1 AND em.is_active = 1 AND cm.is_active = 1
            GROUP BY am.id, em.id, cm.id
            ORDER BY am.app_code, em.env_code, cm.country_code
            """)
            
            configs = cursor.fetchall()
            return [dict(config) for config in configs]
            
        finally:
            conn.close()
    
    def get_token(self, app_code: str, env_code: str, country_code: str) -> Dict:
        """
        Generar token OAuth para una configuración específica
        
        Args:
            app_code: Código de aplicación (ej: EVA, SCIK)
            env_code: Código de ambiente (ej: STA, PRO, DEV)
            country_code: Código de país (ej: RO, US, DE)
        
        Returns:
            Dict con token y metadata, o error si falla
        """
        try:
            # Buscar configuración
            config = self._find_configuration(app_code, env_code, country_code)
            
            if not config:
                return {
                    'success': False,
                    'error': f'Configuration not found: {app_code} {env_code} {country_code}',
                    'available_configs': [
                        f"{c['app_code']} {c['env_code']} {c['country_code']}" 
                        for c in self.list_configurations() if c['is_complete']
                    ]
                }
            
            # Validar completitud
            missing = self._validate_configuration(config)
            if missing:
                return {
                    'success': False,
                    'error': f'Incomplete configuration, missing: {", ".join(missing)}',
                    'config': config
                }
            
            # Generar token
            token_result = self._generate_oauth_token(config)
            
            return {
                'success': True,
                'access_token': token_result['access_token'],
                'token_type': token_result['token_type'],
                'expires_in': token_result['expires_in'],
                'scope': token_result['scope'],
                'configuration': {
                    'app': config['app_code'],
                    'environment': config['env_code'],
                    'country': config['country_code'],
                    'user_email': config['user']['email'],
                    'client_id': config['client']['client_id'][:20] + '...'  # Truncar por seguridad
                },
                'validation': token_result['validation'],
                'generated_at': datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'type': type(e).__name__
            }
    
    def _find_configuration(self, app_code: str, env_code: str, country_code: str) -> Optional[Dict]:
        """Buscar configuración OAuth específica en la base de datos"""
        
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            # Buscar mapping específico
            cursor.execute("""
            SELECT aecm.id as mapping_id,
                   am.app_code, am.app_name, am.id as app_id,
                   em.env_code, em.env_name, em.id as env_id,
                   cm.country_code, cm.country_name, cm.id as country_id
            FROM app_environment_country_mappings aecm
            JOIN apps_master am ON aecm.application_id = am.id
            JOIN environments_master em ON aecm.environment_id = em.id
            JOIN countries_master cm ON aecm.country_id = cm.id
            WHERE am.app_code LIKE ? 
              AND em.env_code = ?
              AND cm.country_code = ?
              AND aecm.is_active = 1
            """, (f'%{app_code.upper()}%', env_code.upper(), country_code.upper()))
            
            mapping = cursor.fetchone()
            if not mapping:
                return None
            
            config = dict(mapping)
            
            # Obtener usuario OAuth
            cursor.execute("""
            SELECT * FROM oauth_users 
            WHERE mapping_id = ? AND is_active = 1
            LIMIT 1
            """, (config['mapping_id'],))
            
            user = cursor.fetchone()
            if user:
                config['user'] = dict(user)
            
            # Obtener JWK activo
            cursor.execute("""
            SELECT * FROM oauth_jwks
            WHERE environment_id = ? AND is_active = 1
            LIMIT 1
            """, (config['env_id'],))
            
            jwk = cursor.fetchone()
            if jwk:
                config['jwk'] = dict(jwk)
                config['jwk']['jwk_data'] = json.loads(jwk['jwk_content'])
            
            # Obtener client OAuth
            cursor.execute("""
            SELECT * FROM oauth_app_clients
            WHERE application_id = ? AND environment_id = ? AND is_active = 1
            LIMIT 1
            """, (config['app_id'], config['env_id']))
            
            client = cursor.fetchone()
            if client:
                config['client'] = dict(client)
            
            return config
            
        finally:
            conn.close()
    
    def _validate_configuration(self, config: Dict) -> List[str]:
        """Validar que la configuración está completa"""
        
        missing = []
        
        if 'user' not in config:
            missing.append('oauth_user')
        if 'jwk' not in config:
            missing.append('jwk_key')
        if 'client' not in config:
            missing.append('oauth_client')
        
        return missing
    
    def _generate_oauth_token(self, config: Dict) -> Dict:
        """Generar token OAuth usando configuración de la base de datos"""
        
        # Generar parámetros JWT
        now = datetime.now(timezone.utc)
        
        # Payload del token
        payload = {
            'iss': f"https://login.{config['env_code'].lower()}.talentscloud.siemens.com",
            'aud': config['client']['client_id'],
            'sub': config['user']['email'],
            'email': config['user']['email'],
            'given_name': config['user']['given_name'],
            'family_name': config['user']['family_name'],
            'phone_number': config['user']['phone_number'],
            'gender': config['user']['gender'],
            'iat': int(now.timestamp()),
            'exp': int(now.timestamp()) + 3600,  # 1 hora de expiración
            'scope': config['client']['default_scopes'],
            'app_code': config['app_code'],
            'env_code': config['env_code'],
            'country_code': config['country_code']
        }
        
        # Header JWT
        header = {
            'alg': 'ES256',
            'typ': 'JWT',
            'kid': config['jwk']['jwk_data']['kid']
        }
        
        # Firmar el token
        access_token = jws.sign(
            payload, 
            config['jwk']['jwk_data'], 
            algorithm='ES256', 
            headers=header
        )
        
        # Validar el token generado
        validation = self._validate_jwt_token(access_token)
        
        return {
            'access_token': access_token,
            'token_type': 'Bearer',
            'expires_in': 3600,
            'scope': config['client']['default_scopes'],
            'validation': validation
        }
    
    def _validate_jwt_token(self, access_token: str) -> Dict:
        """Validar estructura del JWT token generado"""
        
        try:
            # Decodificar header y payload (sin verificar firma)
            header_encoded, payload_encoded, signature = access_token.split('.')
            
            # Agregar padding si es necesario
            header_padded = header_encoded + '=' * (4 - len(header_encoded) % 4)
            payload_padded = payload_encoded + '=' * (4 - len(payload_encoded) % 4)
            
            header_data = json.loads(base64.urlsafe_b64decode(header_padded).decode())
            payload_data = json.loads(base64.urlsafe_b64decode(payload_padded).decode())
            
            return {
                'valid': True,
                'header': header_data,
                'payload_preview': {
                    'subject': payload_data.get('sub'),
                    'audience': payload_data.get('aud'),
                    'issued_at': payload_data.get('iat'),
                    'expires_at': payload_data.get('exp'),
                    'scope': payload_data.get('scope')
                },
                'algorithm': header_data.get('alg'),
                'key_id': header_data.get('kid')
            }
            
        except Exception as e:
            return {
                'valid': False,
                'error': str(e)
            }

# CLI Interface para testing directo
def main():
    """Interfaz de línea de comandos para testing"""
    
    if len(sys.argv) == 1 or '--help' in sys.argv:
        print("QA OAuth Tool - Generador de tokens OAuth integrado")
        print("")
        print("Uso:")
        print("  python qa_oauth_tool.py --list                    # Listar configuraciones")
        print("  python qa_oauth_tool.py EVA STA RO              # Generar token específico")
        print("  python qa_oauth_tool.py --help                   # Esta ayuda")
        print("")
        print("Ejemplos:")
        print("  python qa_oauth_tool.py EVA STA RO")
        print("  python qa_oauth_tool.py SCIK PRO US")
        return
    
    try:
        tool = QAOAuthTool()
        
        if '--list' in sys.argv:
            print("📋 CONFIGURACIONES OAUTH DISPONIBLES")
            print("=" * 50)
            
            configs = tool.list_configurations()
            
            if not configs:
                print("❌ No hay configuraciones OAuth disponibles")
                return
            
            complete_configs = [c for c in configs if c['is_complete']]
            incomplete_configs = [c for c in configs if not c['is_complete']]
            
            if complete_configs:
                print("✅ CONFIGURACIONES COMPLETAS:")
                for config in complete_configs:
                    print(f"   {config['app_code']} {config['env_code']} {config['country_code']} - {config['app_name']} | {config['env_name']} | {config['country_name']}")
            
            if incomplete_configs:
                print("\n⚠️  CONFIGURACIONES INCOMPLETAS:")
                for config in incomplete_configs:
                    missing = []
                    if config['user_count'] == 0:
                        missing.append("usuarios")
                    if config['active_jwks'] == 0:
                        missing.append("JWKs")
                    if config['active_clients'] == 0:
                        missing.append("clients")
                    
                    print(f"   {config['app_code']} {config['env_code']} {config['country_code']} - Faltan: {', '.join(missing)}")
            
            return
        
        # Generar token específico
        if len(sys.argv) < 4:
            print("❌ Error: Se requieren 3 argumentos: APP ENV COUNTRY")
            print("   Ejemplo: python qa_oauth_tool.py EVA STA RO")
            return
        
        app_code = sys.argv[1]
        env_code = sys.argv[2]
        country_code = sys.argv[3]
        
        print(f"🔍 Generando token para {app_code} {env_code} {country_code}...")
        
        result = tool.get_token(app_code, env_code, country_code)
        
        if result['success']:
            print("\n" + "=" * 60)
            print("🎉 TOKEN OAUTH GENERADO EXITOSAMENTE")
            print("=" * 60)
            print(f"Access Token: {result['access_token']}")
            print(f"Token Type: {result['token_type']}")
            print(f"Expires In: {result['expires_in']} segundos")
            print(f"Scope: {result['scope']}")
            print(f"Generated At: {result['generated_at']}")
            print("\n📊 Configuración:")
            config = result['configuration']
            print(f"   App: {config['app']}")
            print(f"   Environment: {config['environment']}")
            print(f"   Country: {config['country']}")
            print(f"   User: {config['user_email']}")
            print(f"   Client ID: {config['client_id']}")
        else:
            print(f"❌ Error: {result['error']}")
            if 'available_configs' in result:
                print("   Configuraciones disponibles:")
                for config in result['available_configs']:
                    print(f"     • {config}")
    
    except Exception as e:
        print(f"❌ Error inesperado: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
