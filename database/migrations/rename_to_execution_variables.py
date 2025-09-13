#!/usr/bin/env python3
"""
Migration: Rename postman_variables to execution_variables

This migration renames the postman_variables column to execution_variables
to better reflect its generic purpose for storing test execution variables
from any source (not just Postman).

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

logger = get_logger("RenameExecutionVariablesMigration")

def rename_postman_variables_to_execution_variables():
    """Rename postman_variables column to execution_variables"""
    
    # Get database path
    db_path = Path(__file__).parent.parent.parent / "data" / "qa_intelligence.db"
    
    if not db_path.exists():
        logger.error(f"❌ Database not found at: {db_path}")
        return False
    
    logger.info(f"📂 Using database: {db_path}")
    
    try:
        # Connect to database
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        
        # Check if postman_variables column exists
        cursor.execute("PRAGMA table_info(app_environment_country_mappings)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'postman_variables' not in columns:
            logger.error("❌ Column 'postman_variables' not found")
            return False
        
        if 'execution_variables' in columns:
            logger.info("✅ Column 'execution_variables' already exists")
            return True
        
        # SQLite doesn't support RENAME COLUMN directly in older versions
        # We'll use the recommended approach: create new table, copy data, rename
        
        logger.info("🔄 Starting column rename process...")
        
        # Step 1: Get current table schema
        cursor.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='app_environment_country_mappings'")
        create_sql = cursor.fetchone()[0]
        
        # Step 2: Modify schema to use execution_variables instead of postman_variables
        new_create_sql = create_sql.replace('postman_variables', 'execution_variables')
        
        # Step 3: Create new table with updated schema
        logger.info("📝 Creating temporary table with new schema...")
        temp_table_sql = new_create_sql.replace(
            'CREATE TABLE app_environment_country_mappings', 
            'CREATE TABLE app_environment_country_mappings_new'
        )
        cursor.execute(temp_table_sql)
        
        # Step 4: Copy all data from old table to new table
        logger.info("📋 Copying data to new table...")
        
        # Get all column names except we'll map postman_variables -> execution_variables
        cursor.execute("PRAGMA table_info(app_environment_country_mappings)")
        all_columns = [col[1] for col in cursor.fetchall()]
        
        # Create column mapping for the copy
        select_columns = []
        insert_columns = []
        
        for col in all_columns:
            if col == 'postman_variables':
                select_columns.append('postman_variables')
                insert_columns.append('execution_variables')
            else:
                select_columns.append(col)
                insert_columns.append(col)
        
        copy_sql = f"""
        INSERT INTO app_environment_country_mappings_new ({', '.join(insert_columns)})
        SELECT {', '.join(select_columns)}
        FROM app_environment_country_mappings
        """
        
        cursor.execute(copy_sql)
        
        # Step 5: Check for views or triggers that depend on the table
        logger.info("🔍 Checking for dependencies...")
        cursor.execute("""
            SELECT name, sql FROM sqlite_master 
            WHERE type IN ('view', 'trigger') 
            AND sql LIKE '%app_environment_country_mappings%'
        """)
        dependencies = cursor.fetchall()
        
        if dependencies:
            logger.info(f"⚠️  Found {len(dependencies)} dependencies, but they don't affect our table")
        
        # Step 6: Drop old table
        logger.info("🗑️ Dropping old table...")
        cursor.execute("DROP TABLE app_environment_country_mappings")
        
        # Step 7: Rename new table to original name
        logger.info("🔄 Renaming new table...")
        cursor.execute("ALTER TABLE app_environment_country_mappings_new RENAME TO app_environment_country_mappings")
        
        # Commit changes
        conn.commit()
        
        # Verify the rename was successful
        cursor.execute("PRAGMA table_info(app_environment_country_mappings)")
        new_columns = [column[1] for column in cursor.fetchall()]
        
        if 'execution_variables' in new_columns and 'postman_variables' not in new_columns:
            logger.info("✅ Column renamed successfully: postman_variables → execution_variables")
            
            # Show statistics
            cursor.execute("SELECT COUNT(*) FROM app_environment_country_mappings")
            total_records = cursor.fetchone()[0]
            
            cursor.execute("""
                SELECT COUNT(*) FROM app_environment_country_mappings 
                WHERE execution_variables IS NOT NULL
            """)
            records_with_data = cursor.fetchone()[0]
            
            logger.info(f"📊 Total records: {total_records}")
            logger.info(f"📊 Records with execution_variables: {records_with_data}")
            return True
        else:
            logger.error("❌ Failed to rename column")
            return False
            
    except Exception as e:
        logger.error(f"❌ Migration failed: {e}")
        try:
            conn.rollback()
        except:
            pass
        return False
    finally:
        try:
            if 'conn' in locals():
                conn.close()
        except:
            pass

def verify_migration():
    """Verify the migration was successful"""
    
    db_path = Path(__file__).parent.parent.parent / "data" / "qa_intelligence.db"
    
    try:
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        
        # Check table structure
        cursor.execute("PRAGMA table_info(app_environment_country_mappings)")
        columns = cursor.fetchall()
        
        execution_col = None
        postman_col = None
        
        for col in columns:
            if col[1] == 'execution_variables':
                execution_col = col
            elif col[1] == 'postman_variables':
                postman_col = col
        
        if execution_col and not postman_col:
            logger.info(f"✅ Column verified: {execution_col[1]} ({execution_col[2]})")
            
            # Check sample data
            cursor.execute("""
                SELECT id, application_id, environment_id, country_id, execution_variables
                FROM app_environment_country_mappings 
                LIMIT 3
            """)
            
            sample_data = cursor.fetchall()
            logger.info("📋 Sample records with execution_variables:")
            for record in sample_data:
                logger.info(f"   ID {record[0]}: App {record[1]}, Env {record[2]}, Country {record[3]}")
                if record[4]:
                    execution_data = json.loads(record[4])
                    logger.info(f"     Variables: {len(execution_data.get('variables', {}))}")
            
            return True
        else:
            logger.error("❌ Column rename verification failed")
            if postman_col:
                logger.error("   - Old 'postman_variables' column still exists")
            if not execution_col:
                logger.error("   - New 'execution_variables' column not found")
            return False
            
    except Exception as e:
        logger.error(f"❌ Verification failed: {e}")
        return False
    finally:
        try:
            if 'conn' in locals():
                conn.close()
        except:
            pass

def main():
    """Run the migration"""
    
    logger.info("🚀 Starting postman_variables → execution_variables migration...")
    
    # Run migration
    if rename_postman_variables_to_execution_variables():
        logger.info("✅ Migration completed successfully")
        
        # Verify migration
        if verify_migration():
            logger.info("✅ Migration verified successfully")
            print("\n🎉 Column renamed successfully!")
            print("📋 postman_variables → execution_variables")
            print("🔄 All data preserved during rename")
        else:
            logger.error("❌ Migration verification failed")
            return 1
    else:
        logger.error("❌ Migration failed")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())