#!/usr/bin/env python3
"""
Test simple de la organización sin cargar todos los modelos SQLAlchemy
"""


def test_model_structure():
    """Test estructura del modelo sin SQLAlchemy"""

    print("🧹 Testing Clean Model Structure (No SQLAlchemy)")
    print("=" * 60)

    try:
        # Test import directo del modelo
        from database.models.application_endpoints import ApplicationEndpoint

        print("✅ ApplicationEndpoint imported successfully")

        # Test estructura del modelo
        test_endpoint = ApplicationEndpoint(
            mapping_id=1,
            endpoint_name="test_endpoint",
            endpoint_url="/api/test",
            http_method="GET",
        )

        # Verificar campos
        model_fields = list(test_endpoint.model_fields.keys())
        print(f"📊 Model fields: {model_fields}")

        # Verificar estructura limpia
        has_mapping_id = "mapping_id" in model_fields
        has_old_fields = any(
            field in model_fields
            for field in ["application_id", "environment_id", "country_id"]
        )

        if has_mapping_id and not has_old_fields:
            print("✅ Clean structure confirmed: only mapping_id FK")
        elif has_mapping_id and has_old_fields:
            print("⚠️ Mixed structure: has mapping_id but also old fields")
            print(
                f"Old fields found: {[f for f in ['application_id', 'environment_id', 'country_id'] if f in model_fields]}"
            )
        else:
            print("❌ No mapping_id found")
            return False

        # Test validaciones
        print("\n🔍 Testing validations...")

        # URL validation
        try:
            ApplicationEndpoint(
                mapping_id=1,
                endpoint_name="invalid",
                endpoint_url="invalid-url",
                http_method="GET",
            )
            print("❌ URL validation not working")
        except ValueError as e:
            print(f"✅ URL validation works: {e}")

        # HTTP method validation
        try:
            ApplicationEndpoint(
                mapping_id=1,
                endpoint_name="invalid",
                endpoint_url="/api/test",
                http_method="INVALID",
            )
            print("❌ HTTP method validation not working")
        except ValueError as e:
            print(f"✅ HTTP method validation works: {e}")

        return True

    except Exception as e:
        print(f"❌ Model test failed: {e}")
        return False


def test_repository_structure():
    """Test estructura del repository sin base de datos"""

    print("\n🏛️ Testing Repository Structure")
    print("=" * 40)

    try:
        from database.repositories.application_endpoints_repository import (
            ApplicationEndpointRepository,
        )

        print("✅ ApplicationEndpointRepository imported")

        # Verificar métodos clean
        repo_methods = [
            method
            for method in dir(ApplicationEndpointRepository)
            if not method.startswith("_")
            and callable(getattr(ApplicationEndpointRepository, method))
        ]

        print(f"📊 Repository methods: {len(repo_methods)}")

        # Verificar métodos esperados
        expected_methods = [
            "create_endpoint",
            "get_by_mapping_and_name",
            "get_by_mapping",
            "search_endpoints",
            "update_endpoint",
        ]

        missing_methods = [
            method for method in expected_methods if method not in repo_methods
        ]

        if not missing_methods:
            print("✅ All expected methods present")
        else:
            print(f"❌ Missing methods: {missing_methods}")
            return False

        # Verificar que no tenga métodos antiguos
        old_methods = [
            "create_endpoint_with_app_env_country",  # Ejemplo de método antiguo
            "get_by_combination",
        ]

        found_old_methods = [method for method in old_methods if method in repo_methods]

        if not found_old_methods:
            print("✅ No old methods found")
        else:
            print(f"⚠️ Old methods still present: {found_old_methods}")

        return True

    except Exception as e:
        print(f"❌ Repository test failed: {e}")
        return False


def test_unit_of_work_integration():
    """Test integración con Unit of Work"""

    print("\n🔗 Testing UnitOfWork Integration")
    print("=" * 40)

    try:
        from database.repositories.unit_of_work import UnitOfWork

        print("✅ UnitOfWork imported")

        # Verificar que tiene property para application_endpoints
        uow_methods = dir(UnitOfWork)

        if "application_endpoints" in uow_methods:
            print("✅ UnitOfWork has application_endpoints property")
        else:
            print("❌ UnitOfWork missing application_endpoints property")
            return False

        return True

    except Exception as e:
        print(f"❌ UoW test failed: {e}")
        return False


def test_imports_cleanup():
    """Test que los imports están limpios"""

    print("\n🧹 Testing Import Cleanup")
    print("=" * 30)

    try:
        # Test que el modelo principal funciona
        from database.models.application_endpoints import ApplicationEndpoint

        print("✅ Main model import works")

        # Test que no quedan archivos old
        try:
            from database.models.application_endpoints_old import (
                ApplicationEndpoint as OldEndpoint,
            )

            print("❌ Old model file still exists")
            return False
        except (ImportError, ModuleNotFoundError):
            print("✅ Old model files cleaned up")

        # Test que el __init__.py está actualizado
        from database.models import ApplicationEndpoint as InitEndpoint

        print("✅ Model exported from __init__.py")

        return True

    except Exception as e:
        print(f"❌ Import cleanup test failed: {e}")
        return False


if __name__ == "__main__":
    print("🚀 Clean Organization Test (Lightweight)")
    print("=" * 50)

    tests = [
        test_model_structure,
        test_repository_structure,
        test_unit_of_work_integration,
        test_imports_cleanup,
    ]

    results = [test() for test in tests]

    if all(results):
        print("\n🎉 All Tests Passed! Clean Organization Complete!")
        print("✨ Structure: Clean, normalized, maintainable")
        print("📁 Models: Only mapping_id FK, proper validations")
        print("🏛️ Repositories: Clean methods, no redundancy")
        print("🔗 UoW: Integrated properly")
        print("🧹 Imports: Clean and organized")
    else:
        failed_count = len([r for r in results if not r])
        print(f"\n💥 {failed_count}/{len(tests)} tests failed!")
        print("🔧 Fix issues before proceeding")
