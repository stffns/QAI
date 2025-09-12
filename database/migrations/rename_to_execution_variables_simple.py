#!/usr/bin/env python3
"""
Migration: Rename postman_variables to execution_variables (Simple approach)

This migration uses a simpler approach:
1. Add new execution_variables column
2. Copy data from postman_variables to execution_variables  
3. Drop postman_variables column

Date: 2025-12-09
Purpose: Rename column for better semantics
"""

import sqlite3
from pathlib import Path
import json
from datetime import datetime
import sys
import os

# Add project root to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), "..", ".."))

from src.logging_config import get_logger

logger = get_logger("RenameExecutionVariablesSimple")

def rename_column_simple_approach():
    """Simple approach to rename the column"""
    
    # Get database path
    db_path = Path(__file__).parent.parent.parent / "data" / "qa_intelligence.db"
    
    if not db_path.exists():
        logger.error(f"❌ Database not found at: {db_path}")
        return False
    
    logger.info(f"📂 Using database: {db_path}")
    
    conn = None
    try:
        # Connect to database
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        
        # Check current columns
        cursor.execute("PRAGMA table_info(app_environment_country_mappings)")
        columns = [column[1] for column in cursor.fetchall()]
        
        has_postman = 'postman_variables' in columns
        has_execution = 'execution_variables' in columns
        
        logger.info(f"📋 Current state: postman_variables={has_postman}, execution_variables={has_execution}")
        
        if has_execution and not has_postman:
            logger.info("✅ Column already renamed successfully")
            return True
        
        if not has_postman:
            logger.error("❌ Source column 'postman_variables' not found")
            return False
        
        # Step 1: Add new column if it doesn't exist
        if not has_execution:
            logger.info("➕ Adding execution_variables column...")
            cursor.execute("""
                ALTER TABLE app_environment_country_mappings 
                ADD COLUMN execution_variables TEXT
            """)
            conn.commit()
        
        # Step 2: Copy data from postman_variables to execution_variables
        logger.info("📋 Copying data from postman_variables to execution_variables...")
        cursor.execute("""
            UPDATE app_environment_country_mappings 
            SET execution_variables = postman_variables 
            WHERE postman_variables IS NOT NULL
        """)
        
        # Step 3: Verify data was copied
        cursor.execute("SELECT COUNT(*) FROM app_environment_country_mappings WHERE execution_variables IS NOT NULL")
        execution_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM app_environment_country_mappings WHERE postman_variables IS NOT NULL")
        postman_count = cursor.fetchone()[0]
        
        if execution_count != postman_count:
            logger.error(f"❌ Data copy mismatch: postman={postman_count}, execution={execution_count}")
            return False
        
        logger.info(f"✅ Data copied successfully: {execution_count} records")
        
        # Step 4: Create new table without postman_variables column
        logger.info("🔄 Creating new table structure...")
        
        # Get current schema and remove postman_variables
        cursor.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='app_environment_country_mappings'")
        original_sql = cursor.fetchone()[0]
        
        # Create temporary table without postman_variables column
        temp_sql = """
        CREATE TABLE app_environment_country_mappings_temp (
            id INTEGER PRIMARY KEY,
            application_id INTEGER NOT NULL,
            environment_id INTEGER NOT NULL,
            country_id INTEGER NOT NULL,
            base_url TEXT NOT NULL,
            protocol TEXT NOT NULL DEFAULT 'https',
            default_headers TEXT,
            auth_config TEXT,
            execution_variables TEXT,
            performance_config TEXT,
            max_response_time_ms INTEGER NOT NULL DEFAULT 2000,
            max_error_rate_percent REAL NOT NULL DEFAULT 5.0,
            is_active INTEGER NOT NULL DEFAULT 1,
            launched_date TEXT,
            deprecated_date TEXT,
            priority INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL,
            updated_at TEXT,
            FOREIGN KEY (application_id) REFERENCES apps_master(id),
            FOREIGN KEY (environment_id) REFERENCES environments_master(id),
            FOREIGN KEY (country_id) REFERENCES countries_master(id),
            UNIQUE (application_id, environment_id, country_id)
        )
        """
        
        cursor.execute(temp_sql)
        
        # Copy all data to new table (excluding postman_variables)
        logger.info("📋 Copying all data to new table...")
        cursor.execute("""
            INSERT INTO app_environment_country_mappings_temp 
            SELECT 
                id, application_id, environment_id, country_id, base_url, protocol,
                default_headers, auth_config, execution_variables, performance_config,
                max_response_time_ms, max_error_rate_percent, is_active, 
                launched_date, deprecated_date, priority, created_at, updated_at
            FROM app_environment_country_mappings
        """)
        
        # Drop original table and rename temp table
        cursor.execute("DROP TABLE app_environment_country_mappings")
        cursor.execute("ALTER TABLE app_environment_country_mappings_temp RENAME TO app_environment_country_mappings")
        
        # Commit all changes
        conn.commit()
        
        logger.info("✅ Migration completed successfully")
        return True
        
    except Exception as e:
        logger.error(f"❌ Migration failed: {e}")
        if conn:
            try:
                conn.rollback()
            except:
                pass
        return False
    finally:
        if conn:
            try:
                conn.close()
            except:
                pass

def verify_final_state():
    """Verify the migration was successful"""
    
    db_path = Path(__file__).parent.parent.parent / "data" / "qa_intelligence.db"
    
    conn = None
    try:
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        
        # Check final columns
        cursor.execute("PRAGMA table_info(app_environment_country_mappings)")
        columns = [col[1] for col in cursor.fetchall()]
        
        has_execution = 'execution_variables' in columns
        has_postman = 'postman_variables' in columns
        
        if has_execution and not has_postman:
            logger.info("✅ Final verification successful:")
            logger.info("   ✅ execution_variables column exists")
            logger.info("   ✅ postman_variables column removed")
            
            # Check data
            cursor.execute("SELECT COUNT(*) FROM app_environment_country_mappings WHERE execution_variables IS NOT NULL")
            count = cursor.fetchone()[0]
            logger.info(f"   📊 Records with execution_variables: {count}")
            
            return True
        else:
            logger.error("❌ Final verification failed:")
            if not has_execution:
                logger.error("   ❌ execution_variables column missing")
            if has_postman:
                logger.error("   ❌ postman_variables column still exists")
            return False
            
    except Exception as e:
        logger.error(f"❌ Verification failed: {e}")
        return False
    finally:
        if conn:
            try:
                conn.close()
            except:
                pass

def main():
    """Run the migration"""
    
    logger.info("🚀 Starting simple postman_variables → execution_variables migration...")
    
    if rename_column_simple_approach():
        if verify_final_state():
            print("\n🎉 Column renamed successfully!")
            print("📋 postman_variables → execution_variables")
            print("🔄 All data preserved")
            return 0
        else:
            logger.error("❌ Final verification failed")
            return 1
    else:
        logger.error("❌ Migration failed")
        return 1

if __name__ == "__main__":
    exit(main())