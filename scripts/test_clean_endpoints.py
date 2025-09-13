#!/usr/bin/env python3
"""
Test script para el PostmanEndpointImporter con estructura limpia
"""

import os
import sys
from pathlib import Path

# Add project root to path
sys.path.append(os.path.join(os.path.dirname(__file__), "..", ".."))

# No direct database connection import needed - create engine directly
from sqlmodel import Session, create_engine

from src.importers.postman_endpoint_importer import PostmanEndpointImporter


def test_clean_importer():
    """Test the clean importer structure"""

    # Create test collection
    test_collection = {
        "info": {"name": "Clean Test Collection", "version": "1.0.0"},
        "item": [
            {
                "name": "Clean Test Endpoint",
                "request": {
                    "method": "GET",
                    "header": [],
                    "url": {
                        "raw": "/api/clean/test",
                        "path": ["/api", "clean", "test"],
                    },
                    "body": {"mode": "raw", "raw": '{"test": "clean structure"}'},
                },
            }
        ],
    }

    # Save test collection
    import json

    test_path = Path("temp/websocket_uploads/clean_test.json")
    test_path.parent.mkdir(parents=True, exist_ok=True)

    with open(test_path, "w") as f:
        json.dump(test_collection, f, indent=2)

    print(f"✅ Test collection created: {test_path}")

    # Test import with clean structure
    try:
        engine = create_engine("sqlite:///data/qa_intelligence.db")
        with Session(engine) as session:
            importer = PostmanEndpointImporter(session)

            result = importer.import_collection(
                collection_path=test_path,
                application_code="EVA",
                environment_code="STA",
                country_code="RO",
            )

            print("🎉 Import successful!")
            print("Result:", result)

            return result

    except Exception as e:
        print(f"❌ Import failed: {e}")
        import traceback

        traceback.print_exc()
        return None


def verify_clean_structure():
    """Verify that the clean structure is working"""

    try:
        engine = create_engine("sqlite:///data/qa_intelligence.db")
        with Session(engine) as session:
            from sqlmodel import select

            from database.models.app_environment_country_mappings import (
                AppEnvironmentCountryMapping,
            )
            from database.models.application_endpoints_clean import ApplicationEndpoint
            from database.models.apps import Apps
            from database.models.countries import Countries
            from database.models.environments import Environments

            # Test JOIN query with clean structure
            result = session.exec(
                select(
                    ApplicationEndpoint.endpoint_name,
                    ApplicationEndpoint.http_method,
                    ApplicationEndpoint.endpoint_url,
                    Apps.app_name,
                    Environments.env_name,
                    Countries.country_name,
                )
                .join(
                    AppEnvironmentCountryMapping,
                    ApplicationEndpoint.mapping_id == AppEnvironmentCountryMapping.id,
                )
                .join(Apps, AppEnvironmentCountryMapping.application_id == Apps.id)
                .join(
                    Environments,
                    AppEnvironmentCountryMapping.environment_id == Environments.id,
                )
                .join(
                    Countries, AppEnvironmentCountryMapping.country_id == Countries.id
                )
                .limit(5)
            ).all()

            print("\n📊 Clean structure verification:")
            print("Available endpoints with clean JOIN:")
            for row in result:
                print(f"  {row[1]} {row[0]} → {row[3]}/{row[4]}/{row[5]}")

            return True

    except Exception as e:
        print(f"❌ Verification failed: {e}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    print("🧹 Testing Clean Application Endpoints Structure")
    print("=" * 60)

    # Test import
    result = test_clean_importer()

    if result:
        # Verify structure
        verify_clean_structure()
        print("\n✅ Clean structure test completed successfully!")
    else:
        print("\n❌ Clean structure test failed!")
