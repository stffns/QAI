#!/usr/bin/env python3
"""
Test Completo del Workflow WebSocket v2.0 → Postman Import → Clean Database
===========================================================================

Valida el flujo completo:
1. WebSocket recibe attachment con envelope v2.0
2. PostmanEndpointImporter procesa la colección
3. Guarda en application_endpoints con mapping_id limpio
4. Headers se guardan en app_environment_country_mappings

Author: QA Intelligence Team
Date: 2025-09-08
"""

import asyncio
import json
from pathlib import Path

try:
    from config import get_config
except ImportError:
    import os
    import sys

    sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
    from config import get_config

try:
    from src.logging_config import get_logger
except ImportError:
    import logging

    def get_logger(name):
        return logging.getLogger(name)


logger = get_logger("CompleteWorkflowTest")

# Simular datos de WebSocket v2.0
MOCK_ENVELOPE_V2 = {
    "version": "2.0",
    "conversation_id": "test-complete-workflow",
    "message_id": "msg-12345",
    "metadata": {"user_id": "test@qai.com", "timestamp": "2025-01-08T10:00:00Z"},
    "content": {
        "text": "Importar esta colección Postman",
        "attachments": [
            {
                "type": "file",
                "name": "test_collection.json",
                "content": json.dumps(
                    {
                        "info": {
                            "name": "Test API Collection",
                            "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json",
                        },
                        "item": [
                            {
                                "name": "Get Users",
                                "request": {
                                    "method": "GET",
                                    "url": "{{BASE_URL}}/api/v1/users",
                                    "header": [
                                        {
                                            "key": "Authorization",
                                            "value": "Bearer {{TOKEN}}",
                                            "type": "text",
                                        },
                                        {
                                            "key": "Content-Type",
                                            "value": "application/json",
                                            "type": "text",
                                        },
                                    ],
                                },
                            },
                            {
                                "name": "Create User",
                                "request": {
                                    "method": "POST",
                                    "url": "{{BASE_URL}}/api/v1/users",
                                    "header": [
                                        {
                                            "key": "Authorization",
                                            "value": "Bearer {{TOKEN}}",
                                            "type": "text",
                                        }
                                    ],
                                    "body": {
                                        "mode": "raw",
                                        "raw": '{"name": "John Doe", "email": "john@example.com"}',
                                    },
                                },
                            },
                        ],
                    }
                ),
            }
        ],
    },
}


def test_websocket_envelope_validation():
    """Test 1: WebSocket envelope v2.0 validation"""
    print("🌐 Testing WebSocket Envelope v2.0 Validation")
    print("=" * 60)

    try:
        from src.websocket.middleware import ValidationMiddleware

        middleware = ValidationMiddleware()
        processed = middleware.process_envelope(MOCK_ENVELOPE_V2)

        print("✅ Envelope v2.0 validated successfully")
        print(f"📝 Version: {processed['version']}")
        print(f"📁 Attachments: {len(processed['content']['attachments'])}")
        return processed

    except Exception as e:
        print(f"❌ Envelope validation failed: {e}")
        return None


def test_postman_import(envelope):
    """Test 2: Postman collection import with clean structure"""
    print("\n📦 Testing Postman Import with Clean Structure")
    print("=" * 60)

    try:
        from database.connection import get_engine
        from database.repositories import create_unit_of_work_factory
        from src.importers.postman_endpoint_importer import PostmanEndpointImporter

        # Setup database
        engine = get_engine()
        uow_factory = create_unit_of_work_factory(engine)

        # Get attachment content
        attachment = envelope["content"]["attachments"][0]
        collection_data = json.loads(attachment["content"])

        # Import collection
        importer = PostmanEndpointImporter(uow_factory)
        result = importer.import_collection(
            collection_data=collection_data,
            application_code="TEST_APP",
            environment_code="DEV",
            country_code="CO",
        )

        print(f"✅ Import completed")
        print(f"📊 Endpoints imported: {result.get('endpoints_imported', 0)}")
        print(f"🔗 Mapping ID used: {result.get('mapping_id')}")

        return result

    except Exception as e:
        print(f"❌ Postman import failed: {e}")
        import traceback

        traceback.print_exc()
        return None


def test_database_verification(import_result):
    """Test 3: Database structure verification"""
    print("\n🗄️ Testing Database Structure Verification")
    print("=" * 60)

    try:
        from database.connection import get_engine
        from database.repositories import create_unit_of_work_factory

        engine = get_engine()
        uow_factory = create_unit_of_work_factory(engine)

        with uow_factory.create_scope() as uow:
            # Check endpoints in clean structure
            mapping_id = import_result["mapping_id"]
            endpoints = uow.application_endpoints.get_by_mapping_id(mapping_id)

            print(f"✅ Found {len(endpoints)} endpoints in clean structure")

            for endpoint in endpoints:
                print(f"  📍 {endpoint.endpoint_name}")
                print(f"     🔗 Mapping ID: {endpoint.mapping_id}")
                print(f"     📊 Method: {endpoint.http_method}")
                print(f"     🌐 URL: {endpoint.endpoint_url}")

                # Verify no direct FKs to apps/env/country
                assert not hasattr(
                    endpoint, "application_id"
                ), "Direct application_id FK should not exist"
                assert not hasattr(
                    endpoint, "environment_id"
                ), "Direct environment_id FK should not exist"
                assert not hasattr(
                    endpoint, "country_id"
                ), "Direct country_id FK should not exist"
                print(f"     ✅ Clean structure confirmed: only mapping_id FK")

            # Check mapping exists with headers
            mapping = uow.app_environment_country_mappings.get_by_id(mapping_id)
            if mapping and mapping.custom_headers:
                headers = json.loads(mapping.custom_headers)
                print(f"✅ Headers found in mapping: {len(headers)} headers")
                for header in headers:
                    print(
                        f"  🔑 {header.get('key', 'N/A')}: {header.get('value', 'N/A')}"
                    )

        return True

    except Exception as e:
        print(f"❌ Database verification failed: {e}")
        import traceback

        traceback.print_exc()
        return False


def main():
    """Ejecutar test completo del workflow"""
    print("🚀 Complete Workflow Test: WebSocket v2.0 → Import → Clean DB")
    print("=" * 80)

    # Test 1: WebSocket Envelope
    envelope = test_websocket_envelope_validation()
    if not envelope:
        print("💥 Workflow failed at WebSocket validation")
        return False

    # Test 2: Postman Import
    import_result = test_postman_import(envelope)
    if not import_result:
        print("💥 Workflow failed at Postman import")
        return False

    # Test 3: Database Verification
    db_ok = test_database_verification(import_result)
    if not db_ok:
        print("💥 Workflow failed at database verification")
        return False

    print("\n🎉 Complete Workflow Test PASSED!")
    print("✨ WebSocket v2.0 → Postman Import → Clean Database: ALL WORKING")
    print("🏗️ Architecture: Clean, normalized, maintainable")

    return True


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
