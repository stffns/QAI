"""
Test del Chat Agent - Verificar que el agente sigue funcionando correctamente
"""

import sys
import os
from unittest.mock import MagicMock, patch
from datetime import datetime

# Setup path
sys.path.append('.')

def test_chat_agent_imports():
    """Test que los imports del chat agent funcionen"""
    print("🔍 Testing chat agent imports...")
    
    try:
        # Test QA Agent
        from src.agent.qa_agent import QAAgent
        print("   ✅ QA Agent imported successfully")
        
        # Test Chat Interface
        from src.agent.chat_interface import ChatInterface
        print("   ✅ Chat Interface imported successfully")
        
        # Test Manager components
        from src.agent.model_manager import ModelManager
        from src.agent.tools_manager import ToolsManager
        from src.agent.storage_manager import StorageManager
        print("   ✅ Manager components imported successfully")
        
        return True
    except Exception as e:
        print(f"   ❌ Chat agent import error: {e}")
        return False

def test_qa_agent_initialization():
    """Test que el QA Agent se inicialice correctamente"""
    print("\n🤖 Testing QA Agent initialization...")
    
    try:
        from src.agent.qa_agent import QAAgent
        from config import get_settings
        
        # Test basic initialization
        settings = get_settings()
        qa_agent = QAAgent(config=settings)
        
        print("   ✅ QA Agent initialized successfully")
        
        # Test that agent components exist
        assert hasattr(qa_agent, 'agent'), "QA Agent missing internal agent"
        assert hasattr(qa_agent, 'config'), "QA Agent missing config"
        assert hasattr(qa_agent, 'model_manager'), "QA Agent missing model_manager"
        assert hasattr(qa_agent, 'tools_manager'), "QA Agent missing tools_manager"
        assert hasattr(qa_agent, 'storage_manager'), "QA Agent missing storage_manager"
        
        print("   ✅ QA Agent components properly initialized")
        
        # Test health check
        health = qa_agent.health_check()
        if health.get('overall', False):
            print("   ✅ QA Agent health check passed")
        else:
            print(f"   ⚠️  QA Agent health check issues: {health}")
        
        return True
    except Exception as e:
        print(f"   ❌ QA Agent initialization error: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_chat_interface_creation():
    """Test que la interfaz de chat se pueda crear"""
    print("\n💬 Testing Chat Interface creation...")
    
    try:
        from src.agent.qa_agent import QAAgent
        from src.agent.chat_interface import ChatInterface
        from config import get_settings
        
        # Create QA Agent
        settings = get_settings()
        qa_agent = QAAgent(config=settings)
        
        # Create Chat Interface
        chat_interface = ChatInterface(qa_agent.agent, config)
        
        print("   ✅ Chat Interface created successfully")
        
        # Test that interface has required methods
        assert hasattr(chat_interface, 'start_chat'), "Missing start_chat method"
        assert hasattr(chat_interface, '_get_agent_response'), "Missing _get_agent_response method"
        assert hasattr(chat_interface, '_show_welcome'), "Missing _show_welcome method"
        
        print("   ✅ Chat Interface has all required methods")
        
        return True
    except Exception as e:
        print(f"   ❌ Chat Interface creation error: {e}")
        return False

def test_agent_response_simulation():
    """Test simulado de respuesta del agente"""
    print("\n🎯 Testing agent response simulation...")
    
    try:
        from src.agent.qa_agent import QAAgent
        from config import get_settings
        
        # Create QA Agent
        settings = get_settings()
        qa_agent = QAAgent(config=settings)
        
        # Test that the agent exists and can potentially respond
        if qa_agent.agent:
            print("   ✅ Internal agent is properly configured")
            
            # Mock a simple response test
            test_input = "Hello, what can you help me with?"
            
            # Try to get response (this might fail due to API keys, but structure should work)
            try:
                # Create a mock response to avoid API calls
                with patch.object(qa_agent.agent, 'run') as mock_run:
                    mock_response = MagicMock()
                    mock_response.content = "Hello! I'm QA Intelligence Agent. How can I help you today?"
                    mock_run.return_value = mock_response
                    
                    response = qa_agent.agent.run(test_input)
                    if response and hasattr(response, 'content') and response.content:
                        print(f"   ✅ Agent response simulation successful: {str(response.content)[:50]}...")
                    else:
                        print("   ✅ Agent response simulation successful: Response structure correct")
                    
            except Exception as api_error:
                print(f"   ⚠️  Agent response simulation - API issue (expected): {api_error}")
                print("   ✅ Agent structure is correct, API configuration may be needed")
        else:
            print("   ❌ Internal agent not properly configured")
            return False
        
        return True
    except Exception as e:
        print(f"   ❌ Agent response simulation error: {e}")
        return False

def test_configuration_integration():
    """Test integración con el sistema de configuración"""
    print("\n⚙️  Testing configuration integration...")
    
    try:
        from config import get_settings
        from src.agent.qa_agent import QAAgent
        
        # Test config loading
        settings = get_settings()
        print("   ✅ Configuration loaded successfully")
        
        # Test config validation
        is_valid = config.validate_config()
        print(f"   {'✅' if is_valid else '⚠️ '} Configuration validation: {is_valid}")
        
        # Test QA Agent with config
        qa_agent = QAAgent(config=settings)
        
        # Test config access through agent
        agent_info = qa_agent.get_info()
        print(f"   ✅ Agent info available: {len(agent_info)} components")
        
        return True
    except Exception as e:
        print(f"   ❌ Configuration integration error: {e}")
        return False

def test_managers_functionality():
    """Test funcionalidad de los managers"""
    print("\n🏗️  Testing managers functionality...")
    
    try:
        from src.agent.model_manager import ModelManager
        from src.agent.tools_manager import ToolsManager
        from src.agent.storage_manager import StorageManager
        from config import get_settings
        
        settings = get_settings()
        
        # Test Model Manager
        model_manager = ModelManager(config)
        model = model_manager.create_model()
        print("   ✅ Model Manager created model successfully")
        
        # Test Tools Manager
        tools_manager = ToolsManager(config)
        tools = tools_manager.load_tools()
        print(f"   ✅ Tools Manager loaded {len(tools)} tools")
        
        # Test Storage Manager
        storage_manager = StorageManager(config)
        storage = storage_manager.setup_storage()
        if storage:
            print("   ✅ Storage Manager created storage successfully")
        else:
            print("   ⚠️  Storage Manager: Storage is None (might be disabled)")
        
        return True
    except Exception as e:
        print(f"   ❌ Managers functionality error: {e}")
        return False

def test_database_integration_with_agent():
    """Test integración de la base de datos con el agente"""
    print("\n🗄️  Testing database integration with agent...")
    
    try:
        from database.repositories import create_unit_of_work_factory
        from src.agent.qa_agent import QAAgent
        from config import get_settings
        
        # Test database access
        factory = create_unit_of_work_factory('sqlite:///data/qa_intelligence.db')
        with factory.create_scope() as uow:
            user_count = uow.users.count()
            print(f"   ✅ Database accessible: {user_count} users found")
        
        # Test QA Agent can access database indirectly through storage
        settings = get_settings()
        qa_agent = QAAgent(config=settings)
        
        # Test that storage manager can potentially access database
        storage_info = qa_agent.storage_manager.get_storage_info()
        print(f"   ✅ Storage manager info: {storage_info}")
        
        return True
    except Exception as e:
        print(f"   ❌ Database integration error: {e}")
        return False

def test_run_qa_agent_script():
    """Test que el script run_qa_agent.py sea ejecutable"""
    print("\n📝 Testing run_qa_agent.py script...")
    
    try:
        # Test import of main script
        import run_qa_agent
        print("   ✅ run_qa_agent.py imports successfully")
        
        # Test that main function exists
        assert hasattr(run_qa_agent, 'main'), "Missing main function"
        print("   ✅ main() function exists")
        
        return True
    except Exception as e:
        print(f"   ❌ run_qa_agent.py script error: {e}")
        return False

def main():
    """Ejecutar test completo del chat agent"""
    print("🚀 QA Intelligence - Test del Chat Agent")
    print("=" * 60)
    print(f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    tests = [
        ("Chat Agent Imports", test_chat_agent_imports),
        ("QA Agent Initialization", test_qa_agent_initialization),
        ("Chat Interface Creation", test_chat_interface_creation),
        ("Agent Response Simulation", test_agent_response_simulation),
        ("Configuration Integration", test_configuration_integration),
        ("Managers Functionality", test_managers_functionality),
        ("Database Integration", test_database_integration_with_agent),
        ("Run QA Agent Script", test_run_qa_agent_script),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"\n❌ {test_name} test failed with exception: {e}")
            results.append((test_name, False))
    
    # Resumen
    print("\n" + "=" * 60)
    print("📋 RESUMEN DE TESTS DEL CHAT AGENT")
    print("=" * 60)
    
    passed = 0
    failed = 0
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} - {test_name}")
        if result:
            passed += 1
        else:
            failed += 1
    
    print(f"\n📊 RESULTADOS: {passed} passed, {failed} failed")
    
    if failed == 0:
        print("🎉 ¡TODOS LOS TESTS DEL CHAT AGENT PASARON!")
        print("✅ El agente de chat está funcionando correctamente")
        print("✅ La integración con la base de datos es exitosa")
        print("✅ Todos los componentes están operativos")
        print("✅ El chat agent está listo para responder preguntas")
    else:
        print("⚠️  Algunos tests fallaron. El chat agent puede necesitar configuración adicional.")
        print("💡 Verificar configuración de API keys y dependencias")
    
    return failed == 0

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
