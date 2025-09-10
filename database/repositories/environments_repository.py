"""
Environments Repository - Repository implementation for Environments model

Repositorio para gestión de ambientes empresariales:
- Gestión de ambientes de desarrollo/staging/producción
- Consultas por estado y tipo
- Validaciones de negocio
"""
from typing import List, Optional
from sqlmodel import Session, select
from datetime import datetime, timezone

from .base import BaseRepository
from .exceptions import EntityNotFoundError, DuplicateEntityError
from ..models.environments import Environments


class EnvironmentsRepository(BaseRepository[Environments]):
    """
    Repository for Environments operations
    
    Provides specialized queries for environment management including:
    - Finding environments by code
    - Production vs non-production filtering
    - Active environment queries
    - Environment validation
    """
    
    def __init__(self, session: Session):
        super().__init__(session, Environments)
    
    def get_by_code(self, env_code: str) -> Optional[Environments]:
        """Find environment by unique environment code"""
        statement = select(Environments).where(Environments.env_code == env_code.upper())
        return self.session.exec(statement).first()
    
    def get_active_environments(self) -> List[Environments]:
        """Get all active environments"""
        statement = select(Environments).where(Environments.is_active == True)
        result = self.session.exec(statement).all()
        return list(result)
    
    def get_production_environments(self) -> List[Environments]:
        """Get production environments"""
        statement = select(Environments).where(
            Environments.is_production == True,
            Environments.is_active == True
        )
        result = self.session.exec(statement).all()
        return list(result)
    
    def get_non_production_environments(self) -> List[Environments]:
        """Get non-production environments (dev, staging, UAT, etc.)"""
        statement = select(Environments).where(
            Environments.is_production == False,
            Environments.is_active == True
        )
        result = self.session.exec(statement).all()
        return list(result)
    
    def exists_by_code(self, env_code: str) -> bool:
        """Check if an environment exists with the given code"""
        statement = select(Environments.id).where(Environments.env_code == env_code.upper())
        result = self.session.exec(statement).first()
        return result is not None
    
    def create_environment(self, 
                          env_name: str,
                          env_code: str,
                          description: Optional[str] = None,
                          is_production: bool = False,
                          url_pattern: Optional[str] = None) -> Environments:
        """Create a new environment with validation"""
        
        # Normalize code
        env_code = env_code.upper()
        
        # Validation
        if self.exists_by_code(env_code):
            raise DuplicateEntityError("Environments", "env_code", env_code)
        
        environment = Environments(
            env_name=env_name,
            env_code=env_code,
            description=description,
            is_production=is_production,
            url_pattern=url_pattern,
            is_active=True
        )
        
        return self.save(environment)
    
    def update_environment_status(self, env_code: str, is_active: bool) -> Optional[Environments]:
        """Update environment active status"""
        environment = self.get_by_code(env_code)
        if not environment:
            return None
        
        environment.is_active = is_active
        environment.updated_at = datetime.now(timezone.utc)
        return self.save(environment)
    
    def promote_to_production(self, env_code: str) -> Optional[Environments]:
        """Promote environment to production status"""
        environment = self.get_by_code(env_code)
        if not environment:
            return None
        
        environment.is_production = True
        environment.updated_at = datetime.now(timezone.utc)
        return self.save(environment)
    
    def get_environments_summary(self) -> dict:
        """Get summary statistics for environments"""
        from sqlalchemy import func, text
        
        total_statement = select(func.count(text("1"))).select_from(Environments)
        active_statement = select(func.count(text("1"))).select_from(Environments).where(Environments.is_active == True)
        production_statement = select(func.count(text("1"))).select_from(Environments).where(
            Environments.is_production == True, 
            Environments.is_active == True
        )
        
        total = self.session.exec(total_statement).one()
        active = self.session.exec(active_statement).one()
        production = self.session.exec(production_statement).one()
        
        return {
            "total_environments": total,
            "active_environments": active,
            "inactive_environments": total - active,
            "production_environments": production,
            "non_production_environments": active - production
        }
    
    def search_by_name(self, name_pattern: str) -> List[Environments]:
        """Search environments by name pattern (case-insensitive)"""
        from sqlalchemy import func
        
        statement = select(Environments).where(
            func.lower(Environments.env_name).contains(func.lower(name_pattern))
        )
        result = self.session.exec(statement).all()
        return list(result)
    
    def get_environment_types(self) -> dict:
        """Get count of environments by type (production vs non-production)"""
        environments = self.get_active_environments()
        
        production_count = sum(1 for env in environments if env.is_production)
        non_production_count = len(environments) - production_count
        
        return {
            "production": production_count,
            "non_production": non_production_count,
            "total_active": len(environments)
        }
