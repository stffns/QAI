#!/usr/bin/env python3
"""
Debug script to understand Agno tool validation requirements
"""

import sys
import os

# Add project root to path
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

def debug_tool_validation():
    """Debug what the tool validation is expecting"""
    print("🔍 Debugging Agno tool validation")
    print("=" * 50)
    
    try:
        from src.agent.tools.database_tools import database_stats
        
        print(f"Tool type: {type(database_stats)}")
        print(f"Tool name: {database_stats.name if hasattr(database_stats, 'name') else 'No name'}")
        
        # Check validation criteria
        print(f"Is callable: {callable(database_stats)}")
        print(f"Has run method: {hasattr(database_stats, 'run')}")
        print(f"Run is callable: {hasattr(database_stats, 'run') and callable(getattr(database_stats, 'run'))}")
        print(f"Is dict: {isinstance(database_stats, dict)}")
        print(f"Has functions: {hasattr(database_stats, 'functions')}")
        
        # Check specific Agno Function attributes
        if hasattr(database_stats, '__class__'):
            print(f"Class: {database_stats.__class__}")
            print(f"Module: {database_stats.__class__.__module__}")
        
        # Look for tool-specific methods
        tool_methods = [attr for attr in dir(database_stats) if not attr.startswith('_')]
        print(f"Public methods: {tool_methods[:10]}...")  # Show first 10
        
        # Check the agno Function interface
        if hasattr(database_stats, 'entrypoint'):
            print(f"Has entrypoint: {database_stats.entrypoint}")
        
        # Try to examine the internal function
        if hasattr(database_stats, '__wrapped__'):
            print(f"Wrapped function: {database_stats.__wrapped__}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_tool_validation()
