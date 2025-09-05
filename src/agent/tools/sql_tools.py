"""
SQL Tools for QA Intelligence Agent - Agno SQLTools Integration

This module provides SQL analysis tools using Agno's SQLTools for advanced database exploration,
ad-hoc queries, and dynamic analysis capabilities that complement our specialized database tools.
"""
import json
from typing import Optional, List, Dict, Any
from agno.tools import tool
from agno.tools.sql import SQLTools

# Import database connection
try:
    from database.connection import db_manager
except ImportError:
    import sys
    import os
    sys.path.append(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
    from database.connection import db_manager


class QASQLTools:
    """
    QA Intelligence SQL Tools wrapper for Agno SQLTools
    
    Provides advanced SQL analysis capabilities for:
    - Dynamic database exploration
    - Ad-hoc complex queries
    - Schema analysis and debugging
    - Custom reporting and analytics
    """
    
    def __init__(self):
        """Initialize SQL Tools with QA Intelligence database"""
        self.sql_tools = SQLTools(db_engine=db_manager.engine)
    
    def execute_query(self, query: str) -> Dict[str, Any]:
        """
        Execute SQL query and return structured results
        
        Args:
            query: SQL query string
            
        Returns:
            Dictionary with query results and metadata
        """
        try:
            result = self.sql_tools.run_sql_query(query)
            
            # Parse JSON string result if needed
            if isinstance(result, str):
                try:
                    result = json.loads(result)
                except json.JSONDecodeError:
                    # If it's not JSON, treat as raw result
                    pass
            
            return {
                "status": "success",
                "query": query,
                "result": result,
                "row_count": len(result) if isinstance(result, list) else 1
            }
        except Exception as e:
            return {
                "status": "error",
                "query": query,
                "error": str(e),
                "message": f"SQL execution failed: {str(e)}"
            }
    
    def get_table_info(self, table_name: str) -> Dict[str, Any]:
        """
        Get detailed information about a specific table
        
        Args:
            table_name: Name of the table to analyze
            
        Returns:
            Dictionary with table structure and metadata
        """
        try:
            schema = self.sql_tools.describe_table(table_name)
            
            # Parse schema if it's a JSON string
            if isinstance(schema, str):
                try:
                    schema = json.loads(schema)
                except json.JSONDecodeError:
                    pass
            
            # Get record count
            count_result = self.sql_tools.run_sql_query(f"SELECT COUNT(*) as total FROM `{table_name}`")
            
            # Parse count result if it's a JSON string
            if isinstance(count_result, str):
                try:
                    count_result = json.loads(count_result)
                except json.JSONDecodeError:
                    pass
            
            record_count = 0
            if isinstance(count_result, list) and len(count_result) > 0:
                if isinstance(count_result[0], dict) and 'total' in count_result[0]:
                    record_count = count_result[0]['total']
            
            return {
                "status": "success",
                "table_name": table_name,
                "schema": schema,
                "record_count": record_count,
                "columns": len(schema) if isinstance(schema, list) else 0
            }
        except Exception as e:
            return {
                "status": "error",
                "table_name": table_name,
                "error": str(e),
                "message": f"Failed to analyze table '{table_name}': {str(e)}"
            }
    
    def explore_database(self) -> Dict[str, Any]:
        """
        Explore the entire database structure
        
        Returns:
            Dictionary with database overview and table information
        """
        try:
            tables_raw = self.sql_tools.list_tables()
            
            # Parse tables if it's a JSON string
            if isinstance(tables_raw, str):
                try:
                    tables = json.loads(tables_raw)
                except json.JSONDecodeError:
                    # If not JSON, treat as raw list or split by common delimiters
                    if ',' in tables_raw:
                        tables = [t.strip(' "[]') for t in tables_raw.split(',')]
                    else:
                        tables = [tables_raw]
            else:
                tables = tables_raw if isinstance(tables_raw, list) else [str(tables_raw)]
            
            table_details = []
            qa_core_tables = []
            
            for table in tables:
                # Clean table name
                table_name = table.strip(' "[]') if isinstance(table, str) else str(table)
                
                # Skip empty or invalid table names
                if not table_name or len(table_name) < 2:
                    continue
                
                try:
                    # Get basic info for each table
                    count_result = self.sql_tools.run_sql_query(f"SELECT COUNT(*) as total FROM `{table_name}`")
                    
                    # Parse count result
                    if isinstance(count_result, str):
                        try:
                            count_result = json.loads(count_result)
                        except json.JSONDecodeError:
                            pass
                    
                    record_count = 0
                    if isinstance(count_result, list) and len(count_result) > 0:
                        if isinstance(count_result[0], dict) and 'total' in count_result[0]:
                            record_count = count_result[0]['total']
                    
                    table_info = {
                        "table_name": table_name,
                        "record_count": record_count
                    }
                    
                    table_details.append(table_info)
                    
                    # Identify QA core tables
                    if any(keyword in table_name.lower() for keyword in 
                           ['apps_master', 'countries_master', 'application_country_mapping', 
                            'test_', 'performance_', 'audit_', 'environments']):
                        qa_core_tables.append(table_info)
                        
                except Exception as e:
                    table_details.append({
                        "table_name": table_name,
                        "record_count": "unknown",
                        "error": str(e)
                    })
            
            return {
                "status": "success",
                "total_tables": len(table_details),
                "tables": table_details,
                "qa_core_tables": qa_core_tables,
                "summary": {
                    "total_tables": len(table_details),
                    "qa_tables": len(qa_core_tables),
                    "unknown_counts": len([t for t in table_details if t.get("record_count") == "unknown"])
                }
            }
            
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "message": f"Database exploration failed: {str(e)}"
            }


# Initialize global instance
qa_sql_tools = QASQLTools()


# Raw functions for direct calling
def sql_execute_query_raw(query: str) -> str:
    """Execute SQL query - raw function for direct calling"""
    qa_sql = QASQLTools()
    result = qa_sql.execute_query(query)
    return json.dumps(result, indent=2)

def sql_analyze_table_raw(table_name: str) -> str:
    """Analyze table - raw function for direct calling"""
    qa_sql = QASQLTools()
    result = qa_sql.get_table_info(table_name)
    return json.dumps(result, indent=2)

def sql_explore_database_raw() -> str:
    """Explore database - raw function for direct calling"""
    qa_sql = QASQLTools()
    result = qa_sql.explore_database()
    return json.dumps(result, indent=2)

def sql_qa_analytics_raw(analysis_type: str = "deployment_summary") -> str:
    """QA analytics - raw function for direct calling"""
    # Analytics queries
    queries = {
        "deployment_summary": """
            SELECT 
                c.region,
                COUNT(DISTINCT a.app_code) as unique_apps,
                COUNT(m.mapping_id) as total_deployments,
                GROUP_CONCAT(DISTINCT a.app_code) as apps_list
            FROM countries_master c
            LEFT JOIN application_country_mapping m ON c.id = m.country_id AND m.is_active = 1
            LEFT JOIN apps_master a ON m.application_id = a.id
            GROUP BY c.region
            ORDER BY total_deployments DESC
        """,
        "regional_analysis": """
            SELECT 
                c.region,
                c.currency_code,
                COUNT(c.id) as countries_count,
                COUNT(m.mapping_id) as active_deployments,
                ROUND(COUNT(m.mapping_id) * 1.0 / COUNT(c.id), 2) as deployment_ratio
            FROM countries_master c
            LEFT JOIN application_country_mapping m ON c.id = m.country_id AND m.is_active = 1
            GROUP BY c.region, c.currency_code
            ORDER BY deployment_ratio DESC
        """
    }
    
    if analysis_type not in queries:
        return json.dumps({
            "status": "error",
            "error": f"Unknown analysis type: {analysis_type}",
            "available_types": list(queries.keys())
        }, indent=2)
    
    qa_sql = QASQLTools()
    result = qa_sql.execute_query(queries[analysis_type])
    result["analysis_type"] = analysis_type
    return json.dumps(result, indent=2)


# Agno @tool decorated functions for the agent
@tool(
    name="sql_execute_query",
    description="Execute custom SQL queries for advanced database analysis and reporting. Use for complex joins, aggregations, and custom analytics.",
    show_result=False
)
def sql_execute_query(query: str) -> str:
    """
    Execute a custom SQL query for advanced database analysis.
    
    Use this tool for:
    - Complex joins between multiple tables
    - Advanced aggregations and analytics
    - Custom reporting requirements
    - Data validation and debugging
    
    Args:
        query: SQL query string to execute
    
    Returns:
        str: JSON string with query results
    """
    return sql_execute_query_raw(query)


@tool(
    name="sql_analyze_table",
    description="Analyze the structure and content of a specific database table. Get schema, column types, and record counts.",
    show_result=False
)
def sql_analyze_table(table_name: str) -> str:
    """
    Analyze the structure and content of a specific database table.
    
    Use this tool for:
    - Understanding table schemas
    - Checking data types and constraints
    - Getting record counts
    - Table structure exploration
    
    Args:
        table_name: Name of the table to analyze
    
    Returns:
        str: JSON string with table analysis
    """
    return sql_analyze_table_raw(table_name)


@tool(
    name="sql_explore_database",
    description="Explore the entire database structure to discover all tables and get an overview of the data model.",
    show_result=False
)
def sql_explore_database() -> str:
    """
    Explore the entire database structure and get an overview.
    
    Use this tool for:
    - Discovering all available tables
    - Getting database overview
    - Understanding data model structure
    - Initial database exploration
    
    Returns:
        str: JSON string with database exploration results
    """
    return sql_explore_database_raw()


@tool(
    name="sql_qa_analytics",
    description="Perform specialized QA analytics queries for deployment analysis, regional statistics, and app performance metrics.",
    show_result=False
)
def sql_qa_analytics(analysis_type: str = "deployment_summary") -> str:
    """
    Perform specialized QA analytics using predefined complex queries.
    
    Available analysis types:
    - deployment_summary: Apps deployment across regions
    - regional_analysis: Regional deployment patterns
    
    Args:
        analysis_type: Type of analysis to perform
    
    Returns:
        str: JSON string with analytics results
    """
    return sql_qa_analytics_raw(analysis_type)
