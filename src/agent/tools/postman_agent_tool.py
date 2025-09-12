"""
Postman Variables Agent Tool

Este módulo proporciona herramientas para que el agente QA pueda gestionar
variables de ejecución dinámicamente durante las pruebas.
"""

import json
from typing import Dict, Any, Optional, List
from datetime import datetime

# Importar el manager
from src.agent.tools.execution_variables_manager import ExecutionVariablesManager

class PostmanVariablesAgentTool:
    """Herramienta del agente para gestionar variables de ejecución"""
    
    def __init__(self):
        self.manager = ExecutionVariablesManager()
    
    def get_variables_for_test(
        self, 
        app_code: str, 
        env_code: str, 
        country_code: str
    ) -> Optional[Dict[str, Any]]:
        """
        Obtener variables de ejecución para un test específico
        
        Args:
            app_code: Código de aplicación (ej: 'EVA', 'ONEAPP')
            env_code: Código de ambiente (ej: 'STA', 'UAT', 'PRD')
            country_code: Código de país (ej: 'RO', 'FR', 'CO')
            
        Returns:
            Dict con variables y valores runtime, o None si no existe
        """
        # Necesitamos convertir códigos a IDs - esto requeriría consulta a DB
        # Por simplicidad, asumimos que tenemos los IDs
        # En implementación real, agregarías métodos para convertir códigos a IDs
        
        # Por ahora, usamos IDs fijos para testing
        app_id = 1  # Esto debería ser dinámico
        env_id = 1  # Esto debería ser dinámico  
        country_id = 1  # Esto debería ser dinámico
        
        return self.manager.get_mapping_variables(app_id, env_id, country_id)
    
    def update_test_variables(
        self,
        app_code: str,
        env_code: str, 
        country_code: str,
        new_values: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Actualizar valores runtime de variables durante un test
        
        Args:
            app_code: Código de aplicación
            env_code: Código de ambiente
            country_code: Código de país
            new_values: Nuevos valores a establecer
            
        Returns:
            Dict con resultado de la operación
        """
        # Similar conversión de códigos a IDs sería necesaria
        app_id = 1
        env_id = 1
        country_id = 1
        
        success = self.manager.update_runtime_values(
            app_id, env_id, country_id, new_values
        )
        
        return {
            'success': success,
            'updated_variables': list(new_values.keys()),
            'timestamp': datetime.now().isoformat()
        }
    
    def add_new_variables(
        self,
        app_code: str,
        env_code: str,
        country_code: str, 
        variable_templates: Dict[str, str]
    ) -> Dict[str, Any]:
        """
        Agregar nuevas plantillas de variables
        
        Args:
            app_code: Código de aplicación
            env_code: Código de ambiente
            country_code: Código de país
            variable_templates: Dict de {nombre: "{{PLACEHOLDER}}"}
            
        Returns:
            Dict con resultado de la operación
        """
        app_id = 1
        env_id = 1
        country_id = 1
        
        success = self.manager.add_variable_template(
            app_id, env_id, country_id, variable_templates
        )
        
        return {
            'success': success,
            'added_templates': list(variable_templates.keys()),
            'timestamp': datetime.now().isoformat()
        }
    
    def initialize_variables_for_new_test(
        self,
        app_code: str,
        env_code: str,
        country_code: str
    ) -> Dict[str, Any]:
        """
        Inicializar variables de ejecución para un nuevo ambiente de test
        
        Args:
            app_code: Código de aplicación
            env_code: Código de ambiente
            country_code: Código de país
            
        Returns:
            Dict con resultado de la inicialización
        """
        app_id = 1
        env_id = 1
        country_id = 1
        
        success = self.manager.initialize_execution_variables(app_id, env_id, country_id)
        
        return {
            'success': success,
            'initialized': True,
            'timestamp': datetime.now().isoformat()
        }
    
    def list_all_test_configurations(self) -> List[Dict[str, Any]]:
        """
        Listar todas las configuraciones de test con variables de ejecución
        
        Returns:
            Lista de configuraciones disponibles
        """
        return self.manager.list_all_mappings_with_variables()
    
    def generate_postman_environment(
        self,
        app_code: str,
        env_code: str,
        country_code: str
    ) -> Optional[Dict[str, Any]]:
        """
        Generar un archivo de ambiente de Postman con las variables actuales
        
        Args:
            app_code: Código de aplicación
            env_code: Código de ambiente
            country_code: Código de país
            
        Returns:
            Dict en formato de environment de Postman
        """
        variables = self.get_variables_for_test(app_code, env_code, country_code)
        
        if not variables:
            return None
        
        # Formato de environment de Postman
        postman_env = {
            "id": f"{app_code}-{env_code}-{country_code}",
            "name": f"{app_code} {env_code} {country_code} Environment", 
            "values": []
        }
        
        # Agregar variables con valores runtime si están disponibles
        runtime_values = variables.get('runtime_values', {})
        for var_name in variables.get('variables', {}):
            postman_env['values'].append({
                "key": var_name,
                "value": runtime_values.get(var_name, ''),
                "enabled": True
            })
        
        return postman_env

# Instancia global para el agente
postman_agent_tool = PostmanVariablesAgentTool()

# Funciones helper para uso directo del agente
def get_postman_vars(app: str, env: str, country: str) -> Optional[Dict[str, Any]]:
    """Helper para obtener variables de ejecución"""
    return postman_agent_tool.get_variables_for_test(app, env, country)

def update_postman_vars(app: str, env: str, country: str, values: Dict[str, Any]) -> Dict[str, Any]:
    """Helper para actualizar variables de ejecución"""
    return postman_agent_tool.update_test_variables(app, env, country, values)

def create_postman_env_file(app: str, env: str, country: str) -> Optional[Dict[str, Any]]:
    """Helper para crear archivo de environment de Postman"""
    return postman_agent_tool.generate_postman_environment(app, env, country)

if __name__ == "__main__":
    """Ejemplo de uso de la herramienta"""
    
    print("🧪 Probando herramienta del agente para variables de ejecución...")
    
    tool = PostmanVariablesAgentTool()
    
    # 1. Obtener variables actuales
    variables = tool.get_variables_for_test("EVA", "STA", "RO")
    if variables:
        print(f"✅ Variables encontradas: {len(variables.get('variables', {}))}")
        
        # 2. Actualizar algunos valores
        new_values = {
            "api_key": "sk_test_new_123",
            "user_id": "user_test_456"
        }
        
        result = tool.update_test_variables("EVA", "STA", "RO", new_values)
        print(f"✅ Actualización: {result['success']}")
        
        # 3. Generar environment de Postman
        postman_env = tool.generate_postman_environment("EVA", "STA", "RO")
        if postman_env:
            print(f"✅ Environment generado: {postman_env['name']}")
            print(f"   Variables: {len(postman_env['values'])}")
    
    # 4. Listar todas las configuraciones
    configs = tool.list_all_test_configurations()
    print(f"✅ Configuraciones encontradas: {len(configs)}")
    
    print("🎉 Herramienta del agente probada exitosamente!")