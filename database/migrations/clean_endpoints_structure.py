#!/usr/bin/env python3
"""
Migración: Limpiar estructura de application_endpoints
Elimina redundancia de FKs - solo mantener mapping_id
"""

import sqlite3
from pathlib import Path

def run_migration():
    """Ejecuta la migración para limpiar application_endpoints"""
    
    db_path = Path(__file__).parent.parent.parent / "data" / "qa_intelligence.db"
    
    if not db_path.exists():
        print(f"❌ Database not found: {db_path}")
        return False
        
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        print("🔄 Starting migration: Clean application_endpoints structure...")
        
        # 1. Verificar si ya existe la estructura limpia
        cursor.execute("""
            SELECT sql FROM sqlite_master 
            WHERE type='table' AND name='application_endpoints'
        """)
        current_schema = cursor.fetchone()[0]
        
        if 'application_id' not in current_schema:
            print("✅ Structure already clean - no migration needed")
            return True
            
        # 2. Crear tabla temporal con estructura limpia
        print("📋 Creating clean temporary table...")
        cursor.execute("""
            CREATE TABLE application_endpoints_clean (
                id INTEGER NOT NULL,
                mapping_id INTEGER NOT NULL REFERENCES app_environment_country_mappings(id),
                
                -- Información del endpoint (NOT NULL + validaciones)
                endpoint_name VARCHAR(255) NOT NULL CHECK (length(endpoint_name) >= 1),
                endpoint_url VARCHAR(500) NOT NULL CHECK (
                    endpoint_url LIKE '/%' AND  -- Debe empezar con /
                    length(endpoint_url) >= 1 AND
                    length(endpoint_url) <= 500
                ),
                http_method VARCHAR(10) NOT NULL CHECK (
                    http_method IN ('GET', 'POST', 'PUT', 'PATCH', 'DELETE', 'HEAD', 'OPTIONS')
                ),
                endpoint_type VARCHAR(50) CHECK (
                    endpoint_type IS NULL OR 
                    endpoint_type IN ('api', 'health', 'auth', 'dashboard', 'admin', 'public', 'internal')
                ),
                
                -- Datos adicionales y metadata
                description TEXT CHECK (description IS NULL OR length(description) <= 1000),
                body TEXT CHECK (body IS NULL OR json_valid(body)),  -- Validar JSON si no es NULL
                
                -- Estado y timestamps (NOT NULL obligatorio)
                is_active BOOLEAN NOT NULL DEFAULT 1 CHECK (is_active IN (0, 1)),
                created_at DATETIME NOT NULL DEFAULT (datetime('now', 'utc')),
                updated_at DATETIME,
                
                -- Constraints de integridad
                CONSTRAINT pk_application_endpoints PRIMARY KEY (id),
                CONSTRAINT fk_application_endpoints_mapping_id 
                    FOREIGN KEY(mapping_id) REFERENCES app_environment_country_mappings(id),
                
                -- UNIQUE constraint: Un endpoint por mapping + name
                CONSTRAINT uq_mapping_endpoint_name 
                    UNIQUE(mapping_id, endpoint_name)
            )
        """)
        
        # 3. Migrar datos existentes (solo campos válidos)
        print("📊 Migrating existing data...")
        cursor.execute("""
            INSERT INTO application_endpoints_clean (
                id, mapping_id, endpoint_name, endpoint_url, http_method, 
                endpoint_type, description, body, is_active, created_at, updated_at
            )
            SELECT 
                id, mapping_id, endpoint_name, endpoint_url, http_method,
                endpoint_type, description, body, is_active, created_at, updated_at
            FROM application_endpoints
            WHERE mapping_id IS NOT NULL
        """)
        
        migrated_count = cursor.rowcount
        print(f"📈 Migrated {migrated_count} endpoints")
        
        # 4. Verificar que no se perdieron datos críticos
        cursor.execute("SELECT COUNT(*) FROM application_endpoints")
        original_count = cursor.fetchone()[0]
        
        if migrated_count != original_count:
            print(f"⚠️ WARNING: Original={original_count}, Migrated={migrated_count}")
            print("Some endpoints may have NULL mapping_id")
            
        # 5. Reemplazar tabla original
        print("🔄 Replacing original table...")
        cursor.execute("DROP TABLE application_endpoints")
        cursor.execute("ALTER TABLE application_endpoints_clean RENAME TO application_endpoints")
        
        # 6. Commit changes
        conn.commit()
        print("✅ Migration completed successfully!")
        
        # 7. Verificar resultado final
        cursor.execute("SELECT COUNT(*) FROM application_endpoints")
        final_count = cursor.fetchone()[0]
        print(f"📊 Final endpoints count: {final_count}")
        
        return True
        
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        conn.rollback()
        return False
        
    finally:
        conn.close()

def verify_clean_structure():
    """Verifica que la estructura esté limpia"""
    
    db_path = Path(__file__).parent.parent.parent / "data" / "qa_intelligence.db"
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            SELECT sql FROM sqlite_master 
            WHERE type='table' AND name='application_endpoints'
        """)
        schema = cursor.fetchone()[0]
        
        # Verificar que NO tenga las FKs redundantes
        redundant_fields = ['application_id', 'environment_id', 'country_id']
        has_redundancy = any(field in schema for field in redundant_fields)
        
        if has_redundancy:
            print("❌ Structure still has redundant fields")
            return False
        else:
            print("✅ Structure is clean - only mapping_id FK")
            return True
            
    finally:
        conn.close()

if __name__ == "__main__":
    print("=" * 60)
    print("🧹 Application Endpoints Structure Cleanup Migration")
    print("=" * 60)
    
    success = run_migration()
    
    if success:
        verify_clean_structure()
        print("\n🎉 Migration completed successfully!")
    else:
        print("\n💥 Migration failed!")