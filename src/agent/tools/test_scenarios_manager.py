"""
Test Scenarios Manager - Gestión de escenarios de testing

Proporciona funciones para crear, gestionar y ejecutar escenarios de testing
que agrupan endpoints para diferentes propósitos (performance, functional, smoke, etc.)
"""

from datetime import datetime, timezone
from typing import List, Dict, Any, Optional, Union
from pathlib import Path
from sqlmodel import select
from sqlalchemy import and_, or_

try:
    from database.connection import db_manager
    from database.repositories.unit_of_work import UnitOfWorkFactory
    from database.models.test_scenarios import TestScenario, TestScenarioEndpoint, TestScenarioType
    from database.models.app_environment_country_mappings import AppEnvironmentCountryMapping
    from database.models.application_endpoints import ApplicationEndpoint
    from src.logging_config import get_logger
except ImportError:
    import sys
    import os
    sys.path.append(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
    from database.connection import db_manager
    from database.repositories.unit_of_work import UnitOfWorkFactory
    from database.models.test_scenarios import TestScenario, TestScenarioEndpoint, TestScenarioType
    from database.models.app_environment_country_mappings import AppEnvironmentCountryMapping  
    from database.models.application_endpoints import ApplicationEndpoint
    from src.logging_config import get_logger

logger = get_logger("TestScenariosManager")


class TestScenarioManager:
    """Manager para operaciones de escenarios de testing"""
    
    def __init__(self):
        """Inicializar el manager"""
        self.engine = db_manager.engine
        self.uow_factory = UnitOfWorkFactory(self.engine)
    
    def create_scenario(
        self,
        mapping_id: int,
        scenario_name: str,
        scenario_type: Union[str, TestScenarioType],
        description: Optional[str] = None,
        config: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Crear un nuevo escenario de testing
        
        Args:
            mapping_id: ID del mapping (app+env+country)
            scenario_name: Nombre del escenario
            scenario_type: Tipo de escenario
            description: Descripción opcional
            config: Configuración específica del escenario
            **kwargs: Parámetros adicionales del escenario
            
        Returns:
            Dict con resultado de la operación
        """
        try:
            if isinstance(scenario_type, str):
                scenario_type = TestScenarioType(scenario_type.upper())
            
            with self.uow_factory.create_scope() as uow:
                session = uow.session
                
                # Verificar que el mapping existe usando consulta directa
                stmt_check = select(AppEnvironmentCountryMapping.id).where(AppEnvironmentCountryMapping.id == mapping_id)
                existing_mapping = session.exec(stmt_check).first()
                if not existing_mapping:
                    return {
                        "success": False,
                        "error": f"Mapping {mapping_id} not found"
                    }
                
                # Verificar que no existe un escenario con el mismo nombre
                existing = session.query(TestScenario).filter_by(
                    mapping_id=mapping_id,
                    scenario_name=scenario_name
                ).first()
                
                if existing:
                    return {
                        "success": False,
                        "error": f"Scenario '{scenario_name}' already exists for this mapping"
                    }
                
                # Crear el escenario
                scenario_data = {
                    "mapping_id": mapping_id,
                    "scenario_name": scenario_name,
                    "scenario_type": scenario_type,
                    "description": description,
                    "config": config,
                    "created_at": datetime.now(timezone.utc)
                }
                
                # Agregar parámetros opcionales
                for key, value in kwargs.items():
                    if hasattr(TestScenario, key):
                        scenario_data[key] = value
                
                scenario = TestScenario(**scenario_data)
                session.add(scenario)
                session.flush()  # Para obtener el ID
                
                logger.info(f"✅ Created scenario '{scenario_name}' (ID: {scenario.id}) for mapping {mapping_id}")
                
                return {
                    "success": True,
                    "scenario_id": scenario.id,
                    "scenario": {
                        "id": scenario.id,
                        "name": scenario_name,
                        "type": scenario_type.value,
                        "mapping_id": mapping_id,
                        "description": description
                    }
                }
                
        except Exception as e:
            logger.error(f"❌ Error creating scenario: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def add_endpoints_to_scenario(
        self,
        scenario_id: int,
        endpoint_ids: List[int],
        auto_order: bool = True,
        **endpoint_config
    ) -> Dict[str, Any]:
        """
        Agregar endpoints a un escenario
        
        Args:
            scenario_id: ID del escenario
            endpoint_ids: Lista de IDs de endpoints
            auto_order: Si auto-ordenar por tipo de método HTTP
            **endpoint_config: Configuración por defecto para todos los endpoints
            
        Returns:
            Dict con resultado de la operación
        """
        try:
            with self.uow_factory.create_scope() as uow:
                session = uow.session
                
                # Verificar que el escenario existe
                scenario = session.get(TestScenario, scenario_id)
                if not scenario:
                    return {
                        "success": False,
                        "error": f"Scenario {scenario_id} not found"
                    }
                
                added_endpoints = []
                skipped_endpoints = []
                
                # Definir orden por método HTTP para auto_order
                method_priority = {
                    'GET': 1,
                    'POST': 2,
                    'PUT': 3,
                    'PATCH': 4,
                    'DELETE': 5,
                    'HEAD': 6,
                    'OPTIONS': 7
                }
                
                for i, endpoint_id in enumerate(endpoint_ids):
                    # Verificar que el endpoint existe y pertenece al mismo mapping
                    endpoint = session.get(ApplicationEndpoint, endpoint_id)
                    if not endpoint:
                        skipped_endpoints.append({
                            "endpoint_id": endpoint_id,
                            "reason": "Endpoint not found"
                        })
                        continue
                    
                    if endpoint.mapping_id != scenario.mapping_id:
                        skipped_endpoints.append({
                            "endpoint_id": endpoint_id,
                            "reason": "Endpoint belongs to different mapping"
                        })
                        continue
                    
                    # Verificar si ya existe la relación
                    existing = session.query(TestScenarioEndpoint).filter_by(
                        scenario_id=scenario_id,
                        endpoint_id=endpoint_id
                    ).first()
                    
                    if existing:
                        skipped_endpoints.append({
                            "endpoint_id": endpoint_id,
                            "reason": "Already in scenario"
                        })
                        continue
                    
                    # Calcular orden de ejecución
                    if auto_order:
                        execution_order = method_priority.get(endpoint.http_method, 99) * 100 + i
                    else:
                        execution_order = i + 1
                    
                    # Configurar peso basado en el tipo de escenario
                    weight = endpoint_config.get("weight", 1)
                    if scenario.scenario_type == TestScenarioType.PERFORMANCE:
                        weight = 5 if endpoint.http_method == 'GET' else 2
                    
                    # Crear la relación
                    scenario_endpoint = TestScenarioEndpoint(
                        scenario_id=scenario_id,
                        endpoint_id=endpoint_id,
                        execution_order=execution_order,
                        weight=weight,
                        **{k: v for k, v in endpoint_config.items() if k != "weight"}
                    )
                    
                    session.add(scenario_endpoint)
                    added_endpoints.append({
                        "endpoint_id": endpoint_id,
                        "endpoint_name": endpoint.endpoint_name,
                        "method": endpoint.http_method,
                        "execution_order": execution_order
                    })
                
                logger.info(f"✅ Added {len(added_endpoints)} endpoints to scenario {scenario_id}")
                if skipped_endpoints:
                    logger.warning(f"⚠️ Skipped {len(skipped_endpoints)} endpoints")
                
                return {
                    "success": True,
                    "added_count": len(added_endpoints),
                    "skipped_count": len(skipped_endpoints),
                    "added_endpoints": added_endpoints,
                    "skipped_endpoints": skipped_endpoints
                }
                
        except Exception as e:
            logger.error(f"❌ Error adding endpoints to scenario: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def get_scenario_with_endpoints(self, scenario_id: int) -> Optional[Dict[str, Any]]:
        """
        Obtener un escenario completo con sus endpoints
        
        Args:
            scenario_id: ID del escenario
            
        Returns:
            Dict con datos del escenario y endpoints, o None si no existe
        """
        try:
            with self.uow_factory.create_scope() as uow:
                session = uow.session
                
                scenario = session.get(TestScenario, scenario_id)
                if not scenario:
                    return None
                
                # Obtener endpoints del escenario ordenados
                stmt = (
                    select(TestScenarioEndpoint, ApplicationEndpoint)
                    .join(ApplicationEndpoint)
                    .where(TestScenarioEndpoint.scenario_id == scenario_id)
                    .where(TestScenarioEndpoint.is_active == True)  # type: ignore
                    .order_by(TestScenarioEndpoint.execution_order)  # type: ignore
                )
                scenario_endpoints = session.exec(stmt).all()
                
                endpoints_data = []
                for se, endpoint in scenario_endpoints:
                    endpoints_data.append({
                        "scenario_endpoint_id": se.id,
                        "endpoint_id": endpoint.id,
                        "endpoint_name": endpoint.endpoint_name,
                        "endpoint_url": endpoint.endpoint_url,
                        "http_method": endpoint.http_method,
                        "execution_order": se.execution_order,
                        "is_critical": se.is_critical,
                        "weight": se.weight,
                        "custom_timeout_ms": se.custom_timeout_ms,
                        "expected_status_codes": se.expected_status_codes,
                        "depends_on_endpoint_ids": se.depends_on_endpoint_ids,
                        "notes": se.notes
                    })
                
                return {
                    "id": scenario.id,
                    "name": scenario.scenario_name,
                    "type": scenario.scenario_type.value,
                    "description": scenario.description,
                    "mapping_id": scenario.mapping_id,
                    "config": scenario.config,
                    "max_execution_time_minutes": scenario.max_execution_time_minutes,
                    "target_concurrent_users": scenario.target_concurrent_users,
                    "ramp_up_time_seconds": scenario.ramp_up_time_seconds,
                    "retry_failed_endpoints": scenario.retry_failed_endpoints,
                    "stop_on_critical_failure": scenario.stop_on_critical_failure,
                    "priority": scenario.priority,
                    "is_active": scenario.is_active,
                    "created_at": scenario.created_at,
                    "endpoints": endpoints_data,
                    "total_endpoints": len(endpoints_data)
                }
                
        except Exception as e:
            logger.error(f"❌ Error getting scenario {scenario_id}: {e}")
            return None
    
    def list_scenarios_by_mapping(self, mapping_id: int) -> List[Dict[str, Any]]:
        """
        Listar todos los escenarios de un mapping
        
        Args:
            mapping_id: ID del mapping
            
        Returns:
            Lista de escenarios con resumen
        """
        try:
            with self.uow_factory.create_scope() as uow:
                session = uow.session
                
                stmt = (
                    select(TestScenario)
                    .where(TestScenario.mapping_id == mapping_id)
                    .where(TestScenario.is_active == True)  # type: ignore
                    .order_by(TestScenario.priority, TestScenario.scenario_name)  # type: ignore
                )
                scenarios = session.exec(stmt).all()
                
                results = []
                for scenario in scenarios:
                    # Contar endpoints
                    stmt_count = (
                        select(TestScenarioEndpoint)
                        .where(TestScenarioEndpoint.scenario_id == scenario.id)
                        .where(TestScenarioEndpoint.is_active == True)  # type: ignore
                    )
                    endpoints_count = len(session.exec(stmt_count).all())
                    
                    results.append({
                        "id": scenario.id,
                        "name": scenario.scenario_name,
                        "type": scenario.scenario_type.value,
                        "description": scenario.description,
                        "endpoints_count": endpoints_count,
                        "priority": scenario.priority,
                        "target_concurrent_users": scenario.target_concurrent_users,
                        "max_execution_time_minutes": scenario.max_execution_time_minutes,
                        "created_at": scenario.created_at
                    })
                
                return results
                
        except Exception as e:
            logger.error(f"❌ Error listing scenarios for mapping {mapping_id}: {e}")
            return []
    
    def create_performance_scenario_for_mapping(
        self,
        mapping_id: int,
        concurrent_users: int = 10,
        ramp_up_seconds: int = 30,
        scenario_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Crear un escenario de performance optimizado para un mapping
        
        Args:
            mapping_id: ID del mapping
            concurrent_users: Usuarios concurrentes
            ramp_up_seconds: Tiempo de ramp-up
            scenario_name: Nombre personalizado del escenario
            
        Returns:
            Dict con resultado de la operación
        """
        try:
            if not scenario_name:
                scenario_name = f"Performance Test - {concurrent_users} users"
            
            # Crear el escenario
            result = self.create_scenario(
                mapping_id=mapping_id,
                scenario_name=scenario_name,
                scenario_type=TestScenarioType.PERFORMANCE,
                description=f"Performance testing with {concurrent_users} concurrent users",
                target_concurrent_users=concurrent_users,
                ramp_up_time_seconds=ramp_up_seconds,
                max_execution_time_minutes=15,
                stop_on_critical_failure=True
            )
            
            if not result["success"]:
                return result
            
            scenario_id = result["scenario_id"]
            
            # Buscar endpoints GET para performance (más seguros)
            with self.uow_factory.create_scope() as uow:
                session = uow.session
                
                stmt_endpoints = (
                    select(ApplicationEndpoint)
                    .where(ApplicationEndpoint.mapping_id == mapping_id)
                    .where(ApplicationEndpoint.http_method == 'GET')
                    .where(ApplicationEndpoint.endpoint_url.contains('/'))  # type: ignore
                    .order_by(ApplicationEndpoint.endpoint_name)  # type: ignore
                )
                get_endpoints = session.exec(stmt_endpoints).all()
                
                if get_endpoints:
                    endpoint_ids = [ep.id for ep in get_endpoints if ep.id is not None]
                    add_result = self.add_endpoints_to_scenario(
                        scenario_id=scenario_id,
                        endpoint_ids=endpoint_ids,
                        is_critical=True,
                        weight=5
                    )
                    
                    result["endpoints_added"] = add_result.get("added_count", 0)
                
            logger.info(f"✅ Created performance scenario for mapping {mapping_id}: {scenario_name}")
            return result
            
        except Exception as e:
            logger.error(f"❌ Error creating performance scenario: {e}")
            return {
                "success": False,
                "error": str(e)
            }


# Funciones helper para uso directo
def create_default_scenarios_for_mapping(mapping_id: int) -> Dict[str, Any]:
    """Crear escenarios por defecto para un mapping"""
    manager = TestScenarioManager()
    
    results = {
        "mapping_id": mapping_id,
        "created_scenarios": [],
        "errors": []
    }
    
    # SMOKE scenario
    smoke_result = manager.create_scenario(
        mapping_id=mapping_id,
        scenario_name="Smoke Test",
        scenario_type=TestScenarioType.SMOKE,
        description="Basic endpoint availability validation",
        max_execution_time_minutes=5,
        priority=1
    )
    
    if smoke_result["success"]:
        results["created_scenarios"].append("SMOKE")
    else:
        results["errors"].append(f"SMOKE: {smoke_result.get('error')}")
    
    # FUNCTIONAL scenario
    functional_result = manager.create_scenario(
        mapping_id=mapping_id,
        scenario_name="Functional Test",
        scenario_type=TestScenarioType.FUNCTIONAL,
        description="Complete functional testing coverage",
        max_execution_time_minutes=30,
        priority=2
    )
    
    if functional_result["success"]:
        results["created_scenarios"].append("FUNCTIONAL")
    else:
        results["errors"].append(f"FUNCTIONAL: {functional_result.get('error')}")
    
    return results


if __name__ == "__main__":
    """Demo del sistema de escenarios"""
    print("🎭 Test Scenarios Manager Demo")
    
    manager = TestScenarioManager()
    
    # Listar escenarios existentes usando solo campos básicos
    with manager.uow_factory.create_scope() as uow:
        session = uow.session
        
        # Usar consulta más simple con campos que sabemos que existen
        stmt_mappings = select(AppEnvironmentCountryMapping.id, AppEnvironmentCountryMapping.application_id).limit(3)
        results = session.exec(stmt_mappings).all()
        
        print(f"🔍 Found {len(results)} mappings to demo")
        
        for mapping_id, app_id in results:
            if mapping_id is None:
                continue
            print(f"\n📍 Mapping {mapping_id} (App: {app_id}) scenarios:")
            scenarios = manager.list_scenarios_by_mapping(mapping_id)
            
            if not scenarios:
                print("   No scenarios found")
                continue
                
            for scenario in scenarios:
                print(f"   🎭 {scenario['name']} ({scenario['type']}) - {scenario['endpoints_count']} endpoints")
    
    print("\n🎉 Scenarios demo completed!")