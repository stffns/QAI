#!/usr/bin/env python3
"""
OAuth Tools for QA Intelligence Agent

SOLID Architecture - Uses ONLY OAuth Repository (no SQL duplication)
Provides OAuth token generation, configuration listing, and validation tools.
"""

import json
import os
import sys
from typing import Dict, Any, Optional

from agno.tools import tool

# Import logging
try:
    from src.logging_config import get_logger, LogStep, LogExecutionTime
except ImportError:
    sys.path.append(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
    from src.logging_config import get_logger, LogStep, LogExecutionTime

# Import OAuth repository (SOLID architecture - no SQL duplication)
try:
    from database.repositories.oauth_repository import OAuthRepository
    from database.connection import db_manager
    from sqlmodel import Session
except ImportError:
    sys.path.append(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
    from database.repositories.oauth_repository import OAuthRepository
    from database.connection import db_manager
    from sqlmodel import Session

# Real OAuth generator will be imported only when needed to avoid model conflicts
RealOAuthFromDatabase = None

logger = get_logger("OAuthTools")


def generate_oauth_token_raw(app_code: str, env_code: str, country_code: str) -> str:
    """Generate OAuth token - raw function for direct calling"""
    
    try:
        with LogStep(f"Generating OAuth token for {app_code} {env_code} {country_code}", "OAuthTools"):
            # Use OAuth repository - SOLID architecture, no SQL duplication
            engine = db_manager.engine
            with Session(engine) as session:
                oauth_repo = OAuthRepository(session)
                
                # Get OAuth configuration using repository
                config = oauth_repo.get_complete_oauth_config(app_code, env_code, country_code)
                
                if not config:
                    logger.error(f"OAuth configuration not found for {app_code} {env_code} {country_code}")
                    return json.dumps({
                        "success": False,
                        "error": f"OAuth configuration not found for {app_code} {env_code} {country_code}",
                        "app_code": app_code,
                        "env_code": env_code,
                        "country_code": country_code
                    })
                
                # Simple validation - check if we have the basic components
                has_user = config.get('user') is not None
                has_jwk = config.get('jwk') is not None
                has_client = config.get('client') is not None
                
                if not (has_user and has_jwk and has_client):
                    missing = []
                    if not has_user: missing.append('oauth_user')
                    if not has_jwk: missing.append('oauth_jwk')
                    if not has_client: missing.append('oauth_client')
                    
                    logger.error(f"Incomplete OAuth setup. Missing: {missing}")
                    return json.dumps({
                        "success": False,
                        "error": f"Incomplete OAuth setup. Missing components: {', '.join(missing)}",
                        "missing_components": missing,
                        "app_code": app_code,
                        "env_code": env_code,
                        "country_code": country_code
                    })
                
                # Generate real OAuth access token using the existing system
                try:
                    # Import real OAuth generator when needed to avoid model conflicts
                    try:
                        from src.auth.real_oauth_from_database import RealOAuthFromDatabase
                    except Exception as import_err:
                        # Model conflict or import error
                        logger.warning(f"Cannot import RealOAuthFromDatabase: {import_err}")
                        return json.dumps({
                            "success": False,
                            "error": "Real OAuth token generation unavailable due to model conflicts",
                            "note": "OAuth configuration is complete but token generation requires model fixes",
                            "technical_error": str(import_err),
                            "app_code": app_code,
                            "env_code": env_code,
                            "country_code": country_code,
                            "config_available": True
                        })
                    
                    logger.info(f"Generating real OAuth access token for {app_code} {env_code} {country_code}")
                    
                    # Create OAuth generator and get real token
                    oauth_generator = RealOAuthFromDatabase()
                    token_result = oauth_generator.get_real_token(app_code, env_code, country_code)
                    
                    if token_result.get('access_token'):
                        logger.info(f"Real OAuth access token generated successfully for {app_code} {env_code} {country_code}")
                        return json.dumps({
                            "success": True,
                            "access_token": token_result['access_token'],
                            "token_type": token_result.get('token_type', 'Bearer'),
                            "expires_in": token_result.get('expires_in', 1800),  # 30 minutes default
                            "scope": "openid profile email",
                            "app_code": app_code,
                            "env_code": env_code,
                            "country_code": country_code,
                            "user_email": config.get('user', {}).get('email') if config.get('user') else None,
                            "client_id": config.get('client', {}).get('client_id') if config.get('client') else None,
                            "jwk_key_id": config.get('jwk', {}).get('key_id') if config.get('jwk') else None,
                            "generated_at": token_result.get('generated_at'),
                            "gatling_header": f"Authorization: Bearer {token_result['access_token']}",
                            "configuration": token_result.get('configuration', {})
                        })
                    else:
                        logger.error(f"Failed to generate real OAuth token: {token_result.get('error')}")
                        return json.dumps({
                            "success": False,
                            "error": f"Failed to generate OAuth token: {token_result.get('error')}",
                            "app_code": app_code,
                            "env_code": env_code,
                            "country_code": country_code
                        })
                        
                except Exception as e:
                    logger.error(f"Unexpected error generating real OAuth token: {e}")
                    return json.dumps({
                        "success": False,
                        "error": f"Error generating OAuth token: {str(e)}",
                        "app_code": app_code,
                        "env_code": env_code,
                        "country_code": country_code
                    })
                
    except Exception as e:
        logger.error(f"Unexpected error generating OAuth token: {e}")
        return json.dumps({
            "success": False,
            "error": f"Unexpected error: {str(e)}",
            "app_code": app_code,
            "env_code": env_code,
            "country_code": country_code
        })


def list_oauth_configurations_raw() -> str:
    """List available OAuth configurations - raw function for direct calling"""
    
    try:
        with LogStep("Listing OAuth configurations", "OAuthTools"):
            # Use OAuth repository - SOLID architecture
            engine = db_manager.engine
            with Session(engine) as session:
                oauth_repo = OAuthRepository(session)
                
                # Note: For now we'll return a message that this needs implementation
                # This avoids SQL duplication until we add get_all_configs to repository
                return json.dumps({
                    "success": True,
                    "message": "OAuth configuration listing requires get_all_configs implementation in repository",
                    "note": "Use oauth_validate_setup for specific app/env/country validation",
                    "configurations": []
                })
                
    except Exception as e:
        logger.error(f"Error listing OAuth configurations: {e}")
        return json.dumps({
            "success": False,
            "error": f"Error listing OAuth configurations: {str(e)}",
            "configurations": []
        })


def validate_oauth_setup_raw(app_code: str, env_code: str, country_code: str) -> str:
    """Validate OAuth setup for specific app/env/country - raw function for direct calling"""
    
    try:
        with LogStep(f"Validating OAuth setup for {app_code} {env_code} {country_code}", "OAuthTools"):
            # Use OAuth repository - SOLID architecture
            engine = db_manager.engine
            with Session(engine) as session:
                oauth_repo = OAuthRepository(session)
                
                # Get configuration using repository
                config = oauth_repo.get_complete_oauth_config(app_code, env_code, country_code)
                
                if not config:
                    return json.dumps({
                        "success": True,
                        "is_valid": False,
                        "error": f"No OAuth configuration found for {app_code}/{env_code}/{country_code}",
                        "app_code": app_code,
                        "env_code": env_code,
                        "country_code": country_code,
                        "missing_components": ["mapping", "user", "jwk", "client"],
                        "components": {
                            "mapping": None,
                            "user": None,
                            "jwk": None,
                            "client": None
                        }
                    })
                
                # Detailed validation
                has_user = config.get('user') is not None
                has_jwk = config.get('jwk') is not None
                has_client = config.get('client') is not None
                
                missing_components = []
                if not has_user: missing_components.append('oauth_user')
                if not has_jwk: missing_components.append('oauth_jwk')
                if not has_client: missing_components.append('oauth_client')
                
                is_valid = len(missing_components) == 0
                
                # Extract serializable data from repository dicts
                user_data = None
                if has_user:
                    user = config.get('user')
                    user_data = {
                        "id": user.get("id"),
                        "email": user.get("email"),
                        "given_name": user.get("given_name"),
                        "family_name": user.get("family_name"),
                        "locale": user.get("locale"),
                        "is_active": user.get("is_active")
                    }
                
                jwk_data = None
                if has_jwk:
                    jwk = config.get('jwk')
                    jwk_data = {
                        "id": jwk.get("id"),
                        "key_id": jwk.get("key_id"),
                        "algorithm": jwk.get("algorithm"),
                        "is_active": jwk.get("is_active")
                    }
                
                client_data = None
                if has_client:
                    client = config.get('client')
                    client_data = {
                        "id": client.get("id"),
                        "client_id": client.get("client_id"),
                        "client_name": client.get("client_name"),
                        "is_active": client.get("is_active")
                    }
                
                return json.dumps({
                    "success": True,
                    "is_valid": is_valid,
                    "app_code": app_code,
                    "env_code": env_code,
                    "country_code": country_code,
                    "missing_components": missing_components,
                    "components": {
                        "mapping": {
                            "app_name": config.get('app_name'),
                            "env_name": config.get('env_name'),
                            "country_name": config.get('country_name'),
                            "mapping_id": config.get('mapping_id')
                        },
                        "user": user_data,
                        "jwk": jwk_data,
                        "client": client_data
                    },
                    "validation_summary": f"OAuth setup is {'COMPLETE' if is_valid else 'INCOMPLETE'}"
                })
                
    except Exception as e:
        logger.error(f"Error validating OAuth setup: {e}")
        return json.dumps({
            "success": False,
            "error": f"Error validating OAuth setup: {str(e)}",
            "app_code": app_code,
            "env_code": env_code,
            "country_code": country_code
        })


# AGENT TOOLS - using @tool decorator

@tool
def oauth_generate_token(app_code: str, env_code: str, country_code: str) -> str:
    """Generate OAuth access token from database configuration.
    
    Args:
        app_code: Application code (e.g., 'swile-app', 'pluxee-appweb', 'EVA')
        env_code: Environment code (STA, DEV, PROD)
        country_code: Country code (FR, ES, BR, RO, etc.)
        
    Returns:
        Real OAuth access token for use in API calls
    """
    try:
        result_json = generate_oauth_token_raw(app_code, env_code, country_code)
        result = json.loads(result_json)
        
        if result.get('success') and result.get('access_token'):
            token = result['access_token']
            expires_in = result.get('expires_in', 'Unknown')
            
            return f"""✅ OAuth Token Generated Successfully!

🔑 **Access Token**: {token[:50]}...
⏰ **Expires In**: {expires_in} seconds
🌐 **Environment**: {env_code.upper()}
🏗️ **Application**: {app_code}
🌍 **Country**: {country_code.upper()}

📋 **Ready for Gatling/API Use**:
{result.get('gatling_header', f'Authorization: Bearer {token}')}

💡 **Note**: This is a REAL access token from OAuth server"""
        else:
            error_msg = result.get('error', 'Unknown error during token generation')
            technical_error = result.get('technical_error', '')
            note = result.get('note', '')
            
            return f"""❌ Token generation failed: {error_msg}

{note}

🔧 **Technical Details**: {technical_error}""" if technical_error else f"❌ Token generation failed: {error_msg}"
            
    except Exception as e:
        logger.error(f"OAuth token generation failed: {e}")
        return f"❌ Error generating OAuth token: {str(e)}"


@tool  
def oauth_list_configurations() -> str:
    """List all available OAuth configurations in the database.
    
    Returns:
        Formatted list of OAuth configurations with completeness status
    """
    try:
        result_json = list_oauth_configurations_raw()
        result = json.loads(result_json)
        
        if not result.get('success'):
            return f"❌ Error: {result.get('error', 'Unknown error')}"
        
        message = result.get('message', '')
        note = result.get('note', '')
        
        return f"""📋 **OAuth Configurations**

{message}

💡 **Tip**: {note}

Use `oauth_validate_setup('EVA', 'STA', 'RO')` to check a specific configuration."""
        
    except Exception as e:
        logger.error(f"Error listing OAuth configurations: {e}")
        return f"❌ Error listing OAuth configurations: {str(e)}"


@tool
def oauth_validate_setup(app_code: str, env_code: str, country_code: str) -> str:
    """Validate OAuth setup for a specific application/environment/country combination.
    
    Args:
        app_code: Application code (e.g., 'swile-app', 'pluxee-appweb', 'EVA')
        env_code: Environment code (STA, DEV, PROD)
        country_code: Country code (FR, ES, BR, RO, etc.)
        
    Returns:
        Detailed validation report of OAuth configuration
    """
    try:
        result_json = validate_oauth_setup_raw(app_code, env_code, country_code)
        result = json.loads(result_json)
        
        if not result.get('success'):
            return f"❌ Error: {result.get('error', 'Unknown error')}"
        
        is_valid = result.get('is_valid', False)
        missing = result.get('missing_components', [])
        components = result.get('components', {})
        
        status = "✅ VALID" if is_valid else "❌ INVALID"
        
        output = [
            f"🔍 **OAuth Configuration Validation**",
            f"📱 **App**: {app_code} ({components.get('mapping', {}).get('app_name', 'Unknown')})",
            f"🌐 **Environment**: {env_code} ({components.get('mapping', {}).get('env_name', 'Unknown')})",
            f"🌍 **Country**: {country_code} ({components.get('mapping', {}).get('country_name', 'Unknown')})",
            "",
            f"📊 **Status**: {status}",
        ]
        
        if missing:
            output.append(f"⚠️ **Missing Components**: {', '.join(missing)}")
        
        output.append("\n🔧 **Component Details**:")
        
        # Mapping details
        mapping = components.get('mapping')
        if mapping and mapping.get('mapping_id'):
            output.append(f"✅ **Mapping**: ID {mapping.get('mapping_id')} - {mapping.get('app_name')}/{mapping.get('env_name')}/{mapping.get('country_name')}")
        else:
            output.append("❌ **Mapping**: Not found")
        
        # User details
        user = components.get('user')
        if user:
            output.append(f"✅ **OAuth User**: {user.get('email', 'No email')} (ID: {user.get('id')})")
        else:
            output.append("❌ **OAuth User**: Not configured")
        
        # JWK details
        jwk = components.get('jwk')
        if jwk:
            output.append(f"✅ **JWK**: Key ID {jwk.get('key_id', 'No key_id')} (ID: {jwk.get('id')})")
        else:
            output.append("❌ **JWK**: Not configured")
        
        # Client details
        client = components.get('client')
        if client:
            output.append(f"✅ **OAuth Client**: {client.get('client_id', 'No client_id')} (ID: {client.get('id')})")
        else:
            output.append("❌ **OAuth Client**: Not configured")
        
        if is_valid:
            output.append("\n🎉 **Ready for token generation!**")
        else:
            output.append(f"\n⚠️ **Action Required**: Configure missing components: {', '.join(missing)}")
        
        return "\n".join(output)
        
    except Exception as e:
        logger.error(f"Error validating OAuth setup: {e}")
        return f"❌ Error validating OAuth setup: {str(e)}"


# Export the tools for registration
__all__ = [
    'oauth_generate_token',
    'oauth_list_configurations', 
    'oauth_validate_setup',
    'generate_oauth_token_raw',
    'list_oauth_configurations_raw',
    'validate_oauth_setup_raw'
]

# ---------------------------------------------------------------------------
# Backwards compatibility aliases
# The ToolsManager expects names without the `oauth_` prefix (generate_oauth_token,
# list_oauth_configurations, validate_oauth_setup). We expose lightweight aliases
# so existing imports continue working without changing the manager or other code.
# ---------------------------------------------------------------------------

# Only create aliases if they don't already exist (defensive, idempotent)
try:
    generate_oauth_token  # type: ignore  # noqa: F821
except NameError:  # pragma: no cover - simple compatibility shim
    generate_oauth_token = oauth_generate_token  # type: ignore

try:
    list_oauth_configurations  # type: ignore  # noqa: F821
except NameError:  # pragma: no cover
    list_oauth_configurations = oauth_list_configurations  # type: ignore

try:
    validate_oauth_setup  # type: ignore  # noqa: F821
except NameError:  # pragma: no cover
    validate_oauth_setup = oauth_validate_setup  # type: ignore

# Extend exported symbols with legacy names
__all__.extend([
    'generate_oauth_token',
    'list_oauth_configurations',
    'validate_oauth_setup'
])
