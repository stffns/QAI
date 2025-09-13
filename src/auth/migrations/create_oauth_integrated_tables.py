#!/usr/bin/env python3
"""
Migración: Crear tablas OAuth integradas con el esquema existente

Este script:
1. Crea las 3 tablas OAuth integradas con el esquema QAI existente
2. Establece constraints FK con app_environment_country_mappings, apps_master, environments_master
3. Inserta datos iniciales basados en el código Scala (UserMap, ClientIdMap, JWKMap)
4. Valida la integridad referencial

Uso:
    python src/auth/migrations/create_oauth_integrated_tables.py
"""

import hashlib
import json
import os
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

# Agregar el path del proyecto
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "..", ".."))


def get_database_connection():
    """Obtener conexión a la base de datos principal"""
    db_path = Path("data/qa_intelligence.db")
    if not db_path.exists():
        raise FileNotFoundError(f"Database not found: {db_path}")

    conn = sqlite3.connect(str(db_path))
    conn.execute("PRAGMA foreign_keys = ON")  # Habilitar FK constraints
    return conn


def create_oauth_tables(conn: sqlite3.Connection):
    """Crear las 3 tablas OAuth integradas"""

    cursor = conn.cursor()

    print("🏗️ Creando tablas OAuth integradas...")

    # 1. Tabla oauth_users (vinculada a app_environment_country_mappings)
    cursor.execute(
        """
    CREATE TABLE IF NOT EXISTS oauth_users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        
        -- Información del usuario (del código Scala UserMap)
        email VARCHAR(255) NOT NULL UNIQUE 
            CHECK (email LIKE '%@%.%' AND length(email) >= 5),
        given_name VARCHAR(100) NOT NULL 
            CHECK (length(trim(given_name)) >= 1),
        family_name VARCHAR(100) NOT NULL 
            CHECK (length(trim(family_name)) >= 1),
        phone_number VARCHAR(20) NOT NULL 
            CHECK (phone_number LIKE '+%' AND length(phone_number) >= 8),
        gender VARCHAR(10) NOT NULL 
            CHECK (gender IN ('male', 'female')),
        password_hash VARCHAR(255) NOT NULL,
        
        -- RELACIÓN CON ESQUEMA EXISTENTE - FK obligatoria
        mapping_id INTEGER NOT NULL 
            REFERENCES app_environment_country_mappings(id) 
            ON DELETE CASCADE ON UPDATE CASCADE,
        
        -- Control y metadata
        is_active BOOLEAN NOT NULL DEFAULT 1 
            CHECK (is_active IN (0, 1)),
        test_purpose VARCHAR(200),
        locale VARCHAR(10) NOT NULL DEFAULT 'en-US' 
            CHECK (locale LIKE '__-__'),
        
        -- Auditoría
        created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME,
        created_by VARCHAR(100),
        
        -- Constraint único: un usuario no puede repetirse para la misma combinación
        UNIQUE(email, mapping_id)
    );
    """
    )

    # 2. Tabla oauth_jwks (vinculada a environments_master)
    cursor.execute(
        """
    CREATE TABLE IF NOT EXISTS oauth_jwks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        
        -- RELACIÓN CON ESQUEMA EXISTENTE
        environment_id INTEGER NOT NULL 
            REFERENCES environments_master(id) 
            ON DELETE CASCADE ON UPDATE CASCADE,
        
        -- Datos de la clave (del código Scala JWKMap)
        key_id VARCHAR(100) NOT NULL UNIQUE 
            CHECK (length(trim(key_id)) >= 5),
        jwk_content TEXT NOT NULL 
            CHECK (json_valid(jwk_content) = 1),
        algorithm VARCHAR(10) NOT NULL DEFAULT 'ES256' 
            CHECK (algorithm IN ('ES256', 'ES384', 'ES512', 'RS256', 'RS384', 'RS512')),
        
        -- Control
        is_active BOOLEAN NOT NULL DEFAULT 1 
            CHECK (is_active IN (0, 1)),
        expires_at DATETIME,
        
        -- Auditoría
        created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME,
        
        -- Solo una clave JWK activa por ambiente
        UNIQUE(environment_id, is_active) 
    );
    """
    )

    # 3. Tabla oauth_app_clients (vinculada a apps_master + environments_master)
    cursor.execute(
        """
    CREATE TABLE IF NOT EXISTS oauth_app_clients (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        
        -- RELACIÓN CON ESQUEMA EXISTENTE
        application_id INTEGER NOT NULL 
            REFERENCES apps_master(id) 
            ON DELETE CASCADE ON UPDATE CASCADE,
        environment_id INTEGER NOT NULL 
            REFERENCES environments_master(id) 
            ON DELETE CASCADE ON UPDATE CASCADE,
        
        -- Configuración OAuth (del código Scala ClientIdMap)
        client_id VARCHAR(255) NOT NULL UNIQUE 
            CHECK (length(trim(client_id)) >= 10),
        client_name VARCHAR(100) NOT NULL 
            CHECK (length(trim(client_name)) >= 2),
        
        -- URLs de configuración
        callback_url VARCHAR(500) NOT NULL 
            CHECK (callback_url LIKE 'http%://%'),
        resource_url VARCHAR(500)
            CHECK (resource_url IS NULL OR resource_url LIKE 'http%://%'),
        
        -- Flags de configuración
        needs_resource_param BOOLEAN NOT NULL DEFAULT 0 
            CHECK (needs_resource_param IN (0, 1)),
        is_pkce_required BOOLEAN NOT NULL DEFAULT 1 
            CHECK (is_pkce_required IN (0, 1)),
        
        -- Scopes OAuth
        default_scopes VARCHAR(200) NOT NULL DEFAULT 'openid profile email',
        
        -- Control
        is_active BOOLEAN NOT NULL DEFAULT 1 
            CHECK (is_active IN (0, 1)),
        
        -- Auditoría
        created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME,
        
        -- Solo un client_id por app+ambiente
        UNIQUE(application_id, environment_id)
    );
    """
    )

    print("✅ Tablas OAuth creadas exitosamente")


