"""
OAuth Repository - Repository implementation for OAuth models

Repositorio unificado que sigue patrón SOLID del proyecto QAI.
Combina funcionalidades CRUD estándar con operaciones OAuth específicas.

Uso:
    with uow_factory.create_scope() as uow:
        oauth_config = uow.oauth.get_complete_config("EVA", "STA", "RO")
        user = uow.oauth.users.get_by_mapping_id(mapping_id)
"""

import json
from typing import List, Optional, Dict, Any
from sqlmodel import Session, select, and_
from datetime import datetime

from .base import BaseRepository
from .exceptions import EntityNotFoundError, DuplicateEntityError
from ..models.oauth import (
    OAuthUsers, OAuthUserCreate, OAuthUserUpdate,
    OAuthJWKs, OAuthJWKCreate, OAuthJWKUpdate, 
    OAuthAppClients, OAuthAppClientCreate, OAuthAppClientUpdate
)


class OAuthUsersRepository(BaseRepository[OAuthUsers]):
    """Repositorio para usuarios OAuth"""
    
    def __init__(self, session: Session):
        super().__init__(session, OAuthUsers)
    
    def get_by_mapping_id(self, mapping_id: int) -> Optional[OAuthUsers]:
        """Obtener usuario OAuth por mapping_id"""
        statement = select(OAuthUsers).where(
            and_(
                OAuthUsers.mapping_id == mapping_id,
                OAuthUsers.is_active == True
            )
        )
        return self.session.exec(statement).first()
    
    def get_by_email(self, email: str) -> Optional[OAuthUsers]:
        """Obtener usuario OAuth por email"""
        statement = select(OAuthUsers).where(
            and_(
                OAuthUsers.email == email,
                OAuthUsers.is_active == True
            )
        )
        return self.session.exec(statement).first()
    
    def get_by_realm(self, realm: str) -> List[OAuthUsers]:
        """Obtener usuarios OAuth por realm (país)"""
        statement = select(OAuthUsers).where(
            and_(
                OAuthUsers.realm == realm.lower(),
                OAuthUsers.is_active == True
            )
        )
        return list(self.session.exec(statement).all())
    
    def create_oauth_user(self, user_data: OAuthUserCreate) -> OAuthUsers:
        """Crear usuario OAuth con validaciones"""
        
        # Verificar mapping_id único
        existing = self.get_by_mapping_id(user_data.mapping_id)
        if existing:
            raise DuplicateEntityError("OAuthUsers", "mapping_id", str(user_data.mapping_id))
        
        # Verificar email único
        existing_email = self.get_by_email(user_data.email)
        if existing_email:
            raise DuplicateEntityError("OAuthUsers", "email", user_data.email)
        
        # Crear entidad OAuth
        oauth_user = OAuthUsers(**user_data.model_dump())
        return self.save(oauth_user)
    
    def update_oauth_user(self, user_id: int, user_data: OAuthUserUpdate) -> OAuthUsers:
        """Actualizar usuario OAuth"""
        user = self.get_by_id(user_id)
        if not user:
            raise EntityNotFoundError("OAuthUsers", str(user_id))
        
        # Actualizar campos
        update_dict = user_data.model_dump(exclude_unset=True)
        update_dict['updated_at'] = datetime.utcnow()
        
        for key, value in update_dict.items():
            if hasattr(user, key):
                setattr(user, key, value)
        
        return self.save(user)


