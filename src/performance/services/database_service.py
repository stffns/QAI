"""
Database Service - Database operations abstraction

Handles all database operations:
- Session management
- Repository access
- Transaction handling

Single responsibility: database access layer.
"""
from typing import List, Optional, Any
from contextlib import contextmanager


class DatabaseService:
    """Service for database operations."""
    
    def __init__(self, db_manager):
        """Initialize with injected database manager."""
        self.db_manager = db_manager
        self._repositories = {}
    
    @contextmanager
    def get_session(self):
        """Get database session context manager."""
        with self.db_manager.get_session() as session:
            yield session
    
    def _get_repository(self, repo_class, session):
        """Get repository instance with caching."""
        repo_name = repo_class.__name__
        if repo_name not in self._repositories:
            self._repositories[repo_name] = repo_class(session)
        return self._repositories[repo_name]
    
    def get_all_applications(self) -> List[Any]:
        """Get all applications from database."""
        # Import here to avoid circular dependencies
        from database.repositories.apps_repository import AppsRepository
        
        with self.get_session() as session:
            apps_repo = AppsRepository(session)
            return list(apps_repo.get_all())
    
    def get_all_environments(self) -> List[Any]:
        """Get all environments from database."""
        from database.repositories.performance import EnvironmentsRepository
        
        with self.get_session() as session:
            env_repo = EnvironmentsRepository(session)
            return list(env_repo.get_all())
    
    def get_all_countries(self) -> List[Any]:
        """Get all countries from database."""
        from database.repositories.countries_repository import CountriesRepository
        
        with self.get_session() as session:
            countries_repo = CountriesRepository(session)
            return list(countries_repo.get_all())
    
    def get_enhanced_configurations(self, app_code: Optional[str] = None,
                                  env_code: Optional[str] = None,
                                  country_code: Optional[str] = None) -> List[Any]:
        """Get enhanced configurations with filters."""
        from database.repositories.app_environment_country_mappings_repository import AppEnvironmentCountryMappingRepository
        
        with self.get_session() as session:
            # TODO: Update to use new unified mapping repository
            # mappings_repo = AppEnvironmentCountryMappingRepository(session)
            # return mappings_repo.list_configurations(...)
            return []  # Temporary placeholder
    
    def get_performance_tests(self, limit: Optional[int] = None) -> List[dict]:
        """Get performance test records as dictionaries to avoid session issues."""
        from database.repositories.performance import PerformanceTestExecutionsRepository
        
        with self.get_session() as session:
            perf_repo = PerformanceTestExecutionsRepository(session)
            
            # Get all objects within session context
            if limit:
                objects = list(perf_repo.get_all())[:limit]
            else:
                objects = list(perf_repo.get_all())
            
            # Convert to dictionaries while session is active to avoid detached instance errors
            results = []
            for obj in objects:
                try:
                    # Access all attributes while session is active
                    result_dict = {
                        'execution_id': getattr(obj, 'execution_id', None),
                        'created_at': getattr(obj, 'created_at', None),
                        'status': getattr(obj, 'status', None),
                        'app_name': getattr(obj, 'app_name', None),
                        'country_name': getattr(obj, 'country_name', None),
                        'execution_time': getattr(obj, 'execution_time', None),
                        'execution_details': getattr(obj, 'execution_details', {}),
                        'start_time': getattr(obj, 'start_time', None),
                        'end_time': getattr(obj, 'end_time', None),
                        'error_message': getattr(obj, 'error_message', None)
                    }
                    results.append(result_dict)
                except Exception as attr_error:
                    # If any attribute access fails, create minimal dict
                    results.append({
                        'execution_id': f'error_accessing_obj_{len(results)}',
                        'created_at': None,
                        'status': 'error',
                        'app_name': 'unknown',
                        'country_name': 'unknown',
                        'execution_time': None,
                        'execution_details': {'error': str(attr_error)},
                        'start_time': None,
                        'end_time': None,
                        'error_message': f'Attribute access error: {attr_error}'
                    })
            
            return results
    
    def save_performance_test(self, test_data: dict) -> Any:
        """Save performance test to database."""
        from database.repositories.performance import PerformanceTestExecutionsRepository
        from database.models.performance import PerformanceTestExecutions
        
        with self.get_session() as session:
            perf_repo = PerformanceTestExecutionsRepository(session)
            # Create entity from data
            entity = PerformanceTestExecutions(**test_data)
            return perf_repo.save(entity)
    
    def get_test_by_execution_id(self, execution_id: str) -> Optional[Any]:
        """Get test by execution ID."""
        from database.repositories.performance import PerformanceTestExecutionsRepository
        
        with self.get_session() as session:
            perf_repo = PerformanceTestExecutionsRepository(session)
            # Use find_one_by which is available in base repository
            return perf_repo.find_one_by(execution_id=execution_id)

    def persist_execution_to_db(self, execution_result, command: str, params: dict, config_json: str):
        """Persist execution to database for cross-instance tracking"""
        try:
            from sqlalchemy import text
            from datetime import datetime
            import json
            
            with self.get_session() as session:
                # Insert into batch_executions table
                insert_sql = text("""
                    INSERT INTO batch_executions 
                    (execution_id, batch_name, batch_status, status, app_name, country_name, 
                     execution_time, started_at, execution_details, simulation_data, created_at, 
                     test_type_name, updated_at)
                    VALUES 
                    (:execution_id, :batch_name, :batch_status, :status, :app_name, :country_name,
                     :execution_time, :started_at, :execution_details, :simulation_data, :created_at,
                     :test_type_name, :updated_at)
                """)
                
                # Prepare data
                now = datetime.now()
                app_name = params.get('app_code', 'unknown')
                country_name = params.get('country_code', 'unknown')
                
                session.execute(insert_sql, {
                    'execution_id': execution_result.execution_id,
                    'batch_name': f"{app_name}_{execution_result.execution_id[:8]}",
                    'batch_status': execution_result.status.value,
                    'status': execution_result.status.value,
                    'app_name': app_name,
                    'country_name': country_name,
                    'execution_time': now,
                    'started_at': now,
                    'execution_details': json.dumps({
                        'command': command,
                        'parameters': params,
                        'estimated_duration_minutes': execution_result.estimated_duration_minutes,
                        'submitted_at': execution_result.submitted_at
                    }),
                    'simulation_data': config_json,
                    'created_at': now,
                    'test_type_name': 'performance_v2',
                    'updated_at': now
                })
                session.commit()
                
        except Exception as e:
            # Don't fail the execution if DB persistence fails
            import traceback
            print(f"Warning: Failed to persist execution to DB: {e}")
            print(traceback.format_exc())

    def get_execution_from_db(self, execution_id: str) -> dict:
        """Get execution info from database"""
        try:
            from sqlalchemy import text
            import json
            
            with self.get_session() as session:
                result = session.execute(
                    text("SELECT * FROM batch_executions WHERE execution_id = :execution_id"),
                    {'execution_id': execution_id}
                )
                row = result.fetchone()
                
                if row:
                    # Convert row to dict
                    columns = result.keys()
                    execution_data = dict(zip(columns, row))
                    
                    # Parse JSON fields
                    if execution_data.get('execution_details'):
                        try:
                            execution_data['execution_details'] = json.loads(execution_data['execution_details'])
                        except:
                            pass
                    
                    return execution_data
                    
        except Exception as e:
            print(f"Warning: Failed to get execution from DB: {e}")
        
        return {}

    def save_endpoints_data_to_db(self, execution_id: str, endpoints_data: list) -> None:
        """Save the endpoints tested to database for visibility"""
        if not endpoints_data:
            return
            
        try:
            from sqlalchemy import text
            import json
            
            endpoints_summary = {
                "endpoints_count": len(endpoints_data),
                "endpoints_tested": [
                    {
                        "name": ep.get("endpoint_name", "Unknown"),
                        "url": ep.get("endpoint_url", "Unknown"), 
                        "method": ep.get("http_method", "GET"),
                        "description": ep.get("description", ""),
                        "is_active": ep.get("is_active", True)
                    }
                    for ep in endpoints_data
                ]
            }
            
            with self.get_session() as session:
                session.execute(
                    text("""
                        UPDATE batch_executions 
                        SET execution_details = json_set(
                            COALESCE(execution_details, '{}'),
                            '$.endpoints_tested', :endpoints_data
                        )
                        WHERE execution_id = :exec_id
                    """),
                    {
                        'exec_id': execution_id,
                        'endpoints_data': json.dumps(endpoints_summary)
                    }
                )
                session.commit()
                
                print(f"✅ Endpoints data saved to DB for execution {execution_id}: {len(endpoints_data)} endpoints")
                
        except Exception as e:
            print(f"Warning: Failed to save endpoints data: {e}")
