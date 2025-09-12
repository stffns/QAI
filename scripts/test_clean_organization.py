#!/usr/bin/env python3
"""
Test completo de la organización limpia de modelos y repositorios
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), "..", ".."))

from sqlmodel import create_engine, Session
from pathlib import Path

def test_clean_organization():
    """Test de la organización limpia completa"""
    
    print("🧹 Testing Clean Models and Repositories Organization")
    print("=" * 70)
    
    try:
        # 1. Test imports from models/__init__.py
        print("1️⃣ Testing model imports...")
        from database.models import (
            ApplicationEndpoint,
            AppEnvironmentCountryMapping,
            Apps, 
            Environments,
            Countries
        )
        print("✅ All core models imported successfully")
        
        # 2. Test repository imports
        print("\n2️⃣ Testing repository imports...")
        from database.repositories.application_endpoints_repository import ApplicationEndpointRepository
        from database.repositories.unit_of_work import UnitOfWork
        print("✅ Repository and UoW imported successfully")
        
        # 3. Test UnitOfWork integration
        print("\n3️⃣ Testing UnitOfWork integration...")
        engine = create_engine("sqlite:///data/qa_intelligence.db")
        with Session(engine) as session:
            uow = UnitOfWork(session)
            
            # Test repository access
            endpoints_repo = uow.application_endpoints
            mappings_repo = uow.app_environment_country_mappings
            apps_repo = uow.apps
            
            print("✅ UoW provides access to all repositories")
            
            # 4. Test basic repository operations
            print("\n4️⃣ Testing repository operations...")
            
            # Count endpoints
            endpoint_count = endpoints_repo.get_endpoint_count()
            active_count = endpoints_repo.get_active_endpoint_count()
            
            print(f"📊 Total endpoints: {endpoint_count}")
            print(f"📊 Active endpoints: {active_count}")
            
            # Test search
            search_results = endpoints_repo.search_endpoints(search_term="test", is_active=True)
            print(f"📊 Search results for 'test': {len(search_results)}")
            
            # Test mapping-based lookup
            if endpoint_count > 0:
                first_endpoint = endpoints_repo.get_all(limit=1)[0]
                mapping_endpoints = endpoints_repo.get_by_mapping(first_endpoint.mapping_id)
                print(f"📊 Endpoints for mapping {first_endpoint.mapping_id}: {len(mapping_endpoints)}")
            
            print("✅ Repository operations working correctly")
        
        # 5. Test model structure
        print("\n5️⃣ Testing model clean structure...")
        
        # Create test endpoint instance
        test_endpoint = ApplicationEndpoint(
            mapping_id=1,
            endpoint_name="test_clean_endpoint",
            endpoint_url="/api/test/clean",
            http_method="GET",
            description="Test clean structure"
        )
        
        # Check that it only has mapping_id (no redundant FKs)
        model_fields = list(test_endpoint.model_fields.keys())
        has_clean_structure = (
            'mapping_id' in model_fields and
            'application_id' not in model_fields and
            'environment_id' not in model_fields and
            'country_id' not in model_fields
        )
        
        if has_clean_structure:
            print("✅ Model has clean structure (only mapping_id FK)")
        else:
            print("❌ Model still has redundant fields")
            print(f"Fields: {model_fields}")
            return False
        
        # 6. Test validation
        print("\n6️⃣ Testing model validation...")
        
        try:
            # Test URL validation
            invalid_endpoint = ApplicationEndpoint(
                mapping_id=1,
                endpoint_name="invalid",
                endpoint_url="invalid-url",  # Should fail validation
                http_method="GET"
            )
            print("❌ URL validation not working")
            return False
        except ValueError:
            print("✅ URL validation working correctly")
            
        try:
            # Test HTTP method validation
            invalid_method = ApplicationEndpoint(
                mapping_id=1,
                endpoint_name="invalid",
                endpoint_url="/api/test",
                http_method="INVALID"  # Should fail validation
            )
            print("❌ HTTP method validation not working")
            return False
        except ValueError:
            print("✅ HTTP method validation working correctly")
        
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_import_compatibility():
    """Test que la organización no rompe imports existentes"""
    
    print("\n🔗 Testing Import Compatibility")
    print("=" * 40)
    
    try:
        # Test direct model imports (should work)
        from database.models.application_endpoints import ApplicationEndpoint
        from database.models.app_environment_country_mappings import AppEnvironmentCountryMapping
        print("✅ Direct model imports work")
        
        # Test repository imports
        from database.repositories.application_endpoints_repository import ApplicationEndpointRepository
        print("✅ Direct repository imports work")
        
        # Test that old imports don't exist
        try:
            from database.models.application_endpoints_clean import ApplicationEndpoint as OldEndpoint
            print("❌ Old clean model still importable")
            return False
        except ImportError:
            print("✅ Old clean model properly removed")
            
        return True
        
    except Exception as e:
        print(f"❌ Import compatibility test failed: {e}")
        return False

if __name__ == "__main__":
    success1 = test_clean_organization()
    success2 = test_import_compatibility()
    
    if success1 and success2:
        print("\n🎉 Clean Organization Test Completed Successfully!")
        print("✨ Models and repositories are properly organized")
        print("📁 Structure: Clean, normalized, maintainable")
        print("🚀 Ready for production use!")
    else:
        print("\n💥 Organization test failed!")
        print("🔧 Need to fix issues before proceeding")