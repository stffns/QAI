"""
Apps Repository - Repository implementation for Apps Master
"""
from typing import List, Optional, Sequence
from sqlmodel import Session, select
from sqlalchemy import and_, func

from .base import BaseRepository
from .exceptions import EntityNotFoundError, EntityAlreadyExistsError
from ..models.apps import Apps

class AppsRepository(BaseRepository[Apps]):
    """
    Repository for Apps Master operations
    
    Provides specialized queries for application management including:
    - Finding apps by code
    - Filtering by status
    - Country availability queries
    - Regional statistics
    """
    
    def __init__(self, session: Session):
        super().__init__(session, Apps)
    
    def get_by_code(self, app_code: str) -> Optional[Apps]:
        """
        Find application by unique app code
        
        Args:
            app_code: Unique application code
            
        Returns:
            Apps instance if found, None otherwise
        """
        try:
            statement = select(Apps).where(Apps.app_code == app_code)
            result = self.session.exec(statement).first()
            return result
        except Exception as e:
            raise EntityNotFoundError(f"App with code '{app_code}' not found") from e
    
    def get_active_apps(self) -> List[Apps]:
        """
        Get all active applications
        
        Returns:
            List of active Apps instances
        """
        statement = select(Apps).where(Apps.is_active == True)
        result = self.session.exec(statement).all()
        return list(result)
    
    def search_by_name(self, name_pattern: str) -> List[Apps]:
        """
        Search applications by name pattern (case-insensitive)
        
        Args:
            name_pattern: Pattern to search for in app names
            
        Returns:
            List of matching Apps instances
        """
        statement = select(Apps).where(
            Apps.app_name.ilike(f"%{name_pattern}%")
        )
        result = self.session.exec(statement).all()
        return list(result)
    
    def get_apps_by_description_keyword(self, keyword: str) -> List[Apps]:
        """
        Find applications containing a keyword in their description
        
        Args:
            keyword: Keyword to search for
            
        Returns:
            List of matching Apps instances
        """
        statement = select(Apps).where(
            and_(
                Apps.description.ilike(f"%{keyword}%"),
                Apps.is_active == True
            )
        )
        result = self.session.exec(statement).all()
        return list(result)
    
    def count_active_apps(self) -> int:
        """
        Count total number of active applications
        
        Returns:
            Number of active applications
        """
        statement = select(func.count(Apps.id)).where(Apps.is_active == True)
        result = self.session.exec(statement).one()
        return result
    
    def exists_by_code(self, app_code: str) -> bool:
        """
        Check if an application exists with the given code
        
        Args:
            app_code: Application code to check
            
        Returns:
            True if application exists
        """
        statement = select(Apps.id).where(Apps.app_code == app_code)
        result = self.session.exec(statement).first()
        return result is not None
    
    def create_app(self, app_code: str, app_name: str, description: Optional[str] = None,
                   base_url_template: Optional[str] = None) -> Apps:
        """
        Create a new application with validation
        
        Args:
            app_code: Unique application code
            app_name: Display name
            description: Optional description
            base_url_template: Optional URL template
            
        Returns:
            Created Apps instance
            
        Raises:
            EntityAlreadyExistsError: If app code already exists
        """
        if self.exists_by_code(app_code):
            raise EntityAlreadyExistsError(f"Application with code '{app_code}' already exists")
        
        app = Apps(
            app_code=app_code,
            app_name=app_name,
            description=description,
            base_url_template=base_url_template
        )
        
        return self.save(app)
    
    def deactivate_app(self, app_code: str) -> bool:
        """
        Deactivate an application by setting is_active = False
        
        Args:
            app_code: Application code to deactivate
            
        Returns:
            True if app was deactivated, False if not found
        """
        app = self.get_by_code(app_code)
        if not app:
            return False
        
        app.is_active = False
        self.save(app)
        return True
    
    def reactivate_app(self, app_code: str) -> bool:
        """
        Reactivate an application by setting is_active = True
        
        Args:
            app_code: Application code to reactivate
            
        Returns:
            True if app was reactivated, False if not found
        """
        app = self.get_by_code(app_code)
        if not app:
            return False
        
        app.is_active = True
        self.save(app)
        return True
    
    def update_app_description(self, app_code: str, description: str) -> Optional[Apps]:
        """
        Update application description
        
        Args:
            app_code: Application code
            description: New description
            
        Returns:
            Updated Apps instance if found, None otherwise
        """
        app = self.get_by_code(app_code)
        if not app:
            return None
        
        app.description = description
        return self.save(app)
    
    def get_apps_with_url_template(self) -> List[Apps]:
        """
        Get applications that have URL templates configured
        
        Returns:
            List of Apps instances with URL templates
        """
        statement = select(Apps).where(
            and_(
                Apps.base_url_template.isnot(None),
                Apps.is_active == True
            )
        )
        result = self.session.exec(statement).all()
        return list(result)
    
    def get_apps_summary(self) -> dict:
        """
        Get summary statistics for applications
        
        Returns:
            Dictionary with app statistics
        """
        total_statement = select(func.count(Apps.id))
        active_statement = select(func.count(Apps.id)).where(Apps.is_active == True)
        with_urls_statement = select(func.count(Apps.id)).where(
            and_(
                Apps.base_url_template.isnot(None),
                Apps.is_active == True
            )
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