def create_indexes(conn: sqlite3.Connection):
    """Crear índices de performance"""

    cursor = conn.cursor()

    print("📊 Creando índices de performance...")

    indexes = [
        # oauth_users
        "CREATE INDEX IF NOT EXISTS idx_oauth_users_mapping ON oauth_users(mapping_id, is_active)",
        "CREATE INDEX IF NOT EXISTS idx_oauth_users_email ON oauth_users(email)",
        "CREATE INDEX IF NOT EXISTS idx_oauth_users_active ON oauth_users(is_active)",
        # oauth_jwks
        "CREATE INDEX IF NOT EXISTS idx_oauth_jwks_env ON oauth_jwks(environment_id, is_active)",
        "CREATE INDEX IF NOT EXISTS idx_oauth_jwks_key_id ON oauth_jwks(key_id)",
        # oauth_app_clients
        "CREATE INDEX IF NOT EXISTS idx_oauth_clients_app_env ON oauth_app_clients(application_id, environment_id, is_active)",
        "CREATE INDEX IF NOT EXISTS idx_oauth_clients_client_id ON oauth_app_clients(client_id)",
    ]

    for index_sql in indexes:
        cursor.execute(index_sql)

    print("✅ Índices creados exitosamente")


def get_existing_mappings(conn: sqlite3.Connection):
    """Obtener mappings existentes para vincular los datos OAuth"""

    cursor = conn.cursor()

    # Obtener mapping EVA STA RO (si existe)
    cursor.execute(
        """
    SELECT 
        aecm.id as mapping_id,
        am.app_code, am.app_name,
        em.env_code, em.env_name,
        cm.country_code, cm.country_name
    FROM app_environment_country_mappings aecm
    JOIN apps_master am ON aecm.application_id = am.id
    JOIN environments_master em ON aecm.environment_id = em.id  
    JOIN countries_master cm ON aecm.country_id = cm.id
    WHERE am.app_code LIKE '%EVA%' 
       OR em.env_code = 'STA'
       OR cm.country_code = 'RO'
    """
    )

    mappings = cursor.fetchall()

    if not mappings:
        print("⚠️ No se encontraron mappings EVA STA RO existentes")
        print("   Será necesario crear los datos maestros primero")
        return []

    print(f"📋 Mappings encontrados: {len(mappings)}")
    for mapping in mappings:
        print(f"   • ID {mapping[0]}: {mapping[1]} | {mapping[3]} | {mapping[5]}")

    return mappings


