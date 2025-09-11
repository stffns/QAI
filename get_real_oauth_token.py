#!/usr/bin/env python3
"""
Implementación REAL del flujo OAuth/OIDC para obtener access tokens válidos
Replica exactamente el comportamiento del código Scala original
"""

import sys
import os
import json
import base64
import hashlib
import secrets
import urllib.parse
import uuid
import time
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, Optional

# Agregar el path del proyecto
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

import requests
from jose import jws

print("🚀 Iniciando generación de ACCESS TOKEN REAL para EVA STA RO...")

class RealOIDCTokenGenerator:
    """
    Generador de tokens OAuth/OIDC REALES
    Implementa el flujo completo equivalente al código Scala
    """
    
    def __init__(self):
        
        # Configuración EVA STA RO con JWK REAL (del código funcional)
        self.config = {
            "env": "sta",
            "country": "ro", 
            "product": "eva",
            "client_id": "84d70f23-df50-4ed2-9d60-263366326c9d",
            "key_id": "SCIK-QA-STA-20210408-47QNY",
            "locale": "ro", 
            # JWK REAL que funciona (del código AuthenticationOIDCTemporal)
            "jwk": {
                "kid": "SCIK-QA-STA-20210408-47QNY",
                "kty": "EC",
                "crv": "P-256", 
                "x": "ZI2oM8spmX7hhg0KsWZVyVz3Fq7D7rnT2CISwIJk21U",
                "y": "jJkIyEWLvZSNIcRdAxnFZuYLQCTfng1KMOFNXkJcpS4",
                "d": "6D5xCaPKq1gezZTi93Tu8JKSQqpYRNaoqjdlFVQIF2E"
            },
            "user": {
                "email": "qa.auto.soco.ro+2@gmail.com",
                "password": "Test12345#",
                "given_name": "Qa", 
                "family_name": "Qa",
                "phone_number": "+33663005232",
                "gender": "male"  # Como en el JSON ejemplo
            },
            "oidc_domain": "connect.sta.pluxee.app",
            "issuer": "https://connect.sta.pluxee.app/op",
            "callback_url": "http://localhost/oidc/callback",
            "needs_resource_param": False
        }
    
    def get_provider_metadata(self) -> Dict[str, Any]:
        """Obtiene metadatos del proveedor OIDC usando requests"""
        url = f"{self.config['issuer']}/.well-known/openid-configuration"
        print(f"🔍 Obteniendo metadatos OIDC de: {url}")
        
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            metadata = response.json()
            
            print(f"✅ Metadatos obtenidos:")
            print(f"   • Authorization endpoint: {metadata.get('authorization_endpoint', 'N/A')}")
            print(f"   • Token endpoint: {metadata.get('token_endpoint', 'N/A')}")
            
            return metadata
            
        except Exception as e:
            print(f"❌ Error obteniendo metadatos: {e}")
            raise
    
    def generate_pkce(self) -> Dict[str, str]:
        """Genera códigos PKCE para el flujo OAuth"""
        print("🔐 Generando códigos PKCE...")
        
        # Code verifier: random 43-128 caracteres
        code_verifier = base64.urlsafe_b64encode(secrets.token_bytes(32)).decode('utf-8').rstrip('=')
        
        # Code challenge: SHA256 del verifier
        digest = hashlib.sha256(code_verifier.encode('utf-8')).digest()
        code_challenge = base64.urlsafe_b64encode(digest).decode('utf-8').rstrip('=')
        
        print(f"✅ PKCE generado:")
        print(f"   • Code verifier: {code_verifier[:20]}...")
        print(f"   • Code challenge: {code_challenge[:20]}...")
        
        return {
            "code_verifier": code_verifier,
            "code_challenge": code_challenge
        }
    
    def generate_impersonation_token(self, auth_endpoint: str) -> str:
        """
        Genera token de impersonación usando jose.jws exactamente como AuthenticationOIDCTemporal
        """
        print("🎭 Generando token de impersonación JWT con JWK REAL...")
        
        # Payload exacto del código funcional (sin password)
        payload = {
            "jti": str(uuid.uuid4()),
            "aud": auth_endpoint,
            "exp": int(time.time()) + 60,  # 60 segundos como en tu código
            "action": "sign-in",
            "account": {
                "email": self.config["user"]["email"],
                "realm": self.config["country"], 
                "gender": self.config["user"]["gender"],
                "given_name": self.config["user"]["given_name"],
                "family_name": self.config["user"]["family_name"],
                "locale": self.config["locale"],
                "phone_number": self.config["user"]["phone_number"]
            }
        }
        
        # Headers con key ID
        headers = {"kid": self.config["key_id"]}
        
        print(f"   🔑 Key ID: {self.config['key_id']}")
        print(f"   👤 Usuario: {self.config['user']['email']}")
        print(f"   🌍 Realm: {self.config['country']}")
        
        try:
            # Usar jose.jws.sign con JWK real como en tu código funcional
            token = jws.sign(payload, self.config["jwk"], algorithm="ES256", headers=headers)
            print(f"✅ Token de impersonación REAL generado: {token[:50]}...")
            return token
            
        except Exception as e:
            print(f"❌ Error generando token real: {e}")
            raise
    
    def build_authorization_url(self, authorization_endpoint: str, pkce: Dict[str, str], state: Optional[str] = None) -> str:
        """Construye URL de autorización OAuth"""
        print("🔗 Construyendo URL de autorización...")
        
        params = {
            "response_type": "code",
            "client_id": self.config["client_id"],
            "redirect_uri": self.config["callback_url"],
            "scope": "openid profile email",
            "code_challenge": pkce["code_challenge"],
            "code_challenge_method": "S256",
        }
        
        if state:
            params["state"] = state
        
        query_string = urllib.parse.urlencode(params)
        auth_url = f"{authorization_endpoint}?{query_string}"
        
        print(f"✅ URL de autorización: {auth_url[:100]}...")
        return auth_url
    
    def get_authorization_code_real(self, auth_url: str, impersonation_token: str) -> str:
        """
        Obtiene el código de autorización usando requests exactamente como AuthenticationOIDCTemporal
        """
        print("🌐 Obteniendo código de autorización REAL con requests...")
        print(f"   🍪 Token de impersonación: {impersonation_token[:50]}...")
        
        # Crear sesión con cookie exactamente como tu código funcional
        session = requests.Session()
        session.cookies.set(
            "sc_impersonation_token", 
            impersonation_token, 
            domain=self.config["oidc_domain"], 
            path="/op"
        )
        session.max_redirects = 5
        
        print(f"   🔗 URL inicial: {auth_url[:80]}...")
        
        # Seguir redirects exactamente como follow_oidc_redirects() - sin límite como en tu código
        current_url = auth_url
        redirect_count = 0
        max_redirects = 50  # Aumentar límite significativamente
        
        while not current_url.startswith(self.config["callback_url"]) and redirect_count < max_redirects:
            print(f"   🔄 Redirect #{redirect_count + 1}")
            
            response = session.get(current_url, allow_redirects=False)
            status = response.status_code
            
            print(f"   📊 Status: {status}")
            
            if status in [301, 302, 303]:
                location = response.headers.get("Location")
                if not location:
                    raise Exception("Redirect without Location header")
                
                # Manejar URLs relativas
                if not location.startswith("http"):
                    from urllib.parse import urlparse, urljoin
                    base_url = f"https://{urlparse(auth_url).netloc}"
                    current_url = urljoin(base_url, location)
                else:
                    current_url = location
                
                print(f"   ↗️  Redirect a: {current_url[:60]}...")
                redirect_count += 1
            else:
                print(f"   ❌ Status inesperado: {status}")
                print(f"   📄 Response: {response.text[:200]}")
                raise Exception(f"Unexpected status code: {status}")
        
        if redirect_count >= max_redirects:
            raise Exception(f"Too many redirects ({max_redirects})")
        
        # Extraer código del callback URL
        print(f"   🎯 ¡Llegamos al callback URL!")
        from urllib.parse import urlparse, parse_qs
        parsed_url = urlparse(current_url)
        query_params = parse_qs(parsed_url.query)
        
        if "code" not in query_params:
            raise Exception("Authorization code not found in redirect URL")
        
        code = query_params["code"][0]
        print(f"   ✅ Código extraído: {code[:20]}...")
        return code
    
    def exchange_code_for_tokens(self, token_endpoint: str, authorization_code: str, pkce: Dict[str, str]) -> Dict[str, Any]:
        """
        Intercambia authorization code por access token usando requests como AuthenticationOIDCTemporal
        """
        print("💱 Intercambiando código por tokens...")
        
        try:
            # Datos para el intercambio exactos del código funcional
            data = [
                ("grant_type", "authorization_code"),
                ("code", authorization_code),
                ("client_id", self.config["client_id"]),
                ("redirect_uri", self.config["callback_url"]),
                ("code_verifier", pkce["code_verifier"]),
            ]
            
            # Agregar resource si es necesario
            if (self.config["env"] == "sta" and self.config["product"] == "one-app") or self.config["product"] == "m-app":
                data.append(("resource", "https://api.sta.pluxee.app"))
            
            print(f"   📤 Enviando request a: {token_endpoint}")
            
            headers = {"Content-Type": "application/x-www-form-urlencoded"}
            
            response = requests.post(token_endpoint, data=data, headers=headers, timeout=10)
            response.raise_for_status()
            
            tokens = response.json()
            print(f"   ✅ Tokens obtenidos exitosamente!")
            print(f"   • Access token: {tokens.get('access_token', 'N/A')[:50]}...")
            print(f"   • Token type: {tokens.get('token_type', 'N/A')}")
            print(f"   • Expires in: {tokens.get('expires_in', 'N/A')} segundos")
            
            return tokens
                
        except Exception as e:
            print(f"   ❌ Error intercambiando código: {e}")
            raise
    
    def get_real_access_token(self) -> str:
        """
        Método principal - obtiene access token real
        Equivalente completo a OIDCAuthentication.getAccessToken() del código Scala
        """
        print("\n" + "="*70)
        print("🎯 GENERANDO ACCESS TOKEN REAL - EVA STA RO")
        print("="*70)
        print("Replicando: OIDCAuthentication(\"sta\", \"ro\", \"eva\").getAccessToken()")
        print("="*70)
        
        try:
            # Paso 1: Obtener metadatos del proveedor
            metadata = self.get_provider_metadata()
            
            # Paso 2: Generar PKCE
            pkce = self.generate_pkce()
            
            # Paso 3: Generar token de impersonación
            impersonation_token = self.generate_impersonation_token(
                metadata["authorization_endpoint"]
            )
            
            # Paso 4: Construir URL de autorización
            auth_url = self.build_authorization_url(
                metadata["authorization_endpoint"],
                pkce,
                secrets.token_urlsafe(16)
            )
            
            # Paso 5: Obtener authorization code REAL
            authorization_code = self.get_authorization_code_real(
                auth_url, 
                impersonation_token
            )
            
            # Paso 6: Intercambiar código por tokens
            tokens = self.exchange_code_for_tokens(
                metadata["token_endpoint"],
                authorization_code,
                pkce
            )
            
            access_token = tokens["access_token"]
            
            print("\n" + "="*70)
            print("✅ ACCESS TOKEN REAL OBTENIDO!")
            print("="*70)
            print(f"🎯 Token: {access_token}")
            print(f"\n📊 Información del token:")
            print(f"   • Tipo: {tokens.get('token_type', 'Bearer')}")
            print(f"   • Expira en: {tokens.get('expires_in', 'N/A')} segundos")
            print(f"   • Scopes: {tokens.get('scope', 'N/A')}")
            print(f"\n🔧 Configuración utilizada:")
            print(f"   • Ambiente: {self.config['env'].upper()}")
            print(f"   • País: {self.config['country'].upper()}")
            print(f"   • Producto: {self.config['product'].upper()}")
            print(f"   • Usuario: {self.config['user']['email']}")
            print(f"   • Client ID: {self.config['client_id']}")
            
            return access_token
            
        except Exception as e:
            print(f"\n❌ ERROR OBTENIENDO TOKEN REAL: {e}")
            import traceback
            traceback.print_exc()
            raise
        
        finally:
            # No necesario con requests
            pass

def main():
    """Función principal para obtener token real"""
    try:
        generator = RealOIDCTokenGenerator()
        access_token = generator.get_real_access_token()
        
        print(f"\n🚀 LISTO PARA USAR EN GATLING:")
        print(f"Authorization: Bearer {access_token}")
        
        return access_token
        
    except Exception as e:
        print(f"💥 Error: {e}")
        return None

if __name__ == "__main__":
    # Instalar dependencias si no están
    try:
        import jwt
        import cryptography
    except ImportError:
        print("📦 Instalando dependencias necesarias...")
        os.system("pip install PyJWT cryptography")
        import jwt
        import cryptography
    
    main()
