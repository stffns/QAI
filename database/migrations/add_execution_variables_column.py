#!/usr/bin/env python3
"""
Simple migration to add execution_variables column to app_environment_country_mappings
"""
import sqlite3
import sys
from pathlib import Path

def add_execution_variables_column(db_path: str = "data/qa_intelligence.db"):
    """Add execution_variables column to the database"""
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        print("🔧 Adding execution_variables column...")
        
        # Check if column already exists
        cursor.execute("PRAGMA table_info(app_environment_country_mappings);")
        columns = [row[1] for row in cursor.fetchall()]
        
        if 'execution_variables' in columns:
            print("✅ Column execution_variables already exists")
            return True
        
        # Add the column
        cursor.execute("""
            ALTER TABLE app_environment_country_mappings 
            ADD COLUMN execution_variables JSON
        """)
        
        conn.commit()
        
        print("✅ Column execution_variables added successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Error adding column: {e}")
        conn.rollback()
        return False
        
    finally:
        conn.close()


if __name__ == "__main__":
    db_path = sys.argv[1] if len(sys.argv) > 1 else "data/qa_intelligence.db"
    
    if not Path(db_path).exists():
        print(f"❌ Database file not found: {db_path}")
        sys.exit(1)
    
    print(f"🔄 Adding execution_variables column to {db_path}")
    success = add_execution_variables_column(db_path)
    
    if success:
        print("🎉 Migration completed!")
        sys.exit(0)
    else:
        print("💥 Migration failed!")
        sys.exit(1)