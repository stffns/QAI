"""
Data Migration Script for OAuth
Migra los datos hardcoded del código Scala a la base de datos
"""

from __future__ import annotations

import hashlib
from datetime import datetime
from typing import Dict, Any
from sqlmodel import Session, create_engine

try:
    from src.auth.models.oauth_models import (
        OAuthCountry,
        OAuthUser,
        OAuthApplication,
        OAuthJWK,
        OAuthEnvironmentConfig,
        OAuthEnvironment,
        OAuthProduct,
        Gender,
    )
    from database.connection import get_engine
    from src.logging_config import get_logger
except ImportError:
    import sys
    import os
    sys.path.append(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
    from src.auth.models.oauth_models import (
        OAuthCountry,
        OAuthUser,
        OAuthApplication,
        OAuthJWK,
        OAuthEnvironmentConfig,
        OAuthEnvironment,
        OAuthProduct,
        Gender,
    )
    from database.connection import get_engine
    from src.logging_config import get_logger


logger = get_logger("OAuthMigration")


# Datos de países extraídos del código Scala
COUNTRIES_DATA = [
    {"code": "mx", "name": "México", "locale": "es-MX"},
    {"code": "cl", "name": "Chile", "locale": "es-CL"},
    {"code": "co", "name": "Colombia", "locale": "es-CO"},
    {"code": "uy", "name": "Uruguay", "locale": "es-UY"},
    {"code": "pe", "name": "Perú", "locale": "es-PE"},
    {"code": "pa", "name": "Panamá", "locale": "es-PA"},
    {"code": "br", "name": "Brasil", "locale": "pt-BR"},
    {"code": "lu", "name": "Luxemburgo", "locale": "fr-LU"},
    {"code": "tn", "name": "Túnez", "locale": "fr-TN"},
    {"code": "ro", "name": "Rumania", "locale": "ro-RO"},
    {"code": "de", "name": "Alemania", "locale": "de-DE"},
    {"code": "at", "name": "Austria", "locale": "de-AT"},
    {"code": "be", "name": "Bélgica", "locale": "en-BE"},
    {"code": "fr", "name": "Francia", "locale": "fr-FR"},
    {"code": "aq", "name": "Antártida", "locale": "en-US"},  # Usado como país de prueba
]

# Configuraciones de ambiente extraídas del código Scala
ENVIRONMENT_CONFIGS = [
    {
        "environment": OAuthEnvironment.STA,
        "oidc_domain": "connect.sta.pluxee.app",
        "issuer": "https://connect.sta.pluxee.app/op",
    },
    {
        "environment": OAuthEnvironment.UAT,
        "oidc_domain": "connect.uat.pluxee.app",
        "issuer": "https://connect.uat.pluxee.app/op",
    },
]

# JWKs extraídos del código Scala
JWKS_DATA = [
    {
        "environment": OAuthEnvironment.STA,
        "key_id": "SCIK-QA-STA-20210408-47QNY",
        "jwk_content": '{"kty":"RSA","kid":"SCIK-QA-STA-20210408-47QNY","use":"sig","alg":"RS256","n":"mock_n","e":"AQAB"}',  # Mock JWK
    },
    {
        "environment": OAuthEnvironment.UAT,
        "key_id": "SCIK-QA-UAT-20210408-PNCY8",
        "jwk_content": '{"kty":"RSA","kid":"SCIK-QA-UAT-20210408-PNCY8","use":"sig","alg":"RS256","n":"mock_n","e":"AQAB"}',  # Mock JWK
    },
]

# Usuarios extraídos del UserMap.scala
USERS_DATA = [
    # STA Mexico
    {"email": "test.sta.mx11@endtest-mail.io", "given_name": "Lucia", "family_name": "Alamos Lara", "phone_number": "+573219059012", "gender": Gender.FEMALE, "password": "Test12345#", "environment": OAuthEnvironment.STA, "country_code": "mx", "product": OAuthProduct.ONE_APP},
    
    # STA Chile
    {"email": "sodexo.100297329@endtest-mail.io", "given_name": "Lucia", "family_name": "Alamos Lara", "phone_number": "+573219059012", "gender": Gender.FEMALE, "password": "Test12345#", "environment": OAuthEnvironment.STA, "country_code": "cl", "product": OAuthProduct.ONE_APP},
    
    # STA Colombia - multiple variants
    {"email": "colombia.sta@endtest-mail.io", "given_name": "Alejandro", "family_name": "Cabrera", "phone_number": "+573219036969", "gender": Gender.MALE, "password": "Test12345#", "environment": OAuthEnvironment.STA, "country_code": "co", "product": OAuthProduct.ONE_APP},
    {"email": "QAStressTestCO1646@endtest-mail.io", "given_name": "Qatesting", "family_name": "Automation", "phone_number": "+5521968862606", "gender": Gender.MALE, "password": "Test12345#", "environment": OAuthEnvironment.STA, "country_code": "co", "product": OAuthProduct.ONE_APP1},
    {"email": "QAStressTestCO1752@endtest-mail.io", "given_name": "Qatesting", "family_name": "Automation", "phone_number": "+5521968862606", "gender": Gender.MALE, "password": "Test12345#", "environment": OAuthEnvironment.STA, "country_code": "co", "product": OAuthProduct.ONE_APP2},
    {"email": "QAStressTestCO1256@endtest-mail.io", "given_name": "Qatesting", "family_name": "Automation", "phone_number": "+5521968862606", "gender": Gender.MALE, "password": "Test12345#", "environment": OAuthEnvironment.STA, "country_code": "co", "product": OAuthProduct.ONE_APP3},
    {"email": "QAStressTestCO1738@endtest-mail.io", "given_name": "Qatesting", "family_name": "Automation", "phone_number": "+5521968862606", "gender": Gender.MALE, "password": "Test12345#", "environment": OAuthEnvironment.STA, "country_code": "co", "product": OAuthProduct.ONE_APP4},
    
    # STA Uruguay
    {"email": "Uy.sta@endtest-mail.io", "given_name": "Lionel", "family_name": "Messi", "phone_number": "+573114961227", "gender": Gender.FEMALE, "password": "Test12345#", "environment": OAuthEnvironment.STA, "country_code": "uy", "product": OAuthProduct.ONE_APP},
    
    # STA Peru - multiple variants  
    {"email": "sta.peru@endtest-mail.io", "given_name": "Martin", "family_name": "Pruebas", "phone_number": "+51902566821", "gender": Gender.MALE, "password": "Test12345#", "environment": OAuthEnvironment.STA, "country_code": "pe", "product": OAuthProduct.ONE_APP},
    {"email": "QAStressTestpe1752@endtest-mail.io", "given_name": "Qatesting", "family_name": "Automation", "phone_number": "+5521968862606", "gender": Gender.MALE, "password": "Test12345#", "environment": OAuthEnvironment.STA, "country_code": "pe", "product": OAuthProduct.ONE_APP1},
    {"email": "QAStressTestpe1256@endtest-mail.io", "given_name": "Qatesting", "family_name": "Automation", "phone_number": "+5521968862606", "gender": Gender.MALE, "password": "Test12345#", "environment": OAuthEnvironment.STA, "country_code": "pe", "product": OAuthProduct.ONE_APP2},
    {"email": "QAStressTestpe3157@endtest-mail.io", "given_name": "Qatesting", "family_name": "Automation", "phone_number": "+5521968862606", "gender": Gender.MALE, "password": "Test12345#", "environment": OAuthEnvironment.STA, "country_code": "pe", "product": OAuthProduct.ONE_APP3},
    {"email": "QAStressTestpe1408@endtest-mail.io", "given_name": "Qatesting", "family_name": "Automation", "phone_number": "+5521968862606", "gender": Gender.MALE, "password": "Test12345#", "environment": OAuthEnvironment.STA, "country_code": "pe", "product": OAuthProduct.ONE_APP4},
    
    # STA Panama
    {"email": "QA1Testpa0725@endtest-mail.io", "given_name": "Prueba", "family_name": "Test", "phone_number": "+573155453551", "gender": Gender.MALE, "password": "Test12345#", "environment": OAuthEnvironment.STA, "country_code": "pa", "product": OAuthProduct.ONE_APP},
    
    # UAT users
    {"email": "ciam-mix@endtest-mail.io", "given_name": "test", "family_name": "test", "phone_number": "+33663005232", "gender": Gender.FEMALE, "password": "Test12345#", "environment": OAuthEnvironment.UAT, "country_code": "cl", "product": OAuthProduct.ONE_APP},
    {"email": "user.uat.co@endtest-mail.io", "given_name": "test", "family_name": "test", "phone_number": "+33663005232", "gender": Gender.FEMALE, "password": "Test12345#", "environment": OAuthEnvironment.UAT, "country_code": "co", "product": OAuthProduct.ONE_APP},
    
    # M-APP users
    {"email": "register.sta.co@endtest-mail.io", "given_name": "Usuario", "family_name": "Sta", "phone_number": "+50769990981", "gender": Gender.MALE, "password": "Test12345#", "environment": OAuthEnvironment.STA, "country_code": "co", "product": OAuthProduct.M_APP},
    {"email": "creatingnewuserforpanama.sta.pa@endtest-mail.io", "given_name": "Usuario", "family_name": "Panamastauno", "phone_number": "+50769990981", "gender": Gender.MALE, "password": "Test12345#", "environment": OAuthEnvironment.STA, "country_code": "pa", "product": OAuthProduct.M_APP},
    {"email": "merqasta01@endtest-mail.io", "given_name": "Usuario", "family_name": "Panamastauno", "phone_number": "+50769990981", "gender": Gender.MALE, "password": "Test12345#", "environment": OAuthEnvironment.STA, "country_code": "cl", "product": OAuthProduct.M_APP},
    {"email": "anab@tanet.com", "given_name": "Usuario", "family_name": "Panamastauno", "phone_number": "+50769990981", "gender": Gender.MALE, "password": "Test12345#", "environment": OAuthEnvironment.STA, "country_code": "br", "product": OAuthProduct.M_APP},
    
    # EVA users
    {"email": "qa.uat.soco.lu+1@gmail.com", "given_name": "test", "family_name": "test", "phone_number": "+33663005232", "gender": Gender.FEMALE, "password": "Test12345#", "environment": OAuthEnvironment.UAT, "country_code": "lu", "product": OAuthProduct.EVA},
    {"email": "qa.sta.soco+22+06+2021@gmail.com", "given_name": "Sathish", "family_name": "Chinnadurai", "phone_number": "+33663005232", "gender": "Homme", "password": "Test12345#", "environment": OAuthEnvironment.UAT, "country_code": "tn", "product": OAuthProduct.EVA},
    {"email": "qa.uat.soco.ro+4@gmail.com", "given_name": "test", "family_name": "test", "phone_number": "+33617443459", "gender": Gender.MALE, "password": "Test12345#", "environment": OAuthEnvironment.UAT, "country_code": "ro", "product": OAuthProduct.EVA},
]

# Aplicaciones extraídas del ClientIdMap.scala
APPLICATIONS_DATA = [
    # ONE-APP
    {"client_id": "547887ef-6ee7-492d-bad8-1edfd7ba0999", "name": "One App Mexico", "environment": OAuthEnvironment.STA, "country_code": "mx", "product": OAuthProduct.ONE_APP, "callback_url": "http://localhost/oidc/callback", "needs_resource_param": True, "resource_url": "https://api.sta.pluxee.app"},
    {"client_id": "afa77d29-3d61-44fb-947b-af0965f35d5e", "name": "One App Chile", "environment": OAuthEnvironment.STA, "country_code": "cl", "product": OAuthProduct.ONE_APP, "callback_url": "http://localhost/oidc/callback", "needs_resource_param": True, "resource_url": "https://api.sta.pluxee.app"},
    {"client_id": "6836636f-f746-47c5-8259-48c380a6d963", "name": "One App Colombia", "environment": OAuthEnvironment.STA, "country_code": "co", "product": OAuthProduct.ONE_APP, "callback_url": "http://localhost/oidc/callback", "needs_resource_param": True, "resource_url": "https://api.sta.pluxee.app"},
    {"client_id": "09bb93a7-7524-40b9-af45-56cf4362dac6", "name": "One App Uruguay", "environment": OAuthEnvironment.STA, "country_code": "uy", "product": OAuthProduct.ONE_APP, "callback_url": "http://localhost/oidc/callback", "needs_resource_param": True, "resource_url": "https://api.sta.pluxee.app"},
    {"client_id": "7b0dfcf3-adbf-48c3-853e-0ab76142a2b4", "name": "One App Peru", "environment": OAuthEnvironment.STA, "country_code": "pe", "product": OAuthProduct.ONE_APP, "callback_url": "http://localhost/oidc/callback", "needs_resource_param": True, "resource_url": "https://api.sta.pluxee.app"},
    {"client_id": "d478ee6a-000b-4987-ae0e-f700d9c8cfed", "name": "One App Panama", "environment": OAuthEnvironment.STA, "country_code": "pa", "product": OAuthProduct.ONE_APP, "callback_url": "http://localhost/oidc/callback", "needs_resource_param": True, "resource_url": "https://api.sta.pluxee.app"},
    
    # UAT ONE-APP
    {"client_id": "3ed1105d-4651-4d83-9052-4896284a4201", "name": "One App Chile UAT", "environment": OAuthEnvironment.UAT, "country_code": "cl", "product": OAuthProduct.ONE_APP, "callback_url": "http://localhost/oidc/callback", "needs_resource_param": False},
    {"client_id": "2a717089-ad1e-43ff-8450-445754559eaa", "name": "One App Colombia UAT", "environment": OAuthEnvironment.UAT, "country_code": "co", "product": OAuthProduct.ONE_APP, "callback_url": "http://localhost/oidc/callback", "needs_resource_param": False},
    
    # M-APP
    {"client_id": "99a67715-bafe-424b-86a8-9ac281a8a995", "name": "M-App Colombia", "environment": OAuthEnvironment.STA, "country_code": "co", "product": OAuthProduct.M_APP, "callback_url": "http://localhost/oidc/callback", "needs_resource_param": True, "resource_url": "https://api.sta.pluxee.app"},
    {"client_id": "5d840b11-8e78-4947-8f4a-823e1d687bbd", "name": "M-App Panama", "environment": OAuthEnvironment.STA, "country_code": "pa", "product": OAuthProduct.M_APP, "callback_url": "http://localhost/oidc/callback", "needs_resource_param": True, "resource_url": "https://api.sta.pluxee.app"},
    {"client_id": "6d6ea62a-0885-4191-b037-483ea778b69a", "name": "M-App Chile", "environment": OAuthEnvironment.STA, "country_code": "cl", "product": OAuthProduct.M_APP, "callback_url": "http://localhost/oidc/callback", "needs_resource_param": True, "resource_url": "https://api.sta.pluxee.app"},
    {"client_id": "58feae71-14b5-4e25-9e75-bb8ce19eaa2d", "name": "M-App Brasil", "environment": OAuthEnvironment.STA, "country_code": "br", "product": OAuthProduct.M_APP, "callback_url": "http://localhost/oidc/callback", "needs_resource_param": True, "resource_url": "https://api.sta.pluxee.app"},
    
    # EVA
    {"client_id": "47243233-146c-41f8-b306-61e6d0d3fb11", "name": "EVA Luxembourg UAT", "environment": OAuthEnvironment.UAT, "country_code": "lu", "product": OAuthProduct.EVA, "callback_url": "http://localhost/oidc/callback", "needs_resource_param": False},
    {"client_id": "6e8297c6-c221-4909-8228-e7b51462acc5", "name": "EVA Tunisia UAT", "environment": OAuthEnvironment.UAT, "country_code": "tn", "product": OAuthProduct.EVA, "callback_url": "http://localhost/oidc/callback", "needs_resource_param": False},
    {"client_id": "9a2d7f6f-83a6-402e-9c1e-c691f12e71d1", "name": "EVA Romania UAT", "environment": OAuthEnvironment.UAT, "country_code": "ro", "product": OAuthProduct.EVA, "callback_url": "http://localhost/oidc/callback", "needs_resource_param": False},
    {"client_id": "0f2ba049-b2a2-447c-9cff-42eaf38d5717", "name": "EVA Luxembourg STA", "environment": OAuthEnvironment.STA, "country_code": "lu", "product": OAuthProduct.EVA, "callback_url": "http://localhost/oidc/callback", "needs_resource_param": False},
    {"client_id": "13d164db-dcc3-4462-8c42-1970d888cadf", "name": "EVA Tunisia STA", "environment": OAuthEnvironment.STA, "country_code": "tn", "product": OAuthProduct.EVA, "callback_url": "http://localhost/oidc/callback", "needs_resource_param": False},
    {"client_id": "84d70f23-df50-4ed2-9d60-263366326c9d", "name": "EVA Romania STA", "environment": OAuthEnvironment.STA, "country_code": "ro", "product": OAuthProduct.EVA, "callback_url": "http://localhost/oidc/callback", "needs_resource_param": False},
]


def hash_password(password: str) -> str:
    """Hash de password usando SHA256 (en producción usar bcrypt)"""
    return hashlib.sha256(password.encode()).hexdigest()


def migrate_countries(session: Session) -> None:
    """Migra datos de países"""
    logger.info("Migrating countries...")
    
    for country_data in COUNTRIES_DATA:
        existing = session.get(OAuthCountry, {"code": country_data["code"]})
        if not existing:
            country = OAuthCountry(**country_data)
            session.add(country)
            logger.info(f"Added country: {country.name} ({country.code})")
    
    session.commit()


def migrate_environment_configs(session: Session) -> None:
    """Migra configuraciones de ambiente"""
    logger.info("Migrating environment configs...")
    
    for config_data in ENVIRONMENT_CONFIGS:
        existing = session.query(OAuthEnvironmentConfig).filter(
            OAuthEnvironmentConfig.environment == config_data["environment"]
        ).first()
        
        if not existing:
            config = OAuthEnvironmentConfig(**config_data)
            session.add(config)
            logger.info(f"Added environment config: {config.environment}")
    
    session.commit()


def migrate_jwks(session: Session) -> None:
    """Migra claves JWK"""
    logger.info("Migrating JWKs...")
    
    for jwk_data in JWKS_DATA:
        existing = session.query(OAuthJWK).filter(
            OAuthJWK.environment == jwk_data["environment"]
        ).first()
        
        if not existing:
            jwk = OAuthJWK(**jwk_data)
            session.add(jwk)
            logger.info(f"Added JWK for environment: {jwk.environment}")
    
    session.commit()


def migrate_users(session: Session) -> None:
    """Migra usuarios OAuth"""
    logger.info("Migrating OAuth users...")
    
    for user_data in USERS_DATA:
        existing = session.query(OAuthUser).filter(
            OAuthUser.email == user_data["email"]
        ).first()
        
        if not existing:
            # Hash del password
            password = user_data.pop("password")
            user_data["password_hash"] = hash_password(password)
            
            user = OAuthUser(**user_data)
            session.add(user)
            logger.info(f"Added user: {user.email} ({user.environment}/{user.country_code}/{user.product})")
    
    session.commit()


def migrate_applications(session: Session) -> None:
    """Migra aplicaciones OAuth"""
    logger.info("Migrating OAuth applications...")
    
    for app_data in APPLICATIONS_DATA:
        existing = session.query(OAuthApplication).filter(
            OAuthApplication.client_id == app_data["client_id"]
        ).first()
        
        if not existing:
            application = OAuthApplication(**app_data)
            session.add(application)
            logger.info(f"Added application: {application.name} ({application.client_id})")
    
    session.commit()


def run_migration() -> None:
    """Ejecuta la migración completa"""
    logger.info("Starting OAuth data migration...")
    
    engine = get_engine()
    
    # Crear tablas si no existen
    from sqlmodel import SQLModel
    SQLModel.metadata.create_all(engine)
    
    with Session(engine) as session:
        try:
            # Orden de migración respetando dependencias
            migrate_countries(session)
            migrate_environment_configs(session)
            migrate_jwks(session)
            migrate_users(session)
            migrate_applications(session)
            
            logger.info("OAuth data migration completed successfully!")
            
        except Exception as e:
            session.rollback()
            logger.error(f"Migration failed: {e}")
            raise


if __name__ == "__main__":
    run_migration()
