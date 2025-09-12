#!/usr/bin/env python3
"""
Migration: Add postman_variables field to app_environment_country_mappings

This migration adds a JSON field to store Postman collection variables
that can be dynamically updated by the QA agent during test execution.

Date: 2025-12-09
Purpose: Enable dynamic Postman variable management
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

logger = get_logger("PostmanVariablesMigration")

def add_postman_variables_field():
    """Add postman_variables JSON field to app_environment_country_mappings table"""
    
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
        
        # Check if column already exists
        cursor.execute("PRAGMA table_info(app_environment_country_mappings)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'postman_variables' in columns:
            logger.info("✅ Column 'postman_variables' already exists")
            return True
        
        # Add the new column
        logger.info("➕ Adding postman_variables column...")
        alter_query = """
        ALTER TABLE app_environment_country_mappings 
        ADD COLUMN postman_variables TEXT
        """
        cursor.execute(alter_query)
        
        # Create sample data structure for existing records
        sample_postman_vars = {
            "variables": {
                "base_url": "{{BASE_URL}}",
                "api_key": "{{API_KEY}}",
                "user_id": "{{USER_ID}}",
                "access_token": "{{ACCESS_TOKEN}}"
            },
            "runtime_values": {},
            "metadata": {
                "last_updated": datetime.utcnow().isoformat(),
                "updated_by": "migration",
                "version": "1.0"
            }
        }
        
        # Initialize existing records with empty structure
        logger.info("🔄 Initializing existing records with default postman_variables...")
        cursor.execute("""
            UPDATE app_environment_country_mappings 
            SET postman_variables = ? 
            WHERE postman_variables IS NULL
        """, (json.dumps(sample_postman_vars),))
        
        # Commit changes
        conn.commit()
        
        # Verify the column was added
        cursor.execute("PRAGMA table_info(app_environment_country_mappings)")
        columns_after = [column[1] for column in cursor.fetchall()]
        
        if 'postman_variables' in columns_after:
            logger.info("✅ postman_variables column added successfully")
            
            # Show statistics
            cursor.execute("SELECT COUNT(*) FROM app_environment_country_mappings")
            total_records = cursor.fetchone()[0]
            
            cursor.execute("""
                SELECT COUNT(*) FROM app_environment_country_mappings 
                WHERE postman_variables IS NOT NULL
            """)
            initialized_records = cursor.fetchone()[0]
            
            logger.info(f"📊 Records updated: {initialized_records}/{total_records}")
            return True
        else:
            logger.error("❌ Failed to add postman_variables column")
            return False
            
    except Exception as e:
        logger.error(f"❌ Migration failed: {e}")
        return False
    finally:
        try:
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
        
        postman_col = None
        for col in columns:
            if col[1] == 'postman_variables':
                postman_col = col
                break
        
        if postman_col:
            logger.info(f"✅ Column verified: {postman_col[1]} ({postman_col[2]})")
            
            # Check sample data
            cursor.execute("""
                SELECT id, application_id, environment_id, country_id, postman_variables
                FROM app_environment_country_mappings 
                LIMIT 3
            """)
            
            sample_data = cursor.fetchall()
            logger.info("📋 Sample records with postman_variables:")
            for record in sample_data:
                logger.info(f"   ID {record[0]}: App {record[1]}, Env {record[2]}, Country {record[3]}")
                if record[4]:
                    postman_data = json.loads(record[4])
                    logger.info(f"     Variables: {len(postman_data.get('variables', {}))}")
            
            return True
        else:
            logger.error("❌ Column not found after migration")
            return False
            
    except Exception as e:
        logger.error(f"❌ Verification failed: {e}")
        return False
    finally:
        try:
            conn.close()
        except:
            pass

def main():
    """Run the migration"""
    
    logger.info("🚀 Starting postman_variables migration...")
    
    # Run migration
    if add_postman_variables_field():
        logger.info("✅ Migration completed successfully")
        
        # Verify migration
        if verify_migration():
            logger.info("✅ Migration verified successfully")
            print("\n🎉 Postman variables field added successfully!")
            print("📋 Ready to store Postman collection variables")
        else:
            logger.error("❌ Migration verification failed")
            return 1
    else:
        logger.error("❌ Migration failed")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())