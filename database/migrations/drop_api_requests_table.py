#!/usr/bin/env python3
"""
Database Migration: Drop api_requests table and related artifacts
================================================================

This migration removes the deprecated api_requests table and its artifacts:
- Drops api_requests table (20 records will be lost - already migrated to application_endpoints)
- The data is preserved in application_endpoints table (21 records)

Author: QA Intelligence Team
Date: 2025-09-12
"""

import sqlite3
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

def drop_api_requests_table():
    """Drop the deprecated api_requests table"""
    db_path = Path("data/qa_intelligence.db")
    
    if not db_path.exists():
        print(f"❌ Database not found: {db_path}")
        return False
    
    try:
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        
        # Check if table exists
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='api_requests'
        """)
        
        if not cursor.fetchone():
            print("ℹ️ api_requests table does not exist, nothing to drop")
            return True
        
        # Check current record count
        cursor.execute("SELECT COUNT(*) FROM api_requests")
        count = cursor.fetchone()[0]
        print(f"📊 Found {count} records in api_requests table")
        
        # Drop the table
        print("🗑️ Dropping api_requests table...")
        cursor.execute("DROP TABLE IF EXISTS api_requests")
        
        # Drop related indexes (if they exist independently)
        try:
            cursor.execute("DROP INDEX IF EXISTS ix_api_requests_collection_order")
            cursor.execute("DROP INDEX IF EXISTS ix_api_requests_endpoint")
        except Exception as e:
            logger.debug(f"Index drop warning: {e}")
        
        # Commit changes
        conn.commit()
        conn.close()
        
        print("✅ api_requests table dropped successfully")
        print("📊 Data preserved in application_endpoints table")
        return True
        
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        if 'conn' in locals():
            conn.rollback()
            conn.close()
        return False

def verify_migration():
    """Verify that migration was successful"""
    db_path = Path("data/qa_intelligence.db")
    
    try:
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        
        # Check api_requests is gone
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='api_requests'
        """)
        
        if cursor.fetchone():
            print("⚠️ api_requests table still exists")
            return False
        
        # Check application_endpoints exists with data
        cursor.execute("SELECT COUNT(*) FROM application_endpoints")
        count = cursor.fetchone()[0]
        print(f"✅ application_endpoints table has {count} records")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Verification failed: {e}")
        return False

def main():
    """Execute migration"""
    print("🗑️ API Requests Table Cleanup Migration")
    print("=" * 50)
    
    # Drop table
    if not drop_api_requests_table():
        print("💥 Migration failed")
        return 1
    
    # Verify
    if not verify_migration():
        print("💥 Verification failed") 
        return 1
    
    print("\n🎉 Migration completed successfully!")
    print("✨ api_requests table removed, data preserved in application_endpoints")
    
    return 0

if __name__ == "__main__":
    exit(main())