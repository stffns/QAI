"""Application Endpoints Repository - Repository pattern implementation"""

from typing import Any, Dict, List, Optional

from sqlalchemy import func, or_
from sqlmodel import Session, select

from ..models.application_endpoints import ApplicationEndpoint
from .base import BaseRepository
from .exceptions import DuplicateEntityError, InvalidEntityError


class ApplicationEndpointRepository(BaseRepository[ApplicationEndpoint]):
    """Repository for Application Endpoints with country-specific support.

    Provides specialized methods for:
    - Global vs country-specific endpoint management
    - Endpoint lookup by app+env+country combination
    - Bulk operations
    - Testing configuration generation
    """

    def __init__(self, session: Session):
        super().__init__(session, ApplicationEndpoint)

    # === CORE CRUD OPERATIONS ===

    def create_endpoint(
        self,
        application_id: int,
        environment_id: int,
        endpoint_name: str,
        endpoint_url: str,
        http_method: str,
        country_id: Optional[int] = None,
        endpoint_type: Optional[str] = None,
        description: Optional[str] = None,
        body: Optional[Dict[str, Any]] = None,
        is_active: bool = True,
    ) -> ApplicationEndpoint:
        """Create a new application endpoint, ensuring uniqueness per combination."""
        existing = self.get_by_combination(
            application_id=application_id,
            environment_id=environment_id,
            country_id=country_id,
            endpoint_name=endpoint_name,
        )
        if existing:
            combo = f"app={application_id}, env={environment_id}, country={country_id}, name={endpoint_name}"
            raise DuplicateEntityError("ApplicationEndpoint", "combination", combo)

        endpoint = ApplicationEndpoint(
            application_id=application_id,
            environment_id=environment_id,
            country_id=country_id,
            endpoint_name=endpoint_name,
            endpoint_url=endpoint_url,
            http_method=http_method.upper(),
            endpoint_type=endpoint_type,
            description=description,
            body=body,
            is_active=is_active,
        )
        return self.save(endpoint)

    def get_by_combination(
        self,
        application_id: int,
        environment_id: int,
        country_id: Optional[int],
        endpoint_name: str,
    ) -> Optional[ApplicationEndpoint]:
        """Get endpoint by unique combination."""
        query = select(ApplicationEndpoint).where(
            ApplicationEndpoint.application_id == application_id,
            ApplicationEndpoint.environment_id == environment_id,
            ApplicationEndpoint.country_id == country_id,
            ApplicationEndpoint.endpoint_name == endpoint_name,
        )
        return self.session.exec(query).first()

    def get_endpoints_for_app_env(
        self,
        application_id: int,
        environment_id: int,
        country_id: Optional[int] = None,
        include_global: bool = True,
        active_only: bool = True,
    ) -> List[ApplicationEndpoint]:
        """Get all endpoints for an application+environment combination."""
        conditions: List[Any] = [
            ApplicationEndpoint.application_id == application_id,
            ApplicationEndpoint.environment_id == environment_id,
        ]
        if active_only:
            conditions.append(ApplicationEndpoint.is_active == True)

        country_conditions: List[Any] = []
        if country_id is not None:
            country_conditions.append(ApplicationEndpoint.country_id == country_id)
        if include_global:
            country_conditions.append(ApplicationEndpoint.country_id == None)  # noqa: E711
        if country_conditions:
            conditions.append(or_(*country_conditions))

        query = select(ApplicationEndpoint).where(*conditions)
        results = self.session.exec(query).all()
        return list(results)

    def get_global_endpoints(
        self,
        application_id: Optional[int] = None,
        environment_id: Optional[int] = None,
        active_only: bool = True,
    ) -> List[ApplicationEndpoint]:
        """Get all global endpoints (country_id = NULL)."""
        conditions: List[Any] = [ApplicationEndpoint.country_id == None]  # noqa: E711
        if application_id is not None:
            conditions.append(ApplicationEndpoint.application_id == application_id)
        if environment_id is not None:
            conditions.append(ApplicationEndpoint.environment_id == environment_id)
        if active_only:
            conditions.append(ApplicationEndpoint.is_active == True)
        query = select(ApplicationEndpoint).where(*conditions)
        results = self.session.exec(query).all()
        return list(results)

    def get_country_specific_endpoints(
        self,
        country_id: int,
        application_id: Optional[int] = None,
        environment_id: Optional[int] = None,
        active_only: bool = True,
    ) -> List[ApplicationEndpoint]:
        """Get all country-specific endpoints."""
        conditions: List[Any] = [ApplicationEndpoint.country_id == country_id]
        if application_id is not None:
            conditions.append(ApplicationEndpoint.application_id == application_id)
        if environment_id is not None:
            conditions.append(ApplicationEndpoint.environment_id == environment_id)
        if active_only:
            conditions.append(ApplicationEndpoint.is_active == True)
        query = select(ApplicationEndpoint).where(*conditions)
        results = self.session.exec(query).all()
        return list(results)

    # === BULK OPERATIONS ===

    def create_bulk_endpoints(self, endpoints_data: List[Dict[str, Any]]) -> List[ApplicationEndpoint]:
        """Create multiple endpoints in a single transaction."""
        endpoints: List[ApplicationEndpoint] = []
        try:
            for data in endpoints_data:
                endpoint = ApplicationEndpoint(**data)
                self.session.add(endpoint)
                endpoints.append(endpoint)
            self.session.commit()
            for endpoint in endpoints:
                self.session.refresh(endpoint)
            return endpoints
        except Exception as e:
            self.session.rollback()
            msg = str(e)
            if "unique" in msg.lower():
                raise DuplicateEntityError("ApplicationEndpoint", "combination", msg)
            if "check" in msg.lower():
                raise InvalidEntityError("ApplicationEndpoint", [msg])
            raise

    def deactivate_endpoints_by_app_env(
        self,
        application_id: int,
        environment_id: int,
        country_id: Optional[int] = None,
    ) -> int:
        """Deactivate all endpoints for an app+environment combination."""
        endpoints = self.get_endpoints_for_app_env(
            application_id=application_id,
            environment_id=environment_id,
            country_id=country_id,
            include_global=(country_id is None),
            active_only=True,
        )
        count = 0
        for endpoint in endpoints:
            endpoint.mark_as_deprecated()
            count += 1
        self.session.commit()
        return count

    # === SEARCH AND QUERY OPERATIONS ===

    def search_endpoints(
        self,
        search_term: str,
        application_id: Optional[int] = None,
        environment_id: Optional[int] = None,
        country_id: Optional[int] = None,
        active_only: bool = True,
    ) -> List[ApplicationEndpoint]:
        """Search endpoints by name, URL, or description."""
        term = f"%{search_term.lower()}%"
        conditions: List[Any] = [
            or_(
                func.lower(ApplicationEndpoint.endpoint_name).like(term),
                func.lower(ApplicationEndpoint.endpoint_url).like(term),
                func.lower(ApplicationEndpoint.description).like(term),
            )
        ]
        if application_id is not None:
            conditions.append(ApplicationEndpoint.application_id == application_id)
        if environment_id is not None:
            conditions.append(ApplicationEndpoint.environment_id == environment_id)
        if country_id is not None:
            conditions.append(ApplicationEndpoint.country_id == country_id)
        if active_only:
            conditions.append(ApplicationEndpoint.is_active == True)
        query = select(ApplicationEndpoint).where(*conditions)
        results = self.session.exec(query).all()
        return list(results)

    def get_endpoints_by_method(
        self,
        http_method: str,
        application_id: Optional[int] = None,
        active_only: bool = True,
    ) -> List[ApplicationEndpoint]:
        """Get endpoints by HTTP method."""
        conditions: List[Any] = [ApplicationEndpoint.http_method == http_method.upper()]
        if application_id is not None:
            conditions.append(ApplicationEndpoint.application_id == application_id)
        if active_only:
            conditions.append(ApplicationEndpoint.is_active == True)
        query = select(ApplicationEndpoint).where(*conditions)
        results = self.session.exec(query).all()
        return list(results)

    # === TESTING AND CONFIGURATION ===

    def get_test_configuration(
        self,
        application_id: int,
        environment_id: int,
        country_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Get complete test configuration for app+env+country."""
        endpoints = self.get_endpoints_for_app_env(
            application_id=application_id,
            environment_id=environment_id,
            country_id=country_id,
            include_global=True,
            active_only=True,
        )
        config: Dict[str, Any] = {
            "application_id": application_id,
            "environment_id": environment_id,
            "country_id": country_id,
            "endpoints": [],
            "global_endpoints": [],
            "country_specific_endpoints": [],
        }
        for endpoint in endpoints:
            endpoint_config = endpoint.to_test_config()
            config["endpoints"].append(endpoint_config)
            if endpoint.is_global_endpoint:
                config["global_endpoints"].append(endpoint_config)
            else:
                config["country_specific_endpoints"].append(endpoint_config)
        return config

    # === STATISTICS ===

    def get_endpoint_statistics(self) -> Dict[str, Any]:
        """Get statistics about endpoints."""
        all_endpoints = self.get_all()
        stats: Dict[str, Any] = {
            "total_endpoints": len(all_endpoints),
            "active_endpoints": len([e for e in all_endpoints if e.is_active]),
            "inactive_endpoints": len([e for e in all_endpoints if not e.is_active]),
            "global_endpoints": len([e for e in all_endpoints if e.is_global_endpoint]),
            "country_specific_endpoints": len([e for e in all_endpoints if e.is_country_specific]),
            "methods": {},
        }
        for endpoint in all_endpoints:
            method = endpoint.http_method
            stats["methods"][method] = stats["methods"].get(method, 0) + 1
        return stats
