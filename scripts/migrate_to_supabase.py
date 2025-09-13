#!/usr/bin/env python3
"""
Migration script for QA Intelligence: SQLite to Supabase PostgreSQL
This script helps migrate data and validate the new database setup
"""

import asyncio
import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from sqlmodel import create_engine, Session, SQLModel, text
from database.connection import DatabaseManager
from config.supabase import get_supabase_config, is_supabase_configured, get_database_url


def check_supabase_connection():
    """Test Supabase connection and configuration"""
    print("🔍 Checking Supabase configuration...")
    
    if not is_supabase_configured():
        print("❌ Supabase not configured. Please set up .env.supabase first")
        return False
    
    config = get_supabase_config()
    print(f"✅ Supabase URL: {config.supabase_url}")
    print(f"✅ Database URL configured: {bool(config.database_url)}")
    
    # Test database connection
    print("🔍 Testing database connection...")
    try:
        db_manager = DatabaseManager(database_url=config.database_url)
        if db_manager.health_check():
            print("✅ Database connection successful!")
            return True
        else:
            print("❌ Database connection failed")
            return False
    except Exception as e:
        print(f"❌ Connection error: {e}")
        return False


def create_tables():
    """Create all tables in the new PostgreSQL database"""
    print("🏗️ Creating tables in PostgreSQL database...")
    
    try:
        db_manager = DatabaseManager()
        db_manager.create_db_and_tables()
        print("✅ All tables created successfully!")
        return True
    except Exception as e:
        print(f"❌ Error creating tables: {e}")
        return False


def validate_models():
    """Validate that all SQLModel models are properly configured"""
    print("🔍 Validating SQLModel models...")
    
    try:
        # Import all models to register them
        from database.models import (
            User, AuditLog, UserRole, Apps, Environments, Countries,
            AppEnvironmentCountryMapping, ApplicationEndpoint
        )
        
        # Import additional models individually
        from database.models.performance_endpoint_results import PerformanceEndpointResults
        from database.models.performance_test_executions import PerformanceTestExecution
        from database.models.performance_test_configs import PerformanceTestConfig
        from database.models.api_collections import ApiCollection
        from database.models.test_scenarios import TestScenario
        
        # Check that models are registered
        all_tables = SQLModel.metadata.tables
        print(f"✅ Found {len(all_tables)} registered table models:")
        for table_name in sorted(all_tables.keys()):
            print(f"   - {table_name}")
        
        return True
    except Exception as e:
        print(f"❌ Error validating models: {e}")
        return False


def show_migration_status():
    """Show current migration status"""
    print("📊 Migration Status Report")
    print("=" * 50)
    
    # Check SQLite databases
    sqlite_dbs = [
        "data/qa_intelligence.db",
        "data/qa_conversations.db", 
        "data/qa_intelligence_rag.db"
    ]
    
    print("SQLite Databases:")
    for db_path in sqlite_dbs:
        if os.path.exists(db_path):
            size = os.path.getsize(db_path) / 1024  # KB
            print(f"  ✅ {db_path} ({size:.1f} KB)")
        else:
            print(f"  ❌ {db_path} (not found)")
    
    print("\nPostgreSQL/Supabase:")
    if is_supabase_configured():
        config = get_supabase_config()
        print(f"  ✅ Configured: {config.supabase_url}")
        print(f"  ✅ Pool size: {config.pool_size}")
        print(f"  ✅ SSL required: {config.ssl_require}")
    else:
        print("  ❌ Not configured")


async def main():
    """Main migration workflow"""
    print("🚀 QA Intelligence: SQLite to Supabase Migration")
    print("=" * 50)
    
    # Step 1: Show current status
    show_migration_status()
    print()
    
    # Step 2: Validate models
    if not validate_models():
        print("❌ Model validation failed. Aborting migration.")
        return 1
    print()
    
    # Step 3: Check Supabase configuration
    if not check_supabase_connection():
        print("❌ Supabase connection failed. Please check configuration.")
        print("📝 Instructions:")
        print("1. Create a Supabase project at https://app.supabase.com")
        print("2. Copy your database URL from Settings > Database")
        print("3. Update .env.supabase with your credentials")
        return 1
    print()
    
    # Step 4: Create tables
    if not create_tables():
        print("❌ Table creation failed. Aborting migration.")
        return 1
    print()
    
    # Step 5: Success message
    print("🎉 Migration setup completed successfully!")
    print("📝 Next steps:")
    print("1. Update your services to use the new database")
    print("2. Test all functionality with PostgreSQL")
    print("3. Consider backing up SQLite data if needed")
    print("4. Update environment variables for production")
    
    return 0


if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n❌ Migration interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        sys.exit(1)