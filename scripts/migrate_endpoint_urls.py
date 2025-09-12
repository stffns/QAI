#!/usr/bin/env python3
"""
Script para migrar endpoints existentes que contengan URLs completas a paths únicamente
"""

import sqlite3
import re
from pathlib import Path


def normalize_existing_endpoints():
    """Normaliza endpoints existentes que contengan URLs completas o variables de base URL"""
    
    db_path = Path("data/qa_intelligence.db")
    
    if not db_path.exists():
        print(f"❌ Database not found: {db_path}")
        return False
    
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    
    try:
        print("🔄 Starting endpoint URL normalization...")
        
        # Get all endpoints that might need normalization
        cursor.execute("""
            SELECT id, endpoint_name, endpoint_url, http_method 
            FROM application_endpoints 
            WHERE endpoint_url LIKE '%{{BASE_URL}}%' 
               OR endpoint_url LIKE '%{{baseUrl}}%'
               OR endpoint_url LIKE '%{{API_URL}}%'
               OR endpoint_url LIKE '%{{ENV}}%'
               OR endpoint_url LIKE '%{{COUNTRY}}%'
               OR endpoint_url LIKE '%{{env}}%'
               OR endpoint_url LIKE '%{{country}}%'
               OR endpoint_url LIKE '%{ENV}%'
               OR endpoint_url LIKE '%{COUNTRY}%'
               OR endpoint_url LIKE '%{env}%'
               OR endpoint_url LIKE '%{country}%'
               OR endpoint_url LIKE 'http%://%'
        """)
        
        endpoints_to_update = cursor.fetchall()
        
        print(f"📊 Found {len(endpoints_to_update)} endpoints to normalize")
        
        if not endpoints_to_update:
            print("✅ No endpoints need normalization")
            return True
        
        # Process each endpoint
        updated_count = 0
        
        for endpoint_id, name, url, method in endpoints_to_update:
            print(f"\n🔧 Processing: {name}")
            print(f"   Original URL: {url}")
            
            # Apply the same normalization logic as the importer
            normalized_url = normalize_url_path(url)
            
            print(f"   Normalized:   {normalized_url}")
            
            if normalized_url != url:
                # Update the endpoint
                cursor.execute("""
                    UPDATE application_endpoints 
                    SET endpoint_url = ? 
                    WHERE id = ?
                """, (normalized_url, endpoint_id))
                
                updated_count += 1
                print(f"   ✅ Updated")
            else:
                print(f"   ℹ️  No change needed")
        
        # Commit changes
        conn.commit()
        
        print(f"\n📈 Migration completed:")
        print(f"   📊 Total endpoints checked: {len(endpoints_to_update)}")
        print(f"   ✅ Endpoints updated: {updated_count}")
        print(f"   ℹ️  Endpoints unchanged: {len(endpoints_to_update) - updated_count}")
        
        return True
        
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        conn.rollback()
        return False
        
    finally:
        conn.close()


