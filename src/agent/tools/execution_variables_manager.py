"""
Execution Variables Management Tool for QA Intelligence Agent

This tool allows the QA agent to manage test execution variables
stored in the app_environment_country_mappings table.

Features:
- Read current execution variables for any mapping
- Update runtime values dynamically
- Add new variable templates
- Validate variable structure
- Support variables from any source (Postman, Insomnia, custom scripts, etc.)
"""

import json
import os
import sys
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

# Add project root to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "..", ".."))

try:
    from database.connection import db_manager
    from database.models.app_environment_country_mappings import (
        AppEnvironmentCountryMapping,
    )
    from database.repositories import create_unit_of_work_factory
    from src.logging_config import get_logger
except ImportError:
    import os
    import sys

    sys.path.append(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
    from database.connection import db_manager
    from database.models.app_environment_country_mappings import (
        AppEnvironmentCountryMapping,
    )
    from database.repositories import create_unit_of_work_factory
    from src.logging_config import get_logger

logger = get_logger("ExecutionVariablesManager")


class ExecutionVariableStructure(BaseModel):
    """Pydantic model for execution_variables field structure"""

    variables: Dict[str, str] = Field(
        default_factory=dict,
        description="Template variables with placeholders like {{VAR_NAME}}",
    )
    runtime_values: Dict[str, Any] = Field(
        default_factory=dict, description="Current runtime values for the variables"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=lambda: {
            "last_updated": datetime.now(timezone.utc).isoformat(),
            "updated_by": "qa_agent",
            "version": "1.0",
        },
        description="Metadata for tracking changes",
    )


class ExecutionVariablesManager:
    """Manager class for Postman variables operations"""

    def __init__(self):
        """Initialize the manager with database connection"""
        self.uow_factory = create_unit_of_work_factory(db_manager.database_url)

    def get_mapping_variables(
        self, application_id: int, environment_id: int, country_id: int
    ) -> Optional[Dict[str, Any]]:
        """
        Get postman variables for a specific mapping

        Args:
            application_id: Application ID
            environment_id: Environment ID
            country_id: Country ID

        Returns:
            Dict with postman variables or None if not found
        """
        try:
            with self.uow_factory.create_scope() as uow:
                # Find the mapping
                mapping = uow.app_environment_country_mappings.get_by_combination(
                    app_id=application_id, env_id=environment_id, country_id=country_id
                )

                if not mapping:
                    logger.warning(
                        f"No mapping found for App:{application_id}, Env:{environment_id}, Country:{country_id}"
                    )
                    return None

                if not mapping.execution_variables:
                    logger.info("No execution_variables set for this mapping")
                    return None

                # Parse JSON if it's a string
                if isinstance(mapping.execution_variables, str):
                    return json.loads(mapping.execution_variables)

                return mapping.execution_variables

        except Exception as e:
            logger.error(f"Error getting mapping variables: {e}")
            return None

    def update_runtime_values(
        self,
        application_id: int,
        environment_id: int,
        country_id: int,
        runtime_values: Dict[str, Any],
    ) -> bool:
        """
        Update runtime values for postman variables

        Args:
            application_id: Application ID
            environment_id: Environment ID
            country_id: Country ID
            runtime_values: New runtime values to set

        Returns:
            True if successful, False otherwise
        """
        try:
            with self.uow_factory.create_scope() as uow:
                # Find the mapping
                mapping = uow.app_environment_country_mappings.get_by_combination(
                    app_id=application_id, env_id=environment_id, country_id=country_id
                )

                if not mapping:
                    logger.error(
                        f"No mapping found for App:{application_id}, Env:{environment_id}, Country:{country_id}"
                    )
                    return False

                # Get current execution_variables or create new structure
                current_vars = mapping.execution_variables or {}
                if isinstance(current_vars, str):
                    current_vars = json.loads(current_vars)

                # Ensure structure exists
                if "runtime_values" not in current_vars:
                    current_vars["runtime_values"] = {}
                if "metadata" not in current_vars:
                    current_vars["metadata"] = {}

                # Update runtime values
                current_vars["runtime_values"].update(runtime_values)

                # Update metadata
                current_vars["metadata"].update(
                    {
                        "last_updated": datetime.now(timezone.utc).isoformat(),
                        "updated_by": "qa_agent",
                    }
                )

                # Save back to mapping
                mapping.execution_variables = current_vars
                uow.app_environment_country_mappings.save(mapping)

                logger.info(f"✅ Updated runtime values for mapping {mapping.id}")
                logger.info(f"📝 Updated variables: {list(runtime_values.keys())}")

                return True

        except Exception as e:
            logger.error(f"Error updating runtime values: {e}")
            return False

    def add_variable_template(
        self,
        application_id: int,
        environment_id: int,
        country_id: int,
        variable_templates: Dict[str, str],
    ) -> bool:
        """
        Add new variable templates to postman variables

        Args:
            application_id: Application ID
            environment_id: Environment ID
            country_id: Country ID
            variable_templates: Dict of {variable_name: "{{PLACEHOLDER}}"}

        Returns:
            True if successful, False otherwise
        """
        try:
            with self.uow_factory.create_scope() as uow:
                # Find the mapping
                mapping = uow.app_environment_country_mappings.get_by_combination(
                    app_id=application_id, env_id=environment_id, country_id=country_id
                )

                if not mapping:
                    logger.error(
                        f"No mapping found for App:{application_id}, Env:{environment_id}, Country:{country_id}"
                    )
                    return False

                # Get current execution_variables or create new structure
                current_vars = mapping.execution_variables or {}
                if isinstance(current_vars, str):
                    current_vars = json.loads(current_vars)

                # Ensure structure exists
                if "variables" not in current_vars:
                    current_vars["variables"] = {}
                if "metadata" not in current_vars:
                    current_vars["metadata"] = {}

                # Add new variable templates
                current_vars["variables"].update(variable_templates)

                # Update metadata
                current_vars["metadata"].update(
                    {
                        "last_updated": datetime.now(timezone.utc).isoformat(),
                        "updated_by": "qa_agent",
                    }
                )

                # Save back to mapping
                mapping.execution_variables = current_vars
                uow.app_environment_country_mappings.save(mapping)

                logger.info(f"✅ Added variable templates for mapping {mapping.id}")
                logger.info(f"📝 New templates: {list(variable_templates.keys())}")

                return True

        except Exception as e:
            logger.error(f"Error adding variable templates: {e}")
            return False

    def initialize_execution_variables(
        self,
        application_id: int,
        environment_id: int,
        country_id: int,
        common_variables: Optional[Dict[str, str]] = None,
    ) -> bool:
        """
        Initialize execution_variables for a mapping with common Postman variables

        Args:
            application_id: Application ID
            environment_id: Environment ID
            country_id: Country ID
            common_variables: Optional custom variables, defaults to common Postman vars

        Returns:
            True if successful, False otherwise
        """
        if common_variables is None:
            common_variables = {
                "base_url": "{{BASE_URL}}",
                "api_key": "{{API_KEY}}",
                "user_id": "{{USER_ID}}",
                "tenant_id": "{{TENANT_ID}}",
                "access_token": "{{ACCESS_TOKEN}}",
                "refresh_token": "{{REFRESH_TOKEN}}",
                "correlation_id": "{{CORRELATION_ID}}",
                "content_type": "{{CONTENT_TYPE}}",
                "authorization": "{{AUTHORIZATION}}",
            }

        try:
            with self.uow_factory.create_scope() as uow:
                # Find the mapping
                mapping = uow.app_environment_country_mappings.get_by_combination(
                    app_id=application_id, env_id=environment_id, country_id=country_id
                )

                if not mapping:
                    logger.error(
                        f"No mapping found for App:{application_id}, Env:{environment_id}, Country:{country_id}"
                    )
                    return False

                # Create initial structure
                postman_structure = ExecutionVariableStructure(
                    variables=common_variables,
                    runtime_values={},
                    metadata={
                        "last_updated": datetime.now(timezone.utc).isoformat(),
                        "updated_by": "qa_agent",
                        "version": "1.0",
                    },
                )

                # Save to mapping
                mapping.execution_variables = postman_structure.model_dump()
                uow.app_environment_country_mappings.save(mapping)

                logger.info(
                    f"✅ Initialized execution_variables for mapping {mapping.id}"
                )
                logger.info(f"📝 Variables: {list(common_variables.keys())}")

                return True

        except Exception as e:
            logger.error(f"Error initializing postman variables: {e}")
            return False

    def list_all_mappings_with_variables(self) -> List[Dict[str, Any]]:
        """
        List all mappings that have execution_variables configured

        Returns:
            List of mappings with their postman variables
        """
        try:
            with self.uow_factory.create_scope() as uow:
                # Get all active mappings
                mappings = uow.app_environment_country_mappings.get_all()

                results = []
                for mapping in mappings:
                    # Only include active mappings with execution_variables
                    if mapping.is_active and mapping.execution_variables:
                        postman_vars = mapping.execution_variables
                        if isinstance(postman_vars, str):
                            postman_vars = json.loads(postman_vars)

                        results.append(
                            {
                                "mapping_id": mapping.id,
                                "application_id": mapping.application_id,
                                "environment_id": mapping.environment_id,
                                "country_id": mapping.country_id,
                                "base_url": mapping.base_url,
                                "execution_variables": postman_vars,
                                "variable_count": len(
                                    postman_vars.get("variables", {})
                                ),
                                "runtime_values_count": len(
                                    postman_vars.get("runtime_values", {})
                                ),
                            }
                        )

                logger.info(
                    f"📋 Found {len(results)} mappings with execution_variables"
                )
                return results

        except Exception as e:
            logger.error(f"Error listing mappings with variables: {e}")
            return []


# Convenience functions for direct use
def get_execution_variables(
    app_id: int, env_id: int, country_id: int
) -> Optional[Dict[str, Any]]:
    """Get postman variables for a mapping"""
    manager = ExecutionVariablesManager()
    return manager.get_mapping_variables(app_id, env_id, country_id)


def update_postman_runtime_values(
    app_id: int, env_id: int, country_id: int, values: Dict[str, Any]
) -> bool:
    """Update runtime values for postman variables"""
    manager = ExecutionVariablesManager()
    return manager.update_runtime_values(app_id, env_id, country_id, values)


def add_execution_variables(
    app_id: int, env_id: int, country_id: int, templates: Dict[str, str]
) -> bool:
    """Add variable templates to postman variables"""
    manager = ExecutionVariablesManager()
    return manager.add_variable_template(app_id, env_id, country_id, templates)


def initialize_mapping_variables(app_id: int, env_id: int, country_id: int) -> bool:
    """Initialize postman variables for a mapping"""
    manager = ExecutionVariablesManager()
    return manager.initialize_execution_variables(app_id, env_id, country_id)


if __name__ == "__main__":
    """Test the postman variables functionality"""

    manager = ExecutionVariablesManager()

    # Test initialization for existing mapping
    print("🧪 Testing postman variables management...")

    # Initialize variables for mapping 1 (assuming it exists)
    success = manager.initialize_execution_variables(1, 1, 1)
    if success:
        print("✅ Initialized postman variables")

        # Test updating runtime values
        runtime_values = {
            "base_url": "https://api-prod.example.com",
            "api_key": "sk_live_test123",
            "user_id": "user_12345",
        }

        success = manager.update_runtime_values(1, 1, 1, runtime_values)
        if success:
            print("✅ Updated runtime values")

            # Test getting variables
            variables = manager.get_mapping_variables(1, 1, 1)
            if variables:
                print("✅ Retrieved postman variables:")
                print(f"   Variables: {len(variables.get('variables', {}))}")
                print(f"   Runtime values: {len(variables.get('runtime_values', {}))}")
                print(
                    f"   Last updated: {variables.get('metadata', {}).get('last_updated')}"
                )

            # List all mappings with variables
            all_mappings = manager.list_all_mappings_with_variables()
            print(f"✅ Found {len(all_mappings)} mappings with execution_variables")

    print("🎉 Postman variables management test completed!")
