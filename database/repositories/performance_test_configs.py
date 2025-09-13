"""
Performance Test Configs Repository - Simplified Version
=======================================================

Repository implementation for performance test configurations with hierarchy support.
"""

from typing import List, Optional, Dict, Any
from datetime import datetime
from sqlmodel import Session, select, and_, or_

try:
    from database.repositories.base import BaseRepository
    from database.models.performance_test_configs import (
        PerformanceTestConfig,
        PerformanceTestConfigCreate,
        PerformanceTestConfigUpdate,
        PerformanceTestConfigHierarchyQuery
    )
    from database.repositories.exceptions import (
        EntityNotFoundError,
        InvalidEntityError,
        DuplicateEntityError
    )
except ImportError:
    import sys
    import os
    sys.path.append(os.path.join(os.path.dirname(__file__), "..", ".."))
    from database.repositories.base import BaseRepository
    from database.models.performance_test_configs import (
        PerformanceTestConfig,
        PerformanceTestConfigCreate, 
        PerformanceTestConfigUpdate,
        PerformanceTestConfigHierarchyQuery
    )
    from database.repositories.exceptions import (
        EntityNotFoundError,
        InvalidEntityError,
        DuplicateEntityError
    )


class PerformanceTestConfigRepository(BaseRepository[PerformanceTestConfig]):
    """Repository for performance test configurations with hierarchy support."""
    
    def __init__(self, session: Session):
        super().__init__(session, PerformanceTestConfig)

    def find_by_hierarchy(
        self, 
        application_id: int,
        environment_id: int,
        country_id: Optional[int] = None,
        endpoint_pattern: Optional[str] = None,
        test_type: Optional[str] = None,
        include_templates: bool = False
    ) -> Optional[PerformanceTestConfig]:
        """
        Find best matching configuration using hierarchy resolution.
        
        Priority order:
        1. ENDPOINT (specificity_level=1) - exact endpoint + country + env + app
        2. COUNTRY_ENV_APP (specificity_level=2) - country + env + app
        3. ENV_APP (specificity_level=3) - env + app
        4. APP_GENERAL (specificity_level=4) - app only
        """
        stmt = (
            select(PerformanceTestConfig)
            .where(
                and_(
                    PerformanceTestConfig.application_id == application_id,
                    PerformanceTestConfig.environment_id == environment_id,
                    PerformanceTestConfig.is_active == True
                )
            )
        )
        
        # Add optional filters
        if country_id is not None:
            stmt = stmt.where(
                or_(
                    PerformanceTestConfig.country_id == country_id,
                    PerformanceTestConfig.country_id == None
                )
            )
        else:
            stmt = stmt.where(PerformanceTestConfig.country_id == None)
        
        if endpoint_pattern:
            stmt = stmt.where(
                or_(
                    PerformanceTestConfig.endpoint_pattern == endpoint_pattern,
                    PerformanceTestConfig.endpoint_pattern == None
                )
            )
        
        if test_type:
            stmt = stmt.where(PerformanceTestConfig.test_type == test_type)
        
        if not include_templates:
            stmt = stmt.where(PerformanceTestConfig.is_template == False)
        
        # Order by hierarchy priority (lowest number = highest priority)
        results = list(self.session.exec(stmt).all())
        
        # Sort by specificity_level and hierarchy_priority
        results.sort(key=lambda x: (x.specificity_level, x.hierarchy_priority))
        
        return results[0] if results else None

    def find_by_scope(self, scope: str, active_only: bool = True) -> List[PerformanceTestConfig]:
        """Find configurations by scope."""
        stmt = select(PerformanceTestConfig).where(PerformanceTestConfig.config_scope == scope)
        
        if active_only:
            stmt = stmt.where(PerformanceTestConfig.is_active == True)
        
        results = list(self.session.exec(stmt).all())
        results.sort(key=lambda x: x.hierarchy_priority)
        
        return results

    def find_templates(self, test_type: Optional[str] = None) -> List[PerformanceTestConfig]:
        """Find template configurations."""
        stmt = (
            select(PerformanceTestConfig)
            .where(
                and_(
                    PerformanceTestConfig.is_template == True,
                    PerformanceTestConfig.is_active == True
                )
            )
        )
        
        if test_type:
            stmt = stmt.where(PerformanceTestConfig.test_type == test_type)
        
        results = list(self.session.exec(stmt).all())
        results.sort(key=lambda x: x.config_name)
        
        return results

    def find_by_application(self, application_id: int, active_only: bool = True) -> List[PerformanceTestConfig]:
        """Find configurations by application."""
        stmt = select(PerformanceTestConfig).where(PerformanceTestConfig.application_id == application_id)
        
        if active_only:
            stmt = stmt.where(PerformanceTestConfig.is_active == True)
        
        results = list(self.session.exec(stmt).all())
        results.sort(key=lambda x: (x.specificity_level, x.hierarchy_priority))
        
        return results

    def find_pending_validation(self) -> List[PerformanceTestConfig]:
        """Find configurations pending validation."""
        stmt = (
            select(PerformanceTestConfig)
            .where(
                and_(
                    PerformanceTestConfig.validation_status == "PENDING",
                    PerformanceTestConfig.is_active == True
                )
            )
        )
        
        results = list(self.session.exec(stmt).all())
        results.sort(key=lambda x: x.created_at)
        
        return results

    def update_validation_status(
        self, 
        config_id: int, 
        status: str, 
        validated_by: Optional[str] = None
    ) -> PerformanceTestConfig:
        """Update validation status of a configuration."""
        config = self.get_by_id(config_id)
        if not config:
            raise EntityNotFoundError("PerformanceTestConfig", str(config_id))
        
        config.validation_status = status
        config.last_validated_at = datetime.utcnow()
        if validated_by:
            config.updated_by = validated_by
        config.updated_at = datetime.utcnow()
        
        self.session.add(config)
        self.session.commit()
        self.session.refresh(config)
        
        return config

    def create_from_template(
        self, 
        template_id: int, 
        create_data: PerformanceTestConfigCreate,
        created_by: Optional[str] = None
    ) -> PerformanceTestConfig:
        """Create a new configuration from a template."""
        template = self.get_by_id(template_id)
        if not template:
            raise EntityNotFoundError("PerformanceTestConfig", str(template_id))
        
        if not template.is_template:
            raise InvalidEntityError("PerformanceTestConfig", ["Configuration is not a template"])
        
        # Create new config based on template
        config_dict = create_data.model_dump(exclude_unset=True)
        
        # Override with template values for execution parameters
        template_dict = template.model_dump(exclude={'id', 'created_at', 'updated_at'})
        
        # Merge template with new data (new data takes precedence for identity fields)
        for key, value in template_dict.items():
            if key not in config_dict and key not in ['application_id', 'environment_id', 'country_id', 'config_name']:
                config_dict[key] = value
        
        # Ensure it's not marked as template
        config_dict['is_template'] = False
        config_dict['created_by'] = created_by
        
        new_config = PerformanceTestConfig(**config_dict)
        
        try:
            self.session.add(new_config)
            self.session.commit()
            self.session.refresh(new_config)
            return new_config
        except Exception as e:
            self.session.rollback()
            raise DuplicateEntityError("PerformanceTestConfig", "combination", "unique constraint")

    def get_hierarchy_statistics(self) -> Dict[str, Any]:
        """Get statistics about configuration hierarchy."""
        all_configs = self.get_all()
        
        stats = {}
        for config in all_configs:
            scope = config.config_scope
            if scope not in stats:
                stats[scope] = {
                    "total_configs": 0,
                    "active_configs": 0,
                    "template_configs": 0,
                    "test_types": set()
                }
            
            stats[scope]["total_configs"] += 1
            if config.is_active:
                stats[scope]["active_configs"] += 1
            if config.is_template:
                stats[scope]["template_configs"] += 1
            stats[scope]["test_types"].add(config.test_type)
        
        # Convert sets to counts
        for scope_stats in stats.values():
            scope_stats["unique_test_types"] = len(scope_stats["test_types"])
            del scope_stats["test_types"]
        
        return {"hierarchy_levels": stats}

    def find_by_test_type(self, test_type: str, active_only: bool = True) -> List[PerformanceTestConfig]:
        """Find configurations by test type."""
        stmt = select(PerformanceTestConfig).where(PerformanceTestConfig.test_type == test_type)
        
        if active_only:
            stmt = stmt.where(PerformanceTestConfig.is_active == True)
        
        results = list(self.session.exec(stmt).all())
        results.sort(key=lambda x: (x.specificity_level, x.hierarchy_priority))
        
        return results
