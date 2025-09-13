#!/usr/bin/env python3
"""
Migration: Add Test Scenarios Tables

Creates tables for test scenario management:
- test_scenarios: Define testing scenarios (performance, functional, smoke, etc.)
- test_scenario_endpoints: Many-to-many relationship between scenarios and endpoints

Author: QA Intelligence System
Date: 2025-09-12
"""

import sqlite3
import sys
from pathlib import Path

def create_test_scenarios_tables(db_path: str = "data/qa_intelligence.db"):
    """Create test scenarios tables in the database"""
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        print("🔧 Creating test scenarios tables...")
        
        # 1. Create test_scenarios table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS test_scenarios (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                mapping_id INTEGER NOT NULL,
                scenario_name VARCHAR(100) NOT NULL,
                scenario_type VARCHAR(20) NOT NULL CHECK (scenario_type IN (
                    'PERFORMANCE', 'FUNCTIONAL', 'SMOKE', 'REGRESSION', 
                    'BUSINESS_FLOW', 'INTEGRATION', 'SECURITY', 'LOAD_BALANCER'
                )),
                description VARCHAR(500),
                config JSON,
                max_execution_time_minutes INTEGER NOT NULL DEFAULT 30 CHECK (max_execution_time_minutes BETWEEN 1 AND 480),
                retry_failed_endpoints BOOLEAN NOT NULL DEFAULT 1,
                stop_on_critical_failure BOOLEAN NOT NULL DEFAULT 0,
                target_concurrent_users INTEGER CHECK (target_concurrent_users BETWEEN 1 AND 10000),
                ramp_up_time_seconds INTEGER CHECK (ramp_up_time_seconds BETWEEN 0 AND 3600),
                is_active BOOLEAN NOT NULL DEFAULT 1,
                created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME,
                created_by VARCHAR(100),
                priority INTEGER NOT NULL DEFAULT 1 CHECK (priority BETWEEN 1 AND 10),
                
                FOREIGN KEY (mapping_id) REFERENCES app_environment_country_mappings(id) ON DELETE CASCADE,
                CONSTRAINT uq_mapping_scenario_name UNIQUE (mapping_id, scenario_name)
            )
        """)
        
        # 2. Create test_scenario_endpoints table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS test_scenario_endpoints (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                scenario_id INTEGER NOT NULL,
                endpoint_id INTEGER NOT NULL,
                execution_order INTEGER NOT NULL DEFAULT 1 CHECK (execution_order BETWEEN 1 AND 1000),
                is_critical BOOLEAN NOT NULL DEFAULT 0,
                is_active BOOLEAN NOT NULL DEFAULT 1,
                weight INTEGER NOT NULL DEFAULT 1 CHECK (weight BETWEEN 1 AND 100),
                custom_timeout_ms INTEGER CHECK (custom_timeout_ms BETWEEN 100 AND 300000),
                expected_status_codes JSON DEFAULT '[200]',
                custom_validation JSON,
                depends_on_endpoint_ids JSON,
                created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME,
                notes VARCHAR(500),
                
                FOREIGN KEY (scenario_id) REFERENCES test_scenarios(id) ON DELETE CASCADE,
                FOREIGN KEY (endpoint_id) REFERENCES application_endpoints(id) ON DELETE CASCADE,
                CONSTRAINT uq_scenario_endpoint UNIQUE (scenario_id, endpoint_id)
            )
        """)
        
        # 3. Create indexes for better performance
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS ix_scenario_mapping_type 
            ON test_scenarios(mapping_id, scenario_type)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS ix_scenario_active 
            ON test_scenarios(is_active)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS ix_scenario_endpoints_order 
            ON test_scenario_endpoints(scenario_id, execution_order)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS ix_scenario_endpoints_active 
            ON test_scenario_endpoints(is_active)
        """)
        
        # 4. Insert some default scenarios for existing mappings
        print("📋 Creating default scenarios for existing mappings...")
        
        cursor.execute("""
            SELECT id, base_url 
            FROM app_environment_country_mappings 
            WHERE is_active = 1
        """)
        
        mappings = cursor.fetchall()
        
        for mapping_id, base_url in mappings:
            # Create default SMOKE scenario
            cursor.execute("""
                INSERT OR IGNORE INTO test_scenarios 
                (mapping_id, scenario_name, scenario_type, description, priority)
                VALUES (?, 'Basic Smoke Test', 'SMOKE', 
                       'Basic endpoint availability and response validation', 1)
            """, (mapping_id,))
            
            # Create default FUNCTIONAL scenario
            cursor.execute("""
                INSERT OR IGNORE INTO test_scenarios 
                (mapping_id, scenario_name, scenario_type, description, priority)
                VALUES (?, 'Complete Functional Test', 'FUNCTIONAL', 
                       'Comprehensive functional testing of all endpoints', 2)
            """, (mapping_id,))
            
            # Create default PERFORMANCE scenario (if appropriate)
            cursor.execute("""
                INSERT OR IGNORE INTO test_scenarios 
                (mapping_id, scenario_name, scenario_type, description, priority,
                 target_concurrent_users, ramp_up_time_seconds, max_execution_time_minutes)
                VALUES (?, 'Load Test - Critical APIs', 'PERFORMANCE', 
                       'Performance testing of critical business endpoints', 3,
                       10, 30, 15)
            """, (mapping_id,))
        
        # 5. Auto-populate scenario endpoints with existing endpoints
        print("🔗 Linking existing endpoints to default scenarios...")
        
        cursor.execute("""
            INSERT OR IGNORE INTO test_scenario_endpoints (scenario_id, endpoint_id, execution_order, weight)
            SELECT 
                ts.id as scenario_id,
                ae.id as endpoint_id,
                ROW_NUMBER() OVER (PARTITION BY ts.id ORDER BY ae.id) as execution_order,
                CASE ae.http_method 
                    WHEN 'GET' THEN 3
                    WHEN 'POST' THEN 2  
                    WHEN 'PUT' THEN 1
                    WHEN 'DELETE' THEN 1
                    ELSE 2
                END as weight
            FROM test_scenarios ts
            JOIN application_endpoints ae ON ae.mapping_id = ts.mapping_id
            WHERE ts.scenario_type IN ('SMOKE', 'FUNCTIONAL')
              AND ae.endpoint_url LIKE '/%'  -- Valid endpoint URLs
        """)
        
        # For PERFORMANCE scenarios, only include GET endpoints initially
        cursor.execute("""
            INSERT OR IGNORE INTO test_scenario_endpoints (scenario_id, endpoint_id, execution_order, weight, is_critical)
            SELECT 
                ts.id as scenario_id,
                ae.id as endpoint_id,
                ROW_NUMBER() OVER (PARTITION BY ts.id ORDER BY ae.id) as execution_order,
                5 as weight,  -- Higher weight for performance
                1 as is_critical
            FROM test_scenarios ts
            JOIN application_endpoints ae ON ae.mapping_id = ts.mapping_id
            WHERE ts.scenario_type = 'PERFORMANCE'
              AND ae.http_method = 'GET'
              AND ae.endpoint_url LIKE '/%'
        """)
        
        conn.commit()
        
        # 6. Report results
        cursor.execute("SELECT COUNT(*) FROM test_scenarios")
        scenarios_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM test_scenario_endpoints") 
        scenario_endpoints_count = cursor.fetchone()[0]
        
        print(f"✅ Migration completed successfully!")
        print(f"📊 Created {scenarios_count} scenarios")
        print(f"🔗 Created {scenario_endpoints_count} scenario-endpoint relationships")
        
        # Show summary by scenario type
        cursor.execute("""
            SELECT scenario_type, COUNT(*) as count
            FROM test_scenarios 
            GROUP BY scenario_type
            ORDER BY count DESC
        """)
        
        print("\n📋 Scenarios by type:")
        for scenario_type, count in cursor.fetchall():
            print(f"   {scenario_type}: {count}")
        
        return True
        
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        conn.rollback()
        return False
        
    finally:
        conn.close()


if __name__ == "__main__":
    db_path = sys.argv[1] if len(sys.argv) > 1 else "data/qa_intelligence.db"
    
    if not Path(db_path).exists():
        print(f"❌ Database file not found: {db_path}")
        sys.exit(1)
    
    print(f"🔄 Running test scenarios migration on {db_path}")
    success = create_test_scenarios_tables(db_path)
    
    if success:
        print("🎉 Test scenarios system ready!")
        sys.exit(0)
    else:
        print("💥 Migration failed!")
        sys.exit(1)