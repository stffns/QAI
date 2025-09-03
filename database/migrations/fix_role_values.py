"""
Database Migration Script - Fix Role Values
Updates role values to match UserRole enum
"""

import sqlite3
import os

def get_database_path():
    """Get the path to qa_intelligence.db"""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(os.path.dirname(script_dir))
    return os.path.join(project_root, 'data', 'qa_intelligence.db')

def fix_role_values():
    """Update role values to match UserRole enum"""
    db_path = get_database_path()
    
    print(f"🔄 Fixing role values in: {db_path}")
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Check current role values
        print("📋 Current role values:")
        cursor.execute("SELECT DISTINCT role FROM users")
        current_roles = cursor.fetchall()
        for role in current_roles:
            print(f"   - {role[0]}")
        
        # Role mapping from database values to enum values
        role_mapping = {
            'viewer': 'VIEWER',
            'super_admin': 'ADMIN',
            'admin': 'ADMIN',
            'analyst': 'ANALYST', 
            'operator': 'OPERATOR'
        }
        
        print("\n🔄 Updating role values...")
        
        # Update each role
        for old_role, new_role in role_mapping.items():
            cursor.execute("UPDATE users SET role = ? WHERE role = ?", (new_role, old_role))
            affected_rows = cursor.rowcount
            if affected_rows > 0:
                print(f"   ✅ Updated {affected_rows} users from '{old_role}' to '{new_role}'")
        
        # Set default role for NULL values
        cursor.execute("UPDATE users SET role = 'VIEWER' WHERE role IS NULL")
        null_updates = cursor.rowcount
        if null_updates > 0:
            print(f"   ✅ Set default role 'VIEWER' for {null_updates} users with NULL role")
        
        # Verify the changes
        print("\n📊 Updated role values:")
        cursor.execute("SELECT DISTINCT role FROM users")
        updated_roles = cursor.fetchall()
        for role in updated_roles:
            print(f"   - {role[0]}")
        
        # Count users by role
        print("\n👥 Users by role:")
        cursor.execute("SELECT role, COUNT(*) FROM users GROUP BY role")
        role_counts = cursor.fetchall()
        for role, count in role_counts:
            print(f"   - {role}: {count} users")
        
        conn.commit()
        print("\n✅ Role values updated successfully!")
        
    except Exception as e:
        print(f"❌ Failed to update role values: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()

def main():
    """Main function"""
    print("🚀 QA Intelligence Role Values Migration")
    print("=" * 50)
    
    try:
        fix_role_values()
        print("\n🎉 Role migration completed successfully!")
        
    except Exception as e:
        print(f"\n💥 Migration failed: {e}")
        return False
    
    return True

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