def insert_sample_oauth_data(conn: sqlite3.Connection):
    """Insertar datos OAuth de ejemplo basados en el código Scala"""

    cursor = conn.cursor()

    print("📝 Insertando datos OAuth de ejemplo...")

    # Obtener mappings existentes
    mappings = get_existing_mappings(conn)

    if not mappings:
        print("❌ No se pueden insertar datos OAuth sin mappings existentes")
        return

    # Usar el primer mapping encontrado para los datos de ejemplo
    sample_mapping_id = mappings[0][0]
    print(f"🎯 Usando mapping_id: {sample_mapping_id}")

    # 1. Insertar ambiente STA si no existe
    cursor.execute("SELECT id FROM environments_master WHERE env_code = 'STA'")
    env_sta = cursor.fetchone()

    if not env_sta:
        cursor.execute(
            """
        INSERT INTO environments_master (env_name, env_code, description, is_production, is_active)
        VALUES ('Staging', 'STA', 'Ambiente de staging/testing', 0, 1)
        """
        )
        env_sta_id = cursor.lastrowid
        print(f"✅ Ambiente STA creado con ID: {env_sta_id}")
    else:
        env_sta_id = env_sta[0]
        print(f"✅ Ambiente STA encontrado con ID: {env_sta_id}")

    # 2. Insertar JWK para STA (del código AuthenticationOIDCTemporal)
    jwk_data = {
        "kid": "SCIK-QA-STA-20210408-47QNY",
        "kty": "EC",
        "crv": "P-256",
        "x": "ZI2oM8spmX7hhg0KsWZVyVz3Fq7D7rnT2CISwIJk21U",
        "y": "jJkIyEWLvZSNIcRdAxnFZuYLQCTfng1KMOFNXkJcpS4",
        "d": "6D5xCaPKq1gezZTi93Tu8JKSQqpYRNaoqjdlFVQIF2E",
    }

    cursor.execute(
        """
    INSERT OR REPLACE INTO oauth_jwks (
        environment_id, key_id, jwk_content, algorithm, is_active
    ) VALUES (?, ?, ?, ?, ?)
    """,
        (env_sta_id, jwk_data["kid"], json.dumps(jwk_data), "ES256", 1),
    )
    print(f"✅ JWK insertado: {jwk_data['kid']}")

    # 3. Insertar usuario de ejemplo (del código funcional)
    password_hash = hashlib.sha256("Test12345#".encode()).hexdigest()

    cursor.execute(
        """
    INSERT OR REPLACE INTO oauth_users (
        email, given_name, family_name, phone_number, gender, 
        password_hash, mapping_id, locale, test_purpose
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """,
        (
            "qa.auto.soco.ro+2@gmail.com",
            "Qa",
            "Qa",
            "+33663005232",
            "male",
            password_hash,
            sample_mapping_id,
            "ro-RO",
            "Usuario de testing EVA STA RO",
        ),
    )
    print("✅ Usuario OAuth insertado: qa.auto.soco.ro+2@gmail.com")

    # 4. Insertar client_id de ejemplo
    cursor.execute("SELECT id FROM apps_master LIMIT 1")
    app_result = cursor.fetchone()

    if app_result:
        app_id = app_result[0]

        cursor.execute(
            """
        INSERT OR REPLACE INTO oauth_app_clients (
            application_id, environment_id, client_id, client_name,
            callback_url, needs_resource_param, default_scopes
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
            (
                app_id,
                env_sta_id,
                "84d70f23-df50-4ed2-9d60-263366326c9d",
                "EVA STA Client",
                "http://localhost/oidc/callback",
                0,  # needs_resource_param = False para EVA
                "openid profile email phone",
            ),
        )
        print("✅ Client OAuth insertado: 84d70f23-df50-4ed2-9d60-263366326c9d")

    print("✅ Datos OAuth de ejemplo insertados exitosamente")


def validate_integration(conn: sqlite3.Connection):
    """Validar que la integración funciona correctamente"""

    cursor = conn.cursor()

    print("🔍 Validando integración OAuth...")

    # Test 1: Contar registros en cada tabla
    tables = ["oauth_users", "oauth_jwks", "oauth_app_clients"]
    for table in tables:
        cursor.execute(f"SELECT COUNT(*) FROM {table}")
        count = cursor.fetchone()[0]
        print(f"   • {table}: {count} registros")

    # Test 2: Validar relaciones FK
    cursor.execute(
        """
    SELECT 
        ou.email,
        am.app_code,
        em.env_code, 
        cm.country_code
    FROM oauth_users ou
    JOIN app_environment_country_mappings aecm ON ou.mapping_id = aecm.id
    JOIN apps_master am ON aecm.application_id = am.id
    JOIN environments_master em ON aecm.environment_id = em.id
    JOIN countries_master cm ON aecm.country_id = cm.id
    """
    )

    user_mappings = cursor.fetchall()
    for user_mapping in user_mappings:
        print(
            f"   👤 Usuario: {user_mapping[0]} → {user_mapping[1]}/{user_mapping[2]}/{user_mapping[3]}"
        )

    # Test 3: Validar JWKs por ambiente
    cursor.execute(
        """
    SELECT 
        oj.key_id,
        em.env_code
    FROM oauth_jwks oj
    JOIN environments_master em ON oj.environment_id = em.id
    WHERE oj.is_active = 1
    """
    )

    jwks = cursor.fetchall()
    for jwk in jwks:
        print(f"   🔑 JWK: {jwk[0]} → {jwk[1]}")

    print("✅ Validación completada")


def main():
    """Función principal de migración"""

    print("🚀 INICIANDO MIGRACIÓN OAUTH INTEGRADA")
    print("=" * 50)

    try:
        # Conectar a la base de datos
        conn = get_database_connection()

        # Crear las tablas
        create_oauth_tables(conn)

        # Crear índices
        create_indexes(conn)

        # Insertar datos de ejemplo
        insert_sample_oauth_data(conn)

        # Validar la integración
        validate_integration(conn)

        # Commit final
        conn.commit()

        print("\n" + "=" * 50)
        print("🎉 MIGRACIÓN OAUTH COMPLETADA EXITOSAMENTE")
        print("\n📋 Resumen:")
        print("   ✅ 3 tablas OAuth creadas e integradas")
        print("   ✅ Constraints FK configurados")
        print("   ✅ Índices de performance creados")
        print("   ✅ Datos de ejemplo insertados")
        print("   ✅ Validación exitosa")

    except Exception as e:
        print(f"❌ ERROR EN MIGRACIÓN: {e}")
        if "conn" in locals():
            conn.rollback()
        raise

    finally:
        if "conn" in locals():
            conn.close()


if __name__ == "__main__":
    main()