class OAuthJWKsRepository(BaseRepository[OAuthJWKs]):
    """Repositorio para claves JWK OAuth"""
    
    def __init__(self, session: Session):
        super().__init__(session, OAuthJWKs)
    
    def get_by_environment_id(self, environment_id: int) -> Optional[OAuthJWKs]:
        """Obtener JWK activa por environment_id"""
        statement = select(OAuthJWKs).where(
            and_(
                OAuthJWKs.environment_id == environment_id,
                OAuthJWKs.is_active == True
            )
        )
        return self.session.exec(statement).first()
    
    def get_by_key_id(self, key_id: str) -> Optional[OAuthJWKs]:
        """Obtener JWK por key_id único"""
        statement = select(OAuthJWKs).where(
            and_(
                OAuthJWKs.key_id == key_id,
                OAuthJWKs.is_active == True
            )
        )
        return self.session.exec(statement).first()
    
    def get_all_active(self) -> List[OAuthJWKs]:
        """Obtener todas las JWK activas"""
        statement = select(OAuthJWKs).where(OAuthJWKs.is_active == True)
        return list(self.session.exec(statement).all())
    
    def create_oauth_jwk(self, jwk_data: OAuthJWKCreate) -> OAuthJWKs:
        """Crear JWK con validaciones"""
        
        # Verificar key_id único
        existing = self.get_by_key_id(jwk_data.key_id)
        if existing:
            raise DuplicateEntityError("OAuthJWKs", "key_id", jwk_data.key_id)
        
        # Crear entidad JWK
        oauth_jwk = OAuthJWKs(**jwk_data.model_dump())
        return self.save(oauth_jwk)
    
    def update_oauth_jwk(self, jwk_id: int, jwk_data: OAuthJWKUpdate) -> OAuthJWKs:
        """Actualizar JWK"""
        jwk = self.get_by_id(jwk_id)
        if not jwk:
            raise EntityNotFoundError("OAuthJWKs", str(jwk_id))
        
        # Actualizar campos
        update_dict = jwk_data.model_dump(exclude_unset=True)
        update_dict['updated_at'] = datetime.utcnow()
        
        for key, value in update_dict.items():
            if hasattr(jwk, key):
                setattr(jwk, key, value)
        
        return self.save(jwk)
    
    def deactivate_environment_jwks(self, environment_id: int) -> int:
        """Desactivar todas las JWK de un ambiente"""
        statement = select(OAuthJWKs).where(
            and_(
                OAuthJWKs.environment_id == environment_id,
                OAuthJWKs.is_active == True
            )
        )
        
        jwks = self.session.exec(statement).all()
        count = 0
        
        for jwk in jwks:
            jwk.is_active = False
            jwk.updated_at = datetime.utcnow()
            self.save(jwk, commit=False)  # No commit individual
            count += 1
        
        return count


class OAuthAppClientsRepository(BaseRepository[OAuthAppClients]):
    """Repositorio para clientes OAuth de aplicaciones"""
    
    def __init__(self, session: Session):
        super().__init__(session, OAuthAppClients)
    
    def get_by_mapping_id(self, mapping_id: int) -> Optional[OAuthAppClients]:
        """Obtener cliente OAuth por mapping_id"""
        statement = select(OAuthAppClients).where(
            and_(
                OAuthAppClients.mapping_id == mapping_id,
                OAuthAppClients.is_active == True
            )
        )
        return self.session.exec(statement).first()
    
    def get_by_client_id(self, client_id: str) -> Optional[OAuthAppClients]:
        """Obtener cliente OAuth por client_id único"""
        statement = select(OAuthAppClients).where(
            and_(
                OAuthAppClients.client_id == client_id,
                OAuthAppClients.is_active == True
            )
        )
        return self.session.exec(statement).first()
    
    def get_all_active(self) -> List[OAuthAppClients]:
        """Obtener todos los clientes OAuth activos"""
        statement = select(OAuthAppClients).where(OAuthAppClients.is_active == True)
        return list(self.session.exec(statement).all())
    
    def create_oauth_client(self, client_data: OAuthAppClientCreate) -> OAuthAppClients:
        """Crear cliente OAuth con validaciones"""
        
        # Verificar mapping_id único
        existing = self.get_by_mapping_id(client_data.mapping_id)
        if existing:
            raise DuplicateEntityError("OAuthAppClients", "mapping_id", str(client_data.mapping_id))
        
        # Verificar client_id único
        existing_client = self.get_by_client_id(client_data.client_id)
        if existing_client:
            raise DuplicateEntityError("OAuthAppClients", "client_id", client_data.client_id)
        
        # Crear entidad OAuth Client
        oauth_client = OAuthAppClients(**client_data.model_dump())
        return self.save(oauth_client)
    
    def update_oauth_client(self, client_id: int, client_data: OAuthAppClientUpdate) -> OAuthAppClients:
        """Actualizar cliente OAuth"""
        client = self.get_by_id(client_id)
        if not client:
            raise EntityNotFoundError("OAuthAppClients", str(client_id))
        
        # Actualizar campos
        update_dict = client_data.model_dump(exclude_unset=True)
        update_dict['updated_at'] = datetime.utcnow()
        
        for key, value in update_dict.items():
            if hasattr(client, key):
                setattr(client, key, value)
        
        return self.save(client)


