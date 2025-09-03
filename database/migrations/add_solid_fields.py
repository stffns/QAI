"""
Database Migration Script for QA Intelligence
Adds SOLID-compatible fields to existing qa_intelligence.db
"""

import sqlite3
import os
from datetime import datetime, timezone

def get_database_path():
    """Get the path to qa_intelligence.db"""
    # Get current script directory
    script_dir = os.path.dirname(os.path.abspath(__file__))
    # Go up two levels to QAI root, then into data folder
    project_root = os.path.dirname(os.path.dirname(script_dir))
    return os.path.join(project_root, 'data', 'qa_intelligence.db')

def backup_database():
    """Create a backup of the database before migration"""
    db_path = get_database_path()
    backup_path = f"{db_path}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    print(f"📦 Creating backup: {backup_path}")
    
    # Copy database file
    import shutil
    shutil.copy2(db_path, backup_path)
    
    print(f"✅ Backup created successfully")
    return backup_path

def check_column_exists(cursor, table_name, column_name):
    """Check if a column exists in a table"""
    cursor.execute(f"PRAGMA table_info({table_name})")
    columns = cursor.fetchall()
    return any(column[1] == column_name for column in columns)

def migrate_users_table():
    """Migrate users table to add SOLID-compatible fields"""
    db_path = get_database_path()
    
    print(f"🔄 Migrating users table in: {db_path}")
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # List of new columns to add
        new_columns = [
            ('created_by', 'INTEGER', 'NULL'),  # Foreign key to users.id
            ('updated_by', 'INTEGER', 'NULL'),  # Foreign key to users.id
            ('username_norm', 'VARCHAR(150)', 'NULL'),  # Normalized username for search
            ('email_norm', 'VARCHAR(255)', 'NULL'),      # Normalized email for search
            ('locked_until', 'DATETIME', 'NULL'),        # When lock expires
        ]
        
        print("📋 Checking existing columns...")
        
        # Add missing columns
        for column_name, column_type, default_value in new_columns:
            if not check_column_exists(cursor, 'users', column_name):
                print(f"   ➕ Adding column: {column_name}")
                cursor.execute(f"ALTER TABLE users ADD COLUMN {column_name} {column_type} DEFAULT {default_value}")
            else:
                print(f"   ✅ Column already exists: {column_name}")
        
        # Update normalized fields for existing records
        print("🔄 Updating normalized fields...")
        cursor.execute("""
            UPDATE users 
            SET username_norm = LOWER(TRIM(username)),
                email_norm = LOWER(TRIM(email))
            WHERE username_norm IS NULL OR email_norm IS NULL
        """)
        
        # Create indices for new fields
        print("🔍 Creating indices...")
        
        indices_to_create = [
            ('idx_users_username_norm', 'users', 'username_norm'),
            ('idx_users_email_norm', 'users', 'email_norm'),
            ('idx_users_created_by', 'users', 'created_by'),
            ('idx_users_updated_by', 'users', 'updated_by'),
            ('idx_users_locked_until', 'users', 'locked_until'),
        ]
        
        for index_name, table_name, column_name in indices_to_create:
            try:
                cursor.execute(f"CREATE INDEX IF NOT EXISTS {index_name} ON {table_name}({column_name})")
                print(f"   ✅ Created index: {index_name}")
            except sqlite3.Error as e:
                print(f"   ⚠️  Index {index_name} might already exist: {e}")
        
        # Commit changes
        conn.commit()
        print("✅ Migration completed successfully!")
        
        # Verify the migration
        print("\n📊 Verifying migration...")
        cursor.execute("PRAGMA table_info(users)")
        columns = cursor.fetchall()
        
        print("Current columns in users table:")
        for column in columns:
            print(f"   - {column[1]} ({column[2]}) {'NOT NULL' if column[3] else 'NULL'}")
        
        # Count existing users
        cursor.execute("SELECT COUNT(*) FROM users")
        user_count = cursor.fetchone()[0]
        print(f"\n👥 Total users in database: {user_count}")
        
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()

def create_audit_log_table():
    """Create audit_log table if it doesn't exist"""
    db_path = get_database_path()
    
    print("🔄 Creating audit_log table...")
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Check if table exists
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='audit_log'
        """)
        
        if cursor.fetchone():
            print("   ✅ audit_log table already exists")
        else:
            # Create audit_log table
            cursor.execute("""
                CREATE TABLE audit_log (
                    id INTEGER NOT NULL PRIMARY KEY,
                    user_id INTEGER NOT NULL,
                    action VARCHAR(50) NOT NULL,
                    entity_type VARCHAR(50) NOT NULL,
                    entity_id VARCHAR(50),
                    old_values TEXT,
                    new_values TEXT,
                    ip_address VARCHAR(45),
                    user_agent TEXT,
                    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id)
                )
            """)
            
            # Create indices
            cursor.execute("CREATE INDEX idx_audit_log_user_id ON audit_log(user_id)")
            cursor.execute("CREATE INDEX idx_audit_log_action ON audit_log(action)")
            cursor.execute("CREATE INDEX idx_audit_log_entity ON audit_log(entity_type, entity_id)")
            cursor.execute("CREATE INDEX idx_audit_log_created_at ON audit_log(created_at)")
            
            print("   ✅ audit_log table created successfully")
        
        conn.commit()
        
    except Exception as e:
        print(f"❌ Failed to create audit_log table: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()

def main():
    """Main migration function"""
    print("🚀 QA Intelligence Database Migration")
    print("=" * 50)
    
    try:
        # Create backup
        backup_path = backup_database()
        
        # Migrate users table
        migrate_users_table()
        
        # Create audit_log table
        create_audit_log_table()
        
        print("\n🎉 Migration completed successfully!")
        print(f"💾 Backup saved at: {backup_path}")
        print("\nYour database is now compatible with the SOLID repository pattern!")
        
    except Exception as e:
        print(f"\n💥 Migration failed: {e}")
        print("Your original database is safe - check the backup file if needed.")
        return False
    
    return True

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
