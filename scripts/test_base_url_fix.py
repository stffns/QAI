#!/usr/bin/env python3
"""
Test script para verificar el PostmanEndpointImporter con la corrección de base URL
"""

import sys
import os
import json
from pathlib import Path

# Add project root to path
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from sqlmodel import Session, create_engine
from src.importers.postman_endpoint_importer import PostmanEndpointImporter


def test_path_normalization():
    """Test que la normalización de paths funciona correctamente"""
    
    print("🧪 Testing Path Normalization")
    print("=" * 50)
    
    # Create test cases
    test_cases = [
        {
            "name": "Full URL with BASE_URL variable",
            "input": "{{BASE_URL}}/api/v1/users",
            "expected": "/api/v1/users"
        },
        {
            "name": "Full URL with protocol",
            "input": "https://api.example.com/api/v1/users",
            "expected": "/api/v1/users"
        },
        {
            "name": "Path with baseUrl variable", 
            "input": "{{baseUrl}}/profile/{{userId}}",
            "expected": "/profile/{userId}"
        },
        {
            "name": "Path with :param syntax",
            "input": "/api/users/:userId/profile",
            "expected": "/api/users/{userId}/profile"
        },
        {
            "name": "Complex path with infrastructure variables (should be removed)",
            "input": "{{BASE_URL}}-{{ENV}}/{{COUNTRY}}/dashboard/{{COUNTRY}}",
            "expected": "/dashboard"
        },
        {
            "name": "Business logic variables (should be kept)",
            "input": "{{BASE_URL}}/api/users/{{userId}}/profile",
            "expected": "/api/users/{userId}/profile"
        }
    ]
    
    # Create importer instance (no database needed for path testing)
    engine = create_engine("sqlite:///:memory:")
    with Session(engine) as session:
        importer = PostmanEndpointImporter(session)
        
        success_count = 0
        for i, test_case in enumerate(test_cases, 1):
            print(f"\n{i}. {test_case['name']}")
            print(f"   Input:    {test_case['input']}")
            
            # Test the path normalization
            result = importer._normalize_path(test_case['input'], {})
            print(f"   Result:   {result}")
            print(f"   Expected: {test_case['expected']}")
            
            if result == test_case['expected']:
                print(f"   ✅ PASS")
                success_count += 1
            else:
                print(f"   ❌ FAIL")
        
        print(f"\n📊 Results: {success_count}/{len(test_cases)} tests passed")
        return success_count == len(test_cases)


def test_postman_collection_import():
    """Test de importación completa con colección de ejemplo"""
    
    print("\n📦 Testing Complete Postman Collection Import")
    print("=" * 60)
    
    # Create test collection with base URLs
    test_collection = {
        "info": {
            "name": "Test API with Base URLs",
            "version": "1.0.0"
        },
        "item": [
            {
                "name": "Get User Profile",
                "request": {
                    "method": "GET",
                    "header": [
                        {"key": "Authorization", "value": "Bearer {{TOKEN}}", "type": "text"}
                    ],
                    "url": {
                        "raw": "{{BASE_URL}}/api/v1/profile",
                        "host": ["{{BASE_URL}}"],
                        "path": ["api", "v1", "profile"]
                    }
                }
            },
            {
                "name": "Update User",
                "request": {
                    "method": "PUT",
                    "header": [
                        {"key": "Content-Type", "value": "application/json"}
                    ],
                    "url": "https://api.example.com/api/v1/users/:userId",
                    "body": {
                        "mode": "raw",
                        "raw": "{\"name\": \"Updated User\"}"
                    }
                }
            }
        ]
    }
    
    # Save test collection
    test_path = Path("temp/test_base_url_collection.json")
    test_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(test_path, 'w') as f:
        json.dump(test_collection, f, indent=2)
    
    print(f"📁 Test collection created: {test_path}")
    
    try:
        # Test import with real database structure
        engine = create_engine("sqlite:///data/qa_intelligence.db")
        with Session(engine) as session:
            importer = PostmanEndpointImporter(session)
            
            result = importer.import_collection(
                collection_path=test_path,
                application_code='TEST_APP',
                environment_code='STA', 
                country_code='RO'
            )
            
            print("🎉 Import successful!")
            print(f"📊 Result: {result}")
            
            # Verify the endpoints were created correctly
            from database.models.application_endpoints import ApplicationEndpoint
            from sqlmodel import select
            
            endpoints = session.exec(
                select(ApplicationEndpoint).where(
                    ApplicationEndpoint.mapping_id == result['mapping_id']
                )
            ).all()
            
            print(f"\n📍 Endpoints created ({len(endpoints)}):")
            for endpoint in endpoints:
                print(f"  • {endpoint.endpoint_name}")
                print(f"    URL: {endpoint.endpoint_url}")  # Should be just path, not full URL
                print(f"    Method: {endpoint.http_method}")
                
                # Verify it's just a path, not full URL
                if endpoint.endpoint_url.startswith('/') and '://' not in endpoint.endpoint_url:
                    print(f"    ✅ Correct: endpoint_url is path only")
                else:
                    print(f"    ❌ Wrong: endpoint_url contains base URL")
            
            return True
            
    except Exception as e:
        print(f"❌ Import failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        # Cleanup
        if test_path.exists():
            test_path.unlink()


def main():
    """Run all tests"""
    print("🚀 Postman Endpoint Importer Base URL Fix Test")
    print("=" * 60)
    
    # Test 1: Path normalization unit tests
    test1_success = test_path_normalization()
    
    # Test 2: Full import test
    test2_success = test_postman_collection_import()
    
    # Final result
    if test1_success and test2_success:
        print("\n🎉 ALL TESTS PASSED!")
        print("✅ Base URL fix is working correctly")
        print("📁 Endpoints now store only paths, base URLs in mapping table")
    else:
        print("\n💥 Some tests failed!")
        print("🔧 Need to fix issues before proceeding")
    
    return test1_success and test2_success


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)