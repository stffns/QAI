"""Enhanced Postman Collection Importer for Application Endpoints.

This importer saves Postman requests to:
- application_endpoints (instead of api_requests)  
- app_environment_country_mappings.default_headers (for headers)
- application_endpoints.body (for request bodies)
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from sqlmodel import Session, select

from database.models.apps import Apps
from database.models.environments import Environments  
from database.models.countries import Countries
from database.models.application_endpoints import ApplicationEndpoint
from database.models.app_environment_country_mappings import AppEnvironmentCountryMapping

# Import the Postman Variables Manager
from src.agent.tools.execution_variables_manager import ExecutionVariablesManager


VARIABLE_PATTERN = re.compile(r"{{\s*([A-Za-z0-9_\-\.]+)\s*}}")
PATH_VAR_PATTERN = re.compile(r":([A-Za-z0-9_]+)")


class PostmanEndpointImporter:
    """Import Postman collections to application_endpoints and mappings."""
    
    def __init__(self, session: Session):
        self.session = session
        self.postman_manager = ExecutionVariablesManager()

    def import_collection(
        self,
        collection_path: Path,
        environment_path: Optional[Path] = None,
        application_code: str = "EVA",  # Default to EVA
        environment_code: str = "STA",  # Default to Staging
        country_code: Optional[str] = "RO",  # Default to Romania
    ) -> Dict[str, Any]:
        """Import Postman collection to application endpoints.
        
        Args:
            collection_path: Path to collection JSON
            environment_path: Optional environment JSON
            application_code: Application code (e.g., 'EVA', 'ONEAPP')
            environment_code: Environment code (e.g., 'STA', 'UAT', 'PRD')  
            country_code: Country code (e.g., 'RO', 'FR', 'CO')
            
        Returns:
            Dict with import summary
        """
        # Load collection
        with open(collection_path, 'r', encoding='utf-8') as f:
            collection = json.load(f)
        
        # Load environment if provided
        env_vars = {}
        env_data = None
        if environment_path and environment_path.exists():
            with open(environment_path, 'r', encoding='utf-8') as f:
                env_data = json.load(f)
                env_vars = {
                    var.get('key', ''): var.get('value', '')
                    for var in env_data.get('values', [])
                    if var.get('enabled', True)
                }

        # Get application, environment, and country (all required)
        if not country_code:
            return {"error": "Country code is required for endpoint mapping"}
            
        application = self._get_or_create_application(application_code)
        environment = self._get_environment(environment_code)
        country = self._get_country(country_code)
        
        if not application or not environment or not country:
            return {
                "error": f"Application {application_code}, environment {environment_code}, or country {country_code} not found"
            }
            
        if application.id is None or environment.id is None or country.id is None:
            return {
                "error": "Missing IDs for application, environment, or country"
            }

        # Get or create mapping
        mapping = self._get_or_create_mapping(
            application.id, environment.id, country.id, env_vars
        )
        
        if not mapping or not mapping.id:
            raise ValueError("Failed to create or find mapping")

        # Extract and save endpoints
        endpoints_created = 0
        endpoints_updated = 0
        
        items = self._flatten_collection_items(collection.get('item', []))
        
        for item in items:
            if 'request' not in item:
                continue
                
            endpoint_data = self._extract_endpoint_data(item, env_vars)
            
            # Check if endpoint already exists by unique constraint fields (new clean structure)
            existing = self.session.exec(
                select(ApplicationEndpoint).where(
                    ApplicationEndpoint.mapping_id == mapping.id,
                    ApplicationEndpoint.endpoint_name == endpoint_data['endpoint_name']
                )
            ).first()
            
            if existing:
                # Update existing endpoint
                existing.body = endpoint_data['body']
                existing.description = endpoint_data['description']
                endpoints_updated += 1
            else:
                # Create new endpoint with clean structure (only mapping_id)
                endpoint = ApplicationEndpoint(
                    mapping_id=mapping.id,
                    endpoint_name=endpoint_data['endpoint_name'],
                    endpoint_url=endpoint_data['endpoint_url'],
                    http_method=endpoint_data['http_method'],
                    body=endpoint_data['body'],
                    description=endpoint_data['description'],
                    is_active=True
                )
                self.session.add(endpoint)
                endpoints_created += 1
        
        # Extract and update Postman variables
        postman_vars_result = self.extract_and_update_execution_variables(
            collection, env_data if environment_path else None, mapping.id
        )
        
        # Commit all changes
        self.session.commit()
        
        return {
            "application": application_code,
            "environment": environment_code,
            "country": country_code,
            "mapping_id": mapping.id,
            "endpoints_created": endpoints_created,
            "endpoints_updated": endpoints_updated,
            "total_endpoints": endpoints_created + endpoints_updated,
            "execution_variables": postman_vars_result
        }

    def _get_or_create_application(self, app_code: str) -> Optional[Apps]:
        """Get or create application by code."""
        app = self.session.exec(
            select(Apps).where(Apps.app_code == app_code)
        ).first()
        
        if not app:
            # Create new application
            app = Apps(
                app_code=app_code,
                app_name=app_code,
                description=f"Application {app_code} (auto-created from Postman import)",
                is_active=True
            )
            self.session.add(app)
            self.session.commit()
            self.session.refresh(app)
        
        return app

    def _get_environment(self, env_code: str) -> Optional[Environments]:
        """Get environment by code."""
        return self.session.exec(
            select(Environments).where(Environments.env_code == env_code)
        ).first()

    def _get_country(self, country_code: str) -> Optional[Countries]:
        """Get country by code.""" 
        return self.session.exec(
            select(Countries).where(Countries.country_code == country_code)
        ).first()

    def _get_or_create_mapping(
        self, 
        app_id: int, 
        env_id: int, 
        country_id: int, 
        env_vars: Dict[str, str]
    ) -> AppEnvironmentCountryMapping:
        """Get or create app-environment-country mapping."""
        mapping = self.session.exec(
            select(AppEnvironmentCountryMapping).where(
                AppEnvironmentCountryMapping.application_id == app_id,
                AppEnvironmentCountryMapping.environment_id == env_id,
                AppEnvironmentCountryMapping.country_id == country_id
            )
        ).first()
        
        if not mapping:
            # Extract base URL from environment variables
            base_url = env_vars.get('BASE_URL', env_vars.get('baseUrl', 'https://api.example.com'))
            
            # Create new mapping with headers from environment
            default_headers = {}
            for key, value in env_vars.items():
                if 'header' in key.lower() or key.lower() in ['authorization', 'content-type', 'accept']:
                    default_headers[key] = value
                    
            mapping = AppEnvironmentCountryMapping(
                application_id=app_id,
                environment_id=env_id,
                country_id=country_id,
                base_url=base_url,
                protocol='https',
                default_headers=default_headers if default_headers else None,
                is_active=True
            )
            self.session.add(mapping)
            self.session.commit()
            self.session.refresh(mapping)
        else:
            # Update headers with new environment data
            current_headers = mapping.default_headers or {}
            for key, value in env_vars.items():
                if 'header' in key.lower() or key.lower() in ['authorization', 'content-type', 'accept']:
                    current_headers[key] = value
            
            if current_headers:
                mapping.default_headers = current_headers
                
        return mapping

    def _flatten_collection_items(self, items: List[Dict]) -> List[Dict]:
        """Flatten nested folder structure to get all requests."""
        flattened = []
        
        for item in items:
            if 'item' in item:  # It's a folder
                flattened.extend(self._flatten_collection_items(item['item']))
            else:  # It's a request
                flattened.append(item)
        
        return flattened

    def _extract_endpoint_data(self, item: Dict, env_vars: Dict[str, str]) -> Dict[str, Any]:
        """Extract endpoint data from Postman request item."""
        request = item.get('request', {})
        
        # Get method
        method = request.get('method', 'GET').upper()
        
        # Get URL
        url_data = request.get('url', {})
        if isinstance(url_data, str):
            raw_url = url_data
        else:
            raw_url = url_data.get('raw', '')
        
        # Normalize URL path 
        normalized_url = self._normalize_path(raw_url, env_vars)
        
        # Get body
        body_data = request.get('body', {})
        body = None
        if body_data:
            if body_data.get('mode') == 'raw':
                body = body_data.get('raw', '')
            elif body_data.get('mode') == 'formdata':
                # Convert form data to JSON representation
                form_items = []
                for form_item in body_data.get('formdata', []):
                    form_items.append({
                        'key': form_item.get('key', ''),
                        'value': form_item.get('value', ''),
                        'type': form_item.get('type', 'text')
                    })
                body = json.dumps({'formdata': form_items})
        
        # Get name and description - ensure uniqueness by adding method prefix
        base_name = item.get('name', normalized_url.split('?')[0])  # Remove query params from name
        name = f"{method} {base_name}"  # Add method prefix to ensure uniqueness
        description = item.get('description', f"Imported from Postman: {base_name}")
        
        return {
            'endpoint_name': name,
            'endpoint_url': normalized_url,
            'http_method': method,
            'body': body,
            'description': description
        }

    def _normalize_path(self, raw_path: str, env_vars: Dict[str, str]) -> str:
        """Normalize path by replacing variables and path parameters to extract only the endpoint path.
        
        The base URL should be in the mapping table, so we need to extract only the path portion.
        """
        # Start with the raw path
        normalized = raw_path
        
        # Step 1: Replace :param with {param} (Postman path parameters)
        normalized = PATH_VAR_PATTERN.sub(r"{\1}", normalized)
        
        # Step 2: Extract just the path part (remove protocol and domain/base URL)
        if "://" in normalized:
            try:
                from urllib.parse import urlparse
                parsed = urlparse(normalized)
                normalized = parsed.path
                if parsed.query:
                    normalized += f"?{parsed.query}"
            except:
                # Fallback: just take everything after the third slash
                parts = normalized.split('/', 3)
                if len(parts) > 3:
                    normalized = '/' + parts[3]
        else:
            # Step 3: Remove base URL, environment, and country variables from the path
            # These variables should be in the mapping table, not in endpoint paths
            infrastructure_patterns = [
                # Base URL patterns
                r'\{\{BASE_URL\}\}',
                r'\{\{baseUrl\}\}', 
                r'\{\{base_url\}\}',
                r'\{\{API_URL\}\}',
                r'\{\{api_url\}\}',
                r'\{\{HOST\}\}',
                r'\{\{host\}\}',
                # Environment patterns  
                r'\{\{ENV\}\}',
                r'\{\{env\}\}',
                r'\{\{ENVIRONMENT\}\}',
                r'\{\{environment\}\}',
                # Country patterns
                r'\{\{COUNTRY\}\}',
                r'\{\{country\}\}',
                r'\{\{REGION\}\}',
                r'\{\{region\}\}',
                # Combined patterns (common in URLs like BASE_URL-ENV)
                r'-\{\{ENV\}\}',
                r'-\{\{env\}\}',
            ]
            
            for pattern in infrastructure_patterns:
                normalized = re.sub(pattern, '', normalized, flags=re.IGNORECASE)
            
            # Clean up any double slashes, leading/trailing slashes, or orphaned dashes
            normalized = re.sub(r'/+', '/', normalized)  # Replace multiple slashes with single
            normalized = re.sub(r'/-+/', '/', normalized)  # Remove orphaned dashes between slashes  
            normalized = re.sub(r'^-+', '', normalized)    # Remove leading dashes
            normalized = normalized.strip('/')
        
        # Step 4: Convert remaining Postman variables {{var}} to {var} format
        # This handles only business logic variables like {{userId}}, {{cardId}}, etc.
        def replace_postman_var(match):
            var_name = match.group(1)
            # Skip infrastructure variables that should have been removed
            if var_name.upper() in ['ENV', 'ENVIRONMENT', 'COUNTRY', 'REGION', 'BASE_URL', 'BASEURL', 'API_URL', 'HOST']:
                return ''  # Remove any remaining infrastructure variables
            return f"{{{var_name}}}"
        
        normalized = VARIABLE_PATTERN.sub(replace_postman_var, normalized)
        
        # Step 5: Ensure it starts with / (endpoint path format)
        if not normalized.startswith('/'):
            normalized = '/' + normalized
            
        # Handle empty paths
        if normalized == '/':
            normalized = '/default'
            
        return normalized

    def extract_and_update_execution_variables(
        self, 
        collection_data: Dict[str, Any],
        environment_data: Optional[Dict[str, Any]],
        mapping_id: int
    ) -> Dict[str, Any]:
        """
        Extract Postman variables from collection and environment, update mapping
        
        Args:
            collection_data: Postman collection data
            environment_data: Postman environment data (optional)
            mapping_id: ID of the app_environment_country_mapping
            
        Returns:
            Dict with extraction results
        """
        extracted_variables = {}
        runtime_values = {}
        
        # Extract from collection variables
        if 'variable' in collection_data:
            for var in collection_data['variable']:
                var_name = var.get('key', '')
                var_value = var.get('value', '')
                if var_name:
                    extracted_variables[var_name] = f"{{{{{var_name}}}}}"
                    if var_value:
                        runtime_values[var_name] = var_value
        
        # Extract from environment variables  
        if environment_data and 'values' in environment_data:
            for var in environment_data['values']:
                var_name = var.get('key', '')
                var_value = var.get('value', '')
                if var_name:
                    extracted_variables[var_name] = f"{{{{{var_name}}}}}"
                    if var_value:
                        runtime_values[var_name] = var_value
        
        # Extract variables from collection items (URLs, headers, body)
        def extract_from_items(items):
            for item in items:
                if isinstance(item, dict):
                    if 'request' in item:
                        # Extract from URL
                        url = item['request'].get('url', '')
                        if isinstance(url, dict):
                            url = url.get('raw', '')
                        self._extract_variables_from_text(str(url), extracted_variables)
                        
                        # Extract from headers
                        headers = item['request'].get('header', [])
                        for header in headers:
                            if isinstance(header, dict):
                                self._extract_variables_from_text(header.get('key', ''), extracted_variables)
                                self._extract_variables_from_text(header.get('value', ''), extracted_variables)
                        
                        # Extract from body
                        body = item['request'].get('body', {})
                        if isinstance(body, dict):
                            raw_body = body.get('raw', '')
                            self._extract_variables_from_text(raw_body, extracted_variables)
                    
                    # Recursively check nested items (folders)
                    if 'item' in item:
                        extract_from_items(item['item'])
        
        if 'item' in collection_data:
            extract_from_items(collection_data['item'])
        
        # Get the mapping to extract its details
        mapping = self.session.get(AppEnvironmentCountryMapping, mapping_id)
        if mapping:
            # Update the mapping with extracted postman variables
            success = self.postman_manager.initialize_execution_variables(
                mapping.application_id,
                mapping.environment_id, 
                mapping.country_id,
                extracted_variables
            )
            
            if success and runtime_values:
                # Update runtime values if we have them
                self.postman_manager.update_runtime_values(
                    mapping.application_id,
                    mapping.environment_id,
                    mapping.country_id,
                    runtime_values
                )
        
        return {
            'variables_extracted': len(extracted_variables),
            'runtime_values_set': len(runtime_values),
            'variables': extracted_variables,
            'runtime_values': runtime_values
        }
    
    def _extract_variables_from_text(self, text: str, variables_dict: Dict[str, str]) -> None:
        """Extract {{variable}} patterns from text and add to variables_dict"""
        if not text:
            return
            
        matches = VARIABLE_PATTERN.findall(text)
        for var_name in matches:
            # Skip infrastructure variables that we normalize away
            if var_name.upper() not in ['ENV', 'ENVIRONMENT', 'COUNTRY', 'REGION', 'BASE_URL', 'BASEURL', 'API_URL', 'HOST']:
                variables_dict[var_name] = f"{{{{{var_name}}}}}"