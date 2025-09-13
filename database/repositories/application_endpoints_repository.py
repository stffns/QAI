"""Application Endpoints Repository - Clean Structure Implementation"""

from typing import Any, Dict, List, Optional

from sqlmodel import Session, select

from ..models.application_endpoints import ApplicationEndpoint
from .base import BaseRepository
from .exceptions import DuplicateEntityError


class ApplicationEndpointRepository(BaseRepository[ApplicationEndpoint]):
    """Repository for Application Endpoints with clean normalized structure."""

    def __init__(self, session: Session):
        super().__init__(session, ApplicationEndpoint)

    # === CLEAN STRUCTURE CRUD OPERATIONS ===

    def create_endpoint(
        self,
        mapping_id: int,
        endpoint_name: str,
        endpoint_url: str,
        http_method: str,
        endpoint_type: Optional[str] = None,
        description: Optional[str] = None,
        body: Optional[str] = None,
        is_active: bool = True,
    ) -> ApplicationEndpoint:
        """Create endpoint with clean structure (only mapping_id FK)."""
        # Check uniqueness
        existing = self.get_by_mapping_and_name(mapping_id, endpoint_name)
        if existing:
            raise DuplicateEntityError("ApplicationEndpoint", "mapping+name", f"{mapping_id}:{endpoint_name}")

        endpoint = ApplicationEndpoint(
            mapping_id=mapping_id,
            endpoint_name=endpoint_name,
            endpoint_url=endpoint_url,
            http_method=http_method,
            endpoint_type=endpoint_type,
            description=description,
            body=body,
            is_active=is_active,
        )

        self.session.add(endpoint)
        return endpoint

    def get_by_mapping_and_name(self, mapping_id: int, endpoint_name: str) -> Optional[ApplicationEndpoint]:
        """Get endpoint by mapping and name (unique constraint)."""
        return self.session.exec(
            select(ApplicationEndpoint).where(
                ApplicationEndpoint.mapping_id == mapping_id,
                ApplicationEndpoint.endpoint_name == endpoint_name
            )
        ).first()

    def get_by_mapping(self, mapping_id: int, active_only: bool = True) -> List[ApplicationEndpoint]:
        """Get all endpoints for a mapping."""
        query = select(ApplicationEndpoint).where(ApplicationEndpoint.mapping_id == mapping_id)
        
        if active_only:
            query = query.where(ApplicationEndpoint.is_active == True)
            
        return list(self.session.exec(query.order_by(ApplicationEndpoint.endpoint_name)))

    def search_endpoints(
        self,
        search_term: Optional[str] = None,
        http_method: Optional[str] = None,
        mapping_id: Optional[int] = None,
        is_active: Optional[bool] = True
    ) -> List[ApplicationEndpoint]:
        """Search endpoints with filters."""
        query = select(ApplicationEndpoint)

        conditions = []
        
        if is_active is not None:
            conditions.append(ApplicationEndpoint.is_active == is_active)
            
        if mapping_id is not None:
            conditions.append(ApplicationEndpoint.mapping_id == mapping_id)
            
        if http_method:
            conditions.append(ApplicationEndpoint.http_method == http_method.upper())

        if search_term:
            # Simple string matching
            search_lower = search_term.lower()
            search_conditions = []
            
            # We'll filter in Python for now to avoid SQLAlchemy type issues
            all_endpoints = list(self.session.exec(
                select(ApplicationEndpoint).where(*conditions) if conditions 
                else select(ApplicationEndpoint)
            ))
            
            filtered = []
            for endpoint in all_endpoints:
                if (search_lower in endpoint.endpoint_name.lower() or
                    search_lower in endpoint.endpoint_url.lower() or
                    (endpoint.description and search_lower in endpoint.description.lower())):
                    filtered.append(endpoint)
            
            return filtered

        if conditions:
            query = query.where(*conditions)

        return list(self.session.exec(query.order_by(ApplicationEndpoint.endpoint_name)))

    def update_endpoint(self, endpoint_id: int, **updates: Any) -> Optional[ApplicationEndpoint]:
        """Update endpoint by ID."""
        endpoint = self.get_by_id(endpoint_id)
        if not endpoint:
            return None

        for field, value in updates.items():
            if hasattr(endpoint, field):
                setattr(endpoint, field, value)

        from datetime import datetime, timezone
        endpoint.updated_at = datetime.now(timezone.utc)
        return endpoint

    def deactivate_endpoint(self, endpoint_id: int) -> bool:
        """Deactivate endpoint (soft delete)."""
        endpoint = self.get_by_id(endpoint_id)
        if not endpoint:
            return False

        endpoint.is_active = False
        from datetime import datetime, timezone
        endpoint.updated_at = datetime.now(timezone.utc)
        return True

    # === BULK OPERATIONS ===

    def bulk_create_endpoints(self, endpoints_data: List[Dict[str, Any]]) -> List[ApplicationEndpoint]:
        """Bulk create endpoints."""
        endpoints = []
        
        for data in endpoints_data:
            # Check required fields
            if not all(field in data for field in ['mapping_id', 'endpoint_name', 'endpoint_url', 'http_method']):
                continue

            # Skip duplicates
            if self.get_by_mapping_and_name(data['mapping_id'], data['endpoint_name']):
                continue

            endpoint = ApplicationEndpoint(**data)
            endpoints.append(endpoint)

        self.session.add_all(endpoints)
        return endpoints

    def get_endpoint_count(self) -> int:
        """Get total endpoint count."""
        return len(list(self.session.exec(select(ApplicationEndpoint))))

    def get_active_endpoint_count(self) -> int:
        """Get active endpoint count."""
        return len(list(self.session.exec(
            select(ApplicationEndpoint).where(ApplicationEndpoint.is_active == True)
        )))

    # === COMPATIBILITY METHODS ===

    def get_endpoints_for_app_env(
        self,
        application_id: int,
        environment_id: int,
        country_id: int,
        include_global: bool = True,
        active_only: bool = True
    ) -> List[ApplicationEndpoint]:
        """Get endpoints for app+env+country combination (legacy method)."""
        return self.get_by_app_env_country_via_mapping(application_id, environment_id, country_id)

    def get_by_app_env_country_via_mapping(
        self, 
        application_id: int, 
        environment_id: int, 
        country_id: int
    ) -> List[ApplicationEndpoint]:
        """Get endpoints by app+env+country through mapping lookup (for backwards compatibility)."""
        from ..models.app_environment_country_mappings import AppEnvironmentCountryMapping
        
        # First find the mapping
        mapping = self.session.exec(
            select(AppEnvironmentCountryMapping).where(
                AppEnvironmentCountryMapping.application_id == application_id,
                AppEnvironmentCountryMapping.environment_id == environment_id,
                AppEnvironmentCountryMapping.country_id == country_id
            )
        ).first()
        
        if not mapping or not mapping.id:
            return []
            
        return self.get_by_mapping(mapping.id)