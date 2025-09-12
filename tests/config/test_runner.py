"""
Test runner principal para todos los tests de configuración

Este módulo permite ejecutar todos los tests de config de forma organizada
y generar reportes comprehensivos.

Uso:
    python tests/config/test_runner.py
    
    # O usar pytest directamente:
    pytest tests/config/ -v
    pytest tests/config/test_core_models.py -v
    pytest tests/config/test_settings.py -v  
    pytest tests/config/test_logging_models.py -v
"""

import sys
import os
from pathlib import Path

# Agregar el directorio raíz al path para imports
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

def run_config_tests():
    """
    Ejecuta todos los tests de configuración y genera reporte
    """
    import pytest
    
    # Configuración de pytest
    args = [
        "tests/config/",
        "-v",                    # Verbose output
        "--tb=short",           # Traceback corto
        "--disable-warnings",   # Desabilitar warnings para output limpio
        "--color=yes",          # Output con colores
        "-x",                   # Parar en primer error
        "--durations=10",       # Mostrar 10 tests más lentos
        "--cov=config",         # Coverage del módulo config
        "--cov-report=term-missing",  # Reporte de coverage
        "--cov-report=html:tests/config/htmlcov",  # Reporte HTML
    ]
    
    print("🧪 Ejecutando tests de configuración...")
    print("=" * 60)
    
    # Ejecutar tests
    exit_code = pytest.main(args)
    
    print("\n" + "=" * 60)
    if exit_code == 0:
        print("✅ Todos los tests de configuración pasaron!")
        print("📊 Reporte de coverage generado en: tests/config/htmlcov/")
    else:
        print("❌ Algunos tests fallaron")
        print(f"💥 Código de salida: {exit_code}")
    
    return exit_code


def run_individual_test_files():
    """
    Ejecuta cada archivo de test individualmente para diagnóstico detallado
    """
    import pytest
    
    test_files = [
        ("Core Models", "tests/config/test_core_models.py"),
        ("Settings", "tests/config/test_settings.py"),
        ("Logging Models", "tests/config/test_logging_models.py")
    ]
    
    results = {}
    
    for name, test_file in test_files:
        print(f"\n🔍 Ejecutando tests de {name}...")
        print("-" * 40)
        
        args = [
            test_file,
            "-v",
            "--tb=short",
            "--disable-warnings",
            "--color=yes"
        ]
        
        exit_code = pytest.main(args)
        results[name] = exit_code
        
        if exit_code == 0:
            print(f"✅ {name}: PASSED")
        else:
            print(f"❌ {name}: FAILED (exit code: {exit_code})")
    
    print("\n" + "=" * 60)
    print("📋 RESUMEN DE RESULTADOS:")
    print("=" * 60)
    
    all_passed = True
    for name, exit_code in results.items():
        status = "✅ PASSED" if exit_code == 0 else "❌ FAILED"
        print(f"{name:20} : {status}")
        if exit_code != 0:
            all_passed = False
    
    if all_passed:
        print("\n🎉 ¡Todos los tests de configuración pasaron!")
    else:
        print("\n⚠️  Algunos tests fallaron. Revisar output arriba.")
    
    return 0 if all_passed else 1


def validate_test_environment():
    """
    Valida que el entorno esté configurado correctamente para los tests
    """
    print("🔧 Validando entorno de tests...")
    
    # Verificar imports principales
    try:
        import config
        print("✅ Módulo config importado correctamente")
    except ImportError as e:
        print(f"❌ Error importando config: {e}")
        return False
    
    try:
        from config.models.core import ModelConfig, DatabaseConfig, ToolsConfig
        print("✅ Modelos core importados correctamente")
    except ImportError as e:
        print(f"❌ Error importando modelos core: {e}")
        return False
    
    try:
        from config.settings import Settings
        print("✅ Settings importado correctamente")
    except ImportError as e:
        print(f"❌ Error importando Settings: {e}")
        return False
    
    try:
        from config.models.logging import LoggingConfig, LogLevel
        print("✅ Modelos de logging importados correctamente")
    except ImportError as e:
        print(f"❌ Error importando modelos de logging: {e}")
        return False
    
    # Verificar pytest disponible
    try:
        import pytest
        print(f"✅ pytest {pytest.__version__} disponible")
    except ImportError:
        print("❌ pytest no está instalado")
        return False
    
    print("✅ Entorno de tests validado correctamente")
    return True


def main():
    """
    Función principal del test runner
    """
    print("🚀 QA Intelligence - Test Runner de Configuración")
    print("=" * 60)
    
    # Validar entorno
    if not validate_test_environment():
        print("\n❌ Validación de entorno falló. Saliendo...")
        return 1
    
    # Preguntar modo de ejecución
    print("\n🎯 Selecciona modo de ejecución:")
    print("1. Ejecutar todos los tests juntos (rápido)")
    print("2. Ejecutar tests individuales (detallado)")
    print("3. Solo validar imports (diagnóstico)")
    
    choice = input("\nSelección [1-3]: ").strip()
    
    if choice == "1":
        return run_config_tests()
    elif choice == "2":
        return run_individual_test_files()
    elif choice == "3":
        print("\n✅ Validación completada. Todos los imports funcionan.")
        return 0
    else:
        print("❌ Selección inválida")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
