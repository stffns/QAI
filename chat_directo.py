#!/usr/bin/env python3
"""
Chat directo con QA Intelligence
Carga automáticamente las configuraciones desde .env
"""

import os
import sys
from pathlib import Path

# Cargar variables de entorno desde .env
def load_env():
    env_file = Path('.env')
    if env_file.exists():
        with open(env_file, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    os.environ[key] = value

def main():
    """Ejecutar el chat agent con configuración automática"""
    print("🚀 Iniciando QA Intelligence Chat")
    print("=" * 40)
    
    # Cargar variables de entorno
    load_env()
    
    # Verificar API key
    if not os.getenv('OPENAI_API_KEY'):
        print("❌ API Key de OpenAI no encontrada")
        print("   Verifica tu archivo .env")
        return
    
    print("✅ Configuración cargada")
    print("💬 Iniciando chat...")
    print("   Escribe tus preguntas o 'salir' para terminar")
    print("=" * 40)
    
    try:
        # Agregar rutas
        project_root = os.path.dirname(os.path.abspath(__file__))
        agent_dir = os.path.join(project_root, 'src', 'agent')
        sys.path.insert(0, agent_dir)
        sys.path.insert(0, project_root)
        
        # Importar componentes
        from agno.agent import Agent
        from agno.models.openai import OpenAIChat
        from config import get_config
        from model_manager import ModelManager
        from tools_manager import ToolsManager
        from storage_manager import StorageManager
        
        # Crear configuración
        config = get_config()
        
        # Crear componentes
        model_manager = ModelManager(config)
        tools_manager = ToolsManager(config)
        storage_manager = StorageManager(config)
        
        # Configurar storage correctamente
        storage = storage_manager.setup_storage()
        
        # Crear modelo y agente con memoria
        model = model_manager.create_model()
        tools = tools_manager.load_tools()
        agent = Agent(
            model=model,
            tools=tools,
            memory=storage  # ← Usar "memory" y la storage configurada
        )
        
        print("🤖 Agente listo!")
        
        # Loop de chat
        while True:
            try:
                user_input = input("\n🙋 Pregunta: ").strip()
                
                if user_input.lower() in ['salir', 'exit', 'quit', 'q']:
                    print("👋 ¡Hasta luego!")
                    break
                
                if not user_input:
                    continue
                
                print("🤖 Respuesta: ", end="", flush=True)
                response = agent.run(user_input)
                # La respuesta puede ser un objeto con diferentes atributos
                if hasattr(response, 'data'):
                    print(response.data)
                elif hasattr(response, 'content'):
                    print(response.content)
                else:
                    print(str(response))
                
            except KeyboardInterrupt:
                print("\n\n👋 Chat terminado")
                break
            except Exception as e:
                print(f"❌ Error: {e}")
                continue
                
    except Exception as e:
        print(f"❌ Error iniciando chat: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
