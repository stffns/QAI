#!/usr/bin/env python3
"""
Database Migration: Drop api_test_executions and api_test_results tables
=====================================================================

This migration removes the unused API testing tables:
- Drops api_test_results table (0 records, FK to api_test_executions)
- Drops api_test_executions table (0 records, no code dependencies)

These tables appear to be unused prototypes that duplicate functionality
already provided by performance_test_executions (60 records, actively used).

Author: QA Intelligence Team
Date: 2025-09-12
"""

import sqlite3
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

def drop_api_test_tables():
    """Drop the unused api_test_executions and api_test_results tables"""
    db_path = Path("data/qa_intelligence.db")
    
    if not db_path.exists():
        print(f"❌ Database not found: {db_path}")
        return False
    
    try:
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        
        # Check current record counts
        for table in ['api_test_results', 'api_test_executions']:
            cursor.execute(f"""
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name='{table}'
            """)
            
            if cursor.fetchone():
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                count = cursor.fetchone()[0]
                print(f"📊 Found {count} records in {table} table")
            else:
                print(f"ℹ️ {table} table does not exist")
        
        # Drop api_test_results first (has FK to api_test_executions)
        print("🗑️ Dropping api_test_results table...")
        cursor.execute("DROP TABLE IF EXISTS api_test_results")
        
        # Drop api_test_executions second (parent table)
        print("🗑️ Dropping api_test_executions table...")
        cursor.execute("DROP TABLE IF EXISTS api_test_executions")
        
        # Drop any related indexes (if they exist independently)
        try:
            cursor.execute("DROP INDEX IF EXISTS idx_api_test_results_execution_id")
            cursor.execute("DROP INDEX IF EXISTS idx_api_test_executions_status")
            cursor.execute("DROP INDEX IF EXISTS idx_api_test_executions_app_env_country")
        except Exception as e:
            logger.debug(f"Index drop warning: {e}")
        
        # Commit changes
        conn.commit()
        conn.close()
        
        print("✅ API test tables dropped successfully")
        return True
        
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        if 'conn' in locals():
            conn.rollback()
            conn.close()
        return False

def verify_migration():
    """Verify that migration was successful and didn't break performance_test_executions"""
    db_path = Path("data/qa_intelligence.db")
    
    try:
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        
        # Check api test tables are gone
        for table in ['api_test_results', 'api_test_executions']:
            cursor.execute(f"""
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name='{table}'
            """)
            
            if cursor.fetchone():
                print(f"⚠️ {table} table still exists")
                return False
            else:
                print(f"✅ {table} table successfully removed")
        
        # Check performance_test_executions is intact
        cursor.execute("SELECT COUNT(*) FROM performance_test_executions")
        count = cursor.fetchone()[0]
        print(f"✅ performance_test_executions table intact with {count} records")
        
        # Verify table structure is still good
        cursor.execute("PRAGMA table_info(performance_test_executions)")
        columns = len(cursor.fetchall())
        print(f"✅ performance_test_executions has {columns} columns")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Verification failed: {e}")
        return False

def main():
    """Execute migration"""
    print("🗑️ API Test Tables Cleanup Migration")
    print("=" * 50)
    
    # Drop tables
    if not drop_api_test_tables():
        print("💥 Migration failed")
        return 1
    
    # Verify
    if not verify_migration():
        print("💥 Verification failed") 
        return 1
    
    print("\n🎉 Migration completed successfully!")
    print("✨ Unused API test tables removed")
    print("🚀 performance_test_executions remains as single testing system")
    
    return 0

if __name__ == "__main__":
    exit(main())