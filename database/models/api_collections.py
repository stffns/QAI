"""API Collections models (Postman import integration).

Focused minimal schema for Phase 1 import pipeline.
Note: ApiRequest model has been removed - functionality moved to ApplicationEndpoint.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional, Dict, Any
from sqlmodel import SQLModel, Field, Column
from sqlalchemy import JSON as SQLAlchemyJSON, Index


class ApiCollection(SQLModel, table=True):
    __tablename__ = "api_collections"  # type: ignore[assignment]

    id: Optional[int] = Field(default=None, primary_key=True)
    mapping_id: Optional[int] = Field(
        default=None,
        foreign_key="app_environment_country_mappings.id",
        description="Optional mapping reference (app+env+country context)"
    )
    name: str = Field(max_length=255, description="Collection name from Postman")
    postman_id: Optional[str] = Field(
        default=None, max_length=100, description="Original Postman collection ID (if present)"
    )
    content_hash: str = Field(max_length=64, description="SHA256 hash of collection content")
    environment_snapshot: Optional[Dict[str, Any]] = Field(
        default=None,
        sa_column=Column(SQLAlchemyJSON),
        description="Variable environment at import time"
    )
    import_meta: Optional[Dict[str, Any]] = Field(
        default=None,
        sa_column=Column(SQLAlchemyJSON),
        description="Import metadata (file path, version, etc.)"
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Import timestamp"
    )

    __table_args__ = (
        Index("ix_api_collections_mapping", "mapping_id"),
        Index("ix_api_collections_hash", "content_hash"),
    )


# REMOVED ApiRequest model - functionality moved to ApplicationEndpoint
# 
# The ApiRequest model that previously stored Postman request details
# has been deprecated in favor of the ApplicationEndpoint model which
# provides a cleaner, more normalized approach:
#
# - ApplicationEndpoint stores the core endpoint data
# - Headers are stored in app_environment_country_mappings.default_headers  
# - Body content is stored in application_endpoints.body
#
# Migration path: api_requests → application_endpoints (completed)


# Export public API
__all__ = ["ApiCollection"]