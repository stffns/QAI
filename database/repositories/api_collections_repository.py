from __future__ import annotations

from typing import Optional, List
from sqlmodel import Session, select
from sqlalchemy import func, text

from .base import BaseRepository
from ..models.api_collections import ApiCollection


class ApiCollectionsRepository(BaseRepository[ApiCollection]):
    """Repository for ApiCollection entities."""

    def __init__(self, session: Session):
        super().__init__(session, ApiCollection)

    def get_by_hash(self, raw_hash: str) -> Optional[ApiCollection]:
        stmt = select(ApiCollection).where(ApiCollection.raw_hash == raw_hash)
        return self.session.exec(stmt).first()

    def list_recent(self, limit: int = 20) -> List[ApiCollection]:
        # Using raw text ordering to avoid typing issues with SQLModel field attribute
        stmt = select(ApiCollection).order_by(text("created_at DESC")).limit(limit)
        return list(self.session.exec(stmt).all())

    def create_collection(
        self,
        name: str,
        raw_hash: str,
        *,
        mapping_id: Optional[int] = None,
        source_raw: Optional[str] = None,
        environment_snapshot: Optional[dict] = None,
        secret_variables: Optional[dict] = None,
        base_url_override: Optional[str] = None,
    ) -> ApiCollection:
        existing = self.get_by_hash(raw_hash)
        if existing:
            return existing
        entity = ApiCollection(
            name=name,
            raw_hash=raw_hash,
            mapping_id=mapping_id,
            source_raw=source_raw,
            environment_snapshot=environment_snapshot,
            secret_variables=secret_variables,
            base_url_override=base_url_override,
        )
        return self.save(entity)
