"""
Apps Repository - Repository implementation for Apps model
"""
from typing import List, Optional
from sqlmodel import Session, select, text
from sqlalchemy import func

from .base import BaseRepository
from .exceptions import EntityNotFoundError, DuplicateEntityError
from ..models.apps import Apps

class AppsRepository(BaseRepository[Apps]):
    """
    Repository for Apps operations
    
    Provides specialized queries for application management including:
    - Finding apps by code
    - Filtering by status
    - Country availability queries
    - Regional statistics
    """
    
    def __init__(self, session: Session):
        super().__init__(session, Apps)
    
    def get_by_code(self, app_code: str) -> Optional[Apps]:
        """Find application by unique app code"""
        statement = select(Apps).where(Apps.app_code == app_code)
        return self.session.exec(statement).first()
    
    def get_active_apps(self) -> List[Apps]:
        """Get all active applications"""
        statement = select(Apps).where(Apps.is_active == True)
        result = self.session.exec(statement).all()
        return list(result)
    
    def search_by_name(self, name_pattern: str) -> List[Apps]:
        """Search applications by name pattern (case-insensitive)"""
        # Use SQL text for ILIKE functionality
        statement = select(Apps).where(text(f"app_name ILIKE '%{name_pattern}%'"))
        result = self.session.exec(statement).all()
        return list(result)
    
    def get_apps_by_description_keyword(self, keyword: str) -> List[Apps]:
        """Find applications containing a keyword in their description"""
        statement = select(Apps).where(
            text(f"description ILIKE '%{keyword}%'"),
            Apps.is_active == True
        )
        result = self.session.exec(statement).all()
        return list(result)
    
    def count_active_apps(self) -> int:
        """Count total number of active applications"""
        # Use text("1") for simple counting
        statement = select(func.count(text("1"))).select_from(Apps).where(Apps.is_active == True)
        return self.session.exec(statement).one()
    
    def exists_by_code(self, app_code: str) -> bool:
        """Check if an application exists with the given code"""
        statement = select(Apps.id).where(Apps.app_code == app_code)
        result = self.session.exec(statement).first()
        return result is not None
    
    def create_app(self, app_code: str, app_name: str, 
                   description: Optional[str] = None,
                   base_url_template: Optional[str] = None) -> Apps:
        """Create a new application with validation"""
        if self.exists_by_code(app_code):
            raise DuplicateEntityError("Apps", "app_code", app_code)
        
        app = Apps(
            app_code=app_code,
            app_name=app_name,
            description=description,
            base_url_template=base_url_template
        )
        
        return self.save(app)
    
    def deactivate_app(self, app_code: str) -> bool:
        """Deactivate an application"""
        app = self.get_by_code(app_code)
        if not app:
            return False
        
        app.is_active = False
        self.save(app)
        return True
    
    def reactivate_app(self, app_code: str) -> bool:
        """Reactivate an application"""
        app = self.get_by_code(app_code)
        if not app:
            return False
        
        app.is_active = True
        self.save(app)
        return True
    
    def update_app_description(self, app_code: str, description: str) -> Optional[Apps]:
        """Update application description"""
        app = self.get_by_code(app_code)
        if not app:
            return None
        
        app.description = description
        return self.save(app)
    
    def get_apps_with_url_template(self) -> List[Apps]:
        """Get applications that have URL templates configured"""
        statement = select(Apps).where(
            Apps.base_url_template != None,
            Apps.is_active == True
        )
        result = self.session.exec(statement).all()
        return list(result)
    
    def get_apps_summary(self) -> dict:
        """Get summary statistics for applications"""
        total_statement = select(func.count(text("1"))).select_from(Apps)
        active_statement = select(func.count(text("1"))).select_from(Apps).where(Apps.is_active == True)
        with_urls_statement = select(func.count(text("1"))).select_from(Apps).where(
            Apps.base_url_template != None,
            Apps.is_active == True
        )
        
        total = self.session.exec(total_statement).one()
        active = self.session.exec(active_statement).one()
        with_urls = self.session.exec(with_urls_statement).one()
        
        return {
            "total_apps": total,
            "active_apps": active,
            "inactive_apps": total - active,
            "apps_with_urls": with_urls,
            "coverage_percentage": round((with_urls / active * 100) if active > 0 else 0, 2)
        }