class OAuthRepository:
    """
    Repositorio OAuth unificado que coordina todas las entidades OAuth
    
    Combina funcionalidades SOLID con operaciones específicas para tokens OAuth.
    Este es el punto de entrada principal para todas las operaciones OAuth.
    """
    
    def __init__(self, session: Session):
        self.session = session
        self.users = OAuthUsersRepository(session)
        self.jwks = OAuthJWKsRepository(session)
        self.app_clients = OAuthAppClientsRepository(session)
    
    def get_complete_oauth_config(self, app_code: str, env_code: str, country_code: str) -> Optional[Dict[str, Any]]:
        """
        Obtener configuración OAuth completa para generar tokens
        
        Enfoque híbrido: usa sqlite3 para query compleja y repositorios para entidades OAuth.
        """
        
        import sqlite3
        from pathlib import Path
        
        # Obtener la configuración usando sqlite3 directo (más confiable para queries complejas)
        db_path = Path("data/qa_intelligence.db")
        if not db_path.exists():
            return None
        
        conn = sqlite3.connect(str(db_path))
        conn.row_factory = sqlite3.Row
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
            
            # Cargar usuario OAuth usando repositorio SQLModel
            user = self.users.get_by_mapping_id(config['mapping_id'])
            config['user'] = user.model_dump() if user else None
            
            # Cargar JWK activa usando repositorio SQLModel
            jwk = self.jwks.get_by_environment_id(config['env_id'])
            config['jwk'] = jwk.model_dump() if jwk else None
            
            # Cargar client OAuth usando repositorio SQLModel
            client = self.app_clients.get_by_mapping_id(config['mapping_id'])
            config['client'] = client.model_dump() if client else None
            
            # Parsear JWK data si existe
            if jwk and jwk.jwk_content and config['jwk']:
                try:
                    config['jwk']['jwk_data'] = json.loads(jwk.jwk_content)
                except json.JSONDecodeError:
                    config['jwk']['jwk_data'] = {}
            
            return config
            
        finally:
            conn.close()
    
    def list_available_oauth_configs(self) -> List[Dict[str, Any]]:
        """Listar todas las configuraciones OAuth disponibles usando sqlite3 directo"""
        
        import sqlite3
        from pathlib import Path
        
        db_path = Path("data/qa_intelligence.db")
        if not db_path.exists():
            return []
        
        conn = sqlite3.connect(str(db_path))
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
            SELECT 
                am.app_code, am.app_name,
                em.env_code, em.env_name,
                cm.country_code, cm.country_name,
                aecm.id as mapping_id,
                ou.email as user_email,
                oac.client_id,
                oj.key_id as jwk_key_id,
                CASE 
                    WHEN ou.id IS NOT NULL AND oac.id IS NOT NULL AND oj.id IS NOT NULL 
                    THEN 1 ELSE 0 
                END as is_complete
            FROM app_environment_country_mappings aecm
            JOIN apps_master am ON aecm.application_id = am.id
            JOIN environments_master em ON aecm.environment_id = em.id
            JOIN countries_master cm ON aecm.country_id = cm.id
            LEFT JOIN oauth_users ou ON ou.mapping_id = aecm.id AND ou.is_active = 1
            LEFT JOIN oauth_jwks oj ON oj.environment_id = em.id AND oj.is_active = 1
            LEFT JOIN oauth_app_clients oac ON oac.mapping_id = aecm.id AND oac.is_active = 1
            WHERE am.is_active = 1 AND em.is_active = 1 AND cm.is_active = 1
            ORDER BY am.app_code, em.env_code, cm.country_code
            """)
            
            configs = cursor.fetchall()
            return [dict(config) for config in configs]
            
        finally:
            conn.close()
    
    def validate_oauth_setup(self, mapping_id: int, environment_id: int) -> Dict[str, Any]:
        """
        Validar setup OAuth y reportar componentes faltantes
        """
        
        user = self.users.get_by_mapping_id(mapping_id)
        client = self.app_clients.get_by_mapping_id(mapping_id)
        jwk = self.jwks.get_by_environment_id(environment_id)
        
        missing = []
        if not user:
            missing.append('oauth_user')
        if not client:
            missing.append('oauth_client') 
        if not jwk:
            missing.append('oauth_jwk')
        
        return {
            'is_valid': len(missing) == 0,
            'missing_components': missing,
            'components': {
                'user': user,
                'client': client,
                'jwk': jwk
            }
        }


# Export principal - UN SOLO REPOSITORIO
__all__ = [
    "OAuthRepository",
    "OAuthUsersRepository", 
    "OAuthJWKsRepository",
    "OAuthAppClientsRepository",
]
