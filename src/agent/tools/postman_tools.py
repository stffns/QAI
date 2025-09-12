"""Postman import tool for QA Intelligence Agent.

Provides a tool function that the agent can invoke to import a Postman
collection (and optional environment) already delivered via attachment
or available on disk.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Optional

from sqlmodel import Session, create_engine

from config.settings import get_settings
from src.importers.postman_endpoint_importer import PostmanEndpointImporter

try:
    from agno.tools import tool
except ImportError:  # pragma: no cover
    def tool(name=None, description=None):  # type: ignore
        def decorator(func):
            return func
        return decorator


@tool(name="postman_import", description="Import a Postman collection and optional environment to application endpoints")
def postman_import(
    collection_path: str,
    environment_path: Optional[str] = None,
    application_code: str = "EVA",
    environment_code: str = "STA", 
    country_code: Optional[str] = "RO",
) -> Dict[str, Any]:
    """Import a Postman collection to application endpoints.

    Args:
        collection_path: Path to collection JSON file
        environment_path: Optional path to environment JSON
        application_code: Application code (EVA, ONEAPP, etc.)
        environment_code: Environment code (STA, UAT, PRD)
        country_code: Optional country code (RO, FR, CO, etc.)

    Returns:
        Dict summary (endpoints created, updated, mapping info)
    """
    settings = get_settings()
    db_url = settings.database.url
    if not db_url:
        return {"error": "Database URL not configured"}
    engine = create_engine(db_url)
    coll_file = Path(collection_path)
    env_file = Path(environment_path) if environment_path else None
    if not coll_file.exists():
        return {"error": f"Collection file not found: {coll_file}"}
    with Session(engine) as session:
        importer = PostmanEndpointImporter(session)
        result = importer.import_collection(
            collection_path=coll_file,
            environment_path=env_file,
            application_code=application_code,
            environment_code=environment_code,
            country_code=country_code,
        )
    return result


__all__ = ["postman_import"]