def normalize_url_path(raw_path: str) -> str:
    """Normalize a URL path using the same logic as PostmanEndpointImporter"""
    
    # Start with the raw path
    normalized = raw_path
    
    # Replace :param with {param} (Postman path parameters)
    PATH_VAR_PATTERN = re.compile(r":([A-Za-z0-9_]+)")
    normalized = PATH_VAR_PATTERN.sub(r"{\1}", normalized)
    
    # Extract just the path part (remove protocol and domain/base URL)
    if "://" in normalized:
        try:
            from urllib.parse import urlparse
            parsed = urlparse(normalized)
            normalized = parsed.path
            if parsed.query:
                normalized += f"?{parsed.query}"
        except:
            # Fallback: just take everything after the third slash
            parts = normalized.split('/', 3)
            if len(parts) > 3:
                normalized = '/' + parts[3]
    else:
        # Remove base URL, environment, and country variables from the path
        infrastructure_patterns = [
            # Base URL patterns
            r'\{\{BASE_URL\}\}',
            r'\{\{baseUrl\}\}', 
            r'\{\{base_url\}\}',
            r'\{\{API_URL\}\}',
            r'\{\{api_url\}\}',
            r'\{\{HOST\}\}',
            r'\{\{host\}\}',
            # Environment patterns  
            r'\{\{ENV\}\}',
            r'\{\{env\}\}',
            r'\{\{ENVIRONMENT\}\}',
            r'\{\{environment\}\}',
            # Country patterns
            r'\{\{COUNTRY\}\}',
            r'\{\{country\}\}',
            r'\{\{REGION\}\}',
            r'\{\{region\}\}',
            # Combined patterns (common in URLs like BASE_URL-ENV)
            r'-\{\{ENV\}\}',
            r'-\{\{env\}\}',
        ]
        
        for pattern in infrastructure_patterns:
            normalized = re.sub(pattern, '', normalized, flags=re.IGNORECASE)
        
        # Clean up any double slashes, leading/trailing slashes, or orphaned dashes
        normalized = re.sub(r'/+', '/', normalized)
        normalized = re.sub(r'/-+/', '/', normalized)  # Remove orphaned dashes between slashes  
        normalized = re.sub(r'^-+', '', normalized)    # Remove leading dashes
        normalized = normalized.strip('/')
    
    # Convert remaining Postman variables {{var}} to {var} format AND remove infrastructure variables
    VARIABLE_PATTERN = re.compile(r"{{\s*([A-Za-z0-9_\-\.]+)\s*}}")
    def replace_postman_var(match):
        var_name = match.group(1)
        # Skip infrastructure variables that should have been removed
        if var_name.upper() in ['ENV', 'ENVIRONMENT', 'COUNTRY', 'REGION', 'BASE_URL', 'BASEURL', 'API_URL', 'HOST']:
            return ''  # Remove any remaining infrastructure variables
        return f"{{{var_name}}}"
    
    normalized = VARIABLE_PATTERN.sub(replace_postman_var, normalized)
    
    # Also remove already converted infrastructure variables {VAR}
    CONVERTED_VARIABLE_PATTERN = re.compile(r"{\s*([A-Za-z0-9_\-\.]+)\s*}")
    def remove_infrastructure_vars(match):
        var_name = match.group(1)
        # Remove infrastructure variables
        if var_name.upper() in ['ENV', 'ENVIRONMENT', 'COUNTRY', 'REGION', 'BASE_URL', 'BASEURL', 'API_URL', 'HOST']:
            return ''  # Remove infrastructure variables
        return match.group(0)  # Keep business logic variables
    
    normalized = CONVERTED_VARIABLE_PATTERN.sub(remove_infrastructure_vars, normalized)
    
    # Clean up any remaining slashes or dashes after variable removal
    normalized = re.sub(r'/+', '/', normalized)
    normalized = re.sub(r'/-+/', '/', normalized)
    normalized = re.sub(r'^-+', '', normalized)
    normalized = normalized.strip('/')
    
    # Ensure it starts with /
    if not normalized.startswith('/'):
        normalized = '/' + normalized
        
    # Handle empty paths
    if normalized == '/':
        normalized = '/default'
        
    return normalized


def verify_migration():
    """Verifica que la migración fue exitosa"""
    
    db_path = Path("data/qa_intelligence.db")
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    
    try:
        print("\n🔍 Verifying migration results...")
        
        # Check for endpoints that still have infrastructure variables
        cursor.execute("""
            SELECT COUNT(*) FROM application_endpoints 
            WHERE endpoint_url LIKE '%{{BASE_URL}}%' 
               OR endpoint_url LIKE '%{{baseUrl}}%'
               OR endpoint_url LIKE '%{{API_URL}}%'
               OR endpoint_url LIKE '%{{ENV}}%'
               OR endpoint_url LIKE '%{{COUNTRY}}%'
               OR endpoint_url LIKE '%{ENV}%'
               OR endpoint_url LIKE '%{COUNTRY}%'
               OR endpoint_url LIKE 'http%://%'
        """)
        
        problematic_count = cursor.fetchone()[0]
        
        # Get some examples of normalized endpoints
        cursor.execute("""
            SELECT endpoint_name, endpoint_url, http_method 
            FROM application_endpoints 
            WHERE endpoint_url LIKE '/%' 
            LIMIT 5
        """)
        
        examples = cursor.fetchall()
        
        print(f"📊 Verification results:")
        print(f"   ❗ Endpoints still needing normalization: {problematic_count}")
        print(f"   ✅ Example normalized endpoints:")
        
        for name, url, method in examples:
            print(f"      • {method} {name} → {url}")
        
        return problematic_count == 0
        
    finally:
        conn.close()


if __name__ == "__main__":
    print("🔄 Endpoint URL Normalization Migration")
    print("=" * 60)
    
    # Run migration
    success = normalize_existing_endpoints()
    
    if success:
        # Verify results
        verify_success = verify_migration()
        
        if verify_success:
            print("\n🎉 Migration completed successfully!")
            print("✅ All endpoints now use path-only URLs")
            print("📁 Base URLs are stored in app_environment_country_mappings table")
        else:
            print("\n⚠️ Migration completed with some issues")
            print("🔧 Some endpoints may need manual review")
    else:
        print("\n💥 Migration failed!")
    
    print("\n" + "=" * 60)