import json
from pathlib import Path
from typing import Dict, Any

from sqlmodel import create_engine, Session, SQLModel

# DEPRECATED - PostmanImporter replaced by PostmanEndpointImporter
# from src.importers.postman_importer import PostmanImporter
from database.models.api_collections import ApiCollection
# ApiRequest model removed - using ApplicationEndpoint instead
from database.models.application_endpoints import ApplicationEndpoint


def build_memory_session():
    engine = create_engine("sqlite:///:memory:", echo=False)
    # Import models to metadata
    SQLModel.metadata.create_all(engine)
    return Session(engine)


def write_tmp(tmp_path: Path, name: str, data: Dict[str, Any]) -> Path:
    p = tmp_path / name
    p.write_text(json.dumps(data, indent=2))
    return p


def minimal_collection():
    return {
        "info": {"name": "Sample"},
        "item": [
            {
                "name": "Get Users",
                "request": {
                    "method": "GET",
                    "url": {"raw": "https://api.example.com/users"},
                    "header": [{"key": "Accept", "value": "application/json"}],
                },
            },
            {
                "name": "Create User",
                "request": {
                    "method": "POST",
                    "url": {"raw": "https://api.example.com/users"},
                    "body": {"mode": "raw", "raw": "{\n  \"name\": \"{{username}}\"\n}"},
                },
            },
        ],
    }


def minimal_environment():
    return {
        "values": [
            {"key": "username", "value": "alice"},
            {"key": "API_TOKEN", "value": "secret123"},
        ]
    }


def test_import_basic(tmp_path):
    session = build_memory_session()
    importer = PostmanImporter(session)

    coll_file = write_tmp(tmp_path, "collection.json", minimal_collection())
    env_file = write_tmp(tmp_path, "environment.json", minimal_environment())

    result = importer.import_collection(coll_file, environment_path=env_file)

    assert result["reused"] is False
    assert result["requests"] == 2
    assert result["unresolved_requests"] == 0  # username resolved

    # Idempotency: second run
    result2 = importer.import_collection(coll_file, environment_path=env_file)
    assert result2["reused"] is True
    assert result2["requests"] == 2


def test_unresolved_variable_detection(tmp_path):
    session = build_memory_session()
    importer = PostmanImporter(session)
    coll = minimal_collection()
    # Body has {{username}}; environment missing it
    coll_file = write_tmp(tmp_path, "collection.json", coll)
    env_file = write_tmp(tmp_path, "environment.json", {"values": []})
    result = importer.import_collection(coll_file, environment_path=env_file)
    assert result["unresolved_requests"] == 1  # POST has unresolved var


def test_endpoint_linkage(tmp_path):
    session = build_memory_session()
    # Pre-create endpoint matching /users GET
    endpoint = ApplicationEndpoint(
        application_id=1,
        environment_id=1,
        country_id=None,
        endpoint_name="Users",
        endpoint_url="/users",
        http_method="GET",
    )
    session.add(endpoint)
    session.commit()
    session.refresh(endpoint)

    importer = PostmanImporter(session)
    coll_file = write_tmp(tmp_path, "collection.json", minimal_collection())
    result = importer.import_collection(coll_file)
    assert result["linked_endpoints"] >= 1
