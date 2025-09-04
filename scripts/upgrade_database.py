#!/usr/bin/env python3
"""
Script para aplicar mejoras inmediatas a la base de datos QA Intelligence
Ejecuta las mejoras de Fase 1 de manera segura con rollback
"""

import sqlite3
import json
import shutil
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any


class DatabaseUpgrader:
    """Aplicador seguro de mejoras a la base de datos"""

    def __init__(self, db_path: str):
        self.db_path = Path(db_path)
        self.backup_path = None
        self.applied_changes = []

    def create_backup(self) -> str:
        """Crear backup antes de aplicar cambios"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"{self.db_path.stem}_backup_{timestamp}.db"
        self.backup_path = self.db_path.parent / backup_name

        shutil.copy2(self.db_path, self.backup_path)
        print(f"✅ Backup creado: {self.backup_path}")
        return str(self.backup_path)

    def apply_improvements(self) -> Dict[str, Any]:
        """Aplicar todas las mejoras de Fase 1"""
        results = {
            "start_time": datetime.now().isoformat(),
            "backup_location": None,
            "changes_applied": [],
            "errors": [],
            "success": False,
        }

        try:
            # Crear backup
            results["backup_location"] = self.create_backup()

            # Conectar a la base de datos
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # 1. Activar foreign keys
            print("🔧 Activando constraints de integridad...")
            cursor.execute("PRAGMA foreign_keys = ON")
            results["changes_applied"].append("foreign_keys_enabled")

            # 2. Agregar índices de performance
            indexes = [
                ("idx_test_runs_status", "test_runs", "status"),
                ("idx_test_runs_app_country", "test_runs", "app_id, country_id"),
                ("idx_performance_results_run", "performance_results", "run_id"),
                ("idx_batch_executions_status", "batch_executions", "status"),
                ("idx_rag_metadata_app_env", "rag_metadata", "app_name, environment"),
                ("idx_rag_vectors_content_type", "rag_vectors", "content_type"),
                ("idx_users_email", "users", "email"),
                ("idx_users_username", "users", "username"),
                ("idx_audit_temporal", "batch_executions", "created_at"),
            ]

            print("🔧 Creando índices de performance...")
            for index_name, table_name, columns in indexes:
                try:
                    sql = f"CREATE INDEX IF NOT EXISTS {index_name} ON {table_name}({columns})"
                    cursor.execute(sql)
                    results["changes_applied"].append(f"index_created_{index_name}")
                    print(f"  ✅ Índice creado: {index_name}")
                except sqlite3.Error as e:
                    error_msg = f"Error creating index {index_name}: {e}"
                    results["errors"].append(error_msg)
                    print(f"  ❌ {error_msg}")

            # 3. Agregar campos de seguridad a la tabla users (si no existen)
            print("🔧 Mejorando tabla de usuarios...")
            security_fields = [
                ("is_locked", "BOOLEAN DEFAULT 0"),
                ("failed_login_attempts", "INTEGER DEFAULT 0"),
                ("last_login_attempt", "DATETIME"),
                ("password_changed_at", "DATETIME"),
                ("api_key_hash", "VARCHAR(255)"),
                ("session_timeout_minutes", "INTEGER DEFAULT 480"),
            ]

            # Verificar qué campos ya existen
            cursor.execute("PRAGMA table_info(users)")
            existing_columns = {row[1] for row in cursor.fetchall()}

            for field_name, field_definition in security_fields:
                if field_name not in existing_columns:
                    try:
                        sql = f"ALTER TABLE users ADD COLUMN {field_name} {field_definition}"
                        cursor.execute(sql)
                        results["changes_applied"].append(
                            f"user_field_added_{field_name}"
                        )
                        print(f"  ✅ Campo agregado: {field_name}")
                    except sqlite3.Error as e:
                        error_msg = f"Error adding field {field_name}: {e}"
                        results["errors"].append(error_msg)
                        print(f"  ❌ {error_msg}")
                else:
                    print(f"  ℹ️  Campo ya existe: {field_name}")

            # 4. Crear tabla de audit_logs si no existe
            print("🔧 Creando sistema de auditoría...")
            audit_table_sql = """
            CREATE TABLE IF NOT EXISTS audit_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER REFERENCES users(id),
                table_name VARCHAR(100) NOT NULL,
                record_id VARCHAR(255),
                action_type VARCHAR(20) NOT NULL,
                old_values TEXT,
                new_values TEXT,
                ip_address VARCHAR(45),
                user_agent TEXT,
                occurred_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                session_id VARCHAR(255)
            )
            """
            cursor.execute(audit_table_sql)
            results["changes_applied"].append("audit_table_created")

            # Índices para audit_logs
            audit_indexes = [
                ("idx_audit_logs_user", "audit_logs", "user_id"),
                ("idx_audit_logs_table", "audit_logs", "table_name"),
                ("idx_audit_logs_time", "audit_logs", "occurred_at"),
                ("idx_audit_logs_action", "audit_logs", "action_type"),
            ]

            for index_name, table_name, columns in audit_indexes:
                cursor.execute(
                    f"CREATE INDEX IF NOT EXISTS {index_name} ON {table_name}({columns})"
                )
                results["changes_applied"].append(f"audit_index_created_{index_name}")

            print("  ✅ Sistema de auditoría creado")

            # 5. Actualizar configuración de base de datos
            print("🔧 Optimizando configuración de base de datos...")
            optimizations = [
                "PRAGMA journal_mode = WAL",  # Write-Ahead Logging
                "PRAGMA synchronous = NORMAL",  # Balance seguridad/performance
                "PRAGMA cache_size = 10000",  # Cache más grande
                "PRAGMA temp_store = MEMORY",  # Tablas temporales en memoria
                "PRAGMA mmap_size = 67108864",  # 64MB memory mapping
            ]

            for pragma in optimizations:
                cursor.execute(pragma)
                results["changes_applied"].append(f"optimization_{pragma.split()[1]}")

            print("  ✅ Optimizaciones aplicadas")

            # Commit todos los cambios
            conn.commit()
            conn.close()

            results["success"] = True
            results["end_time"] = datetime.now().isoformat()

            print(f"\n🎉 Mejoras aplicadas exitosamente!")
            print(f"📊 Total de cambios: {len(results['changes_applied'])}")
            print(f"❌ Errores: {len(results['errors'])}")

        except Exception as e:
            results["errors"].append(f"Critical error: {e}")
            results["success"] = False
            print(f"\n💥 Error crítico: {e}")

            # Restaurar backup si es necesario
            if self.backup_path and self.backup_path.exists():
                print("🔄 Restaurando backup...")
                shutil.copy2(self.backup_path, self.db_path)
                print("✅ Backup restaurado")

        return results

    def verify_improvements(self) -> Dict[str, Any]:
        """Verificar que las mejoras se aplicaron correctamente"""
        verification = {
            "foreign_keys_enabled": False,
            "indexes_created": 0,
            "audit_table_exists": False,
            "user_fields_added": 0,
            "database_optimized": False,
        }

        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Verificar foreign keys
            cursor.execute("PRAGMA foreign_keys")
            verification["foreign_keys_enabled"] = cursor.fetchone()[0] == 1

            # Contar índices
            cursor.execute(
                "SELECT COUNT(*) FROM sqlite_master WHERE type='index' AND name LIKE 'idx_%'"
            )
            verification["indexes_created"] = cursor.fetchone()[0]

            # Verificar tabla de auditoría
            cursor.execute(
                "SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name='audit_logs'"
            )
            verification["audit_table_exists"] = cursor.fetchone()[0] == 1

            # Verificar campos en users
            cursor.execute("PRAGMA table_info(users)")
            user_columns = {row[1] for row in cursor.fetchall()}
            security_fields = [
                "is_locked",
                "failed_login_attempts",
                "last_login_attempt",
                "password_changed_at",
                "api_key_hash",
                "session_timeout_minutes",
            ]
            verification["user_fields_added"] = sum(
                1 for field in security_fields if field in user_columns
            )

            # Verificar optimizaciones
            cursor.execute("PRAGMA journal_mode")
            verification["database_optimized"] = cursor.fetchone()[0].upper() == "WAL"

            conn.close()

        except Exception as e:
            print(f"Error en verificación: {e}")

        return verification


def main():
    """Función principal"""
    db_path = "data/qa_intelligence.db"

    if not Path(db_path).exists():
        print(f"❌ Error: Base de datos no encontrada en {db_path}")
        return

    print("🚀 INICIANDO MEJORAS DE QA INTELLIGENCE DATABASE")
    print("=" * 60)

    # Crear upgrader
    upgrader = DatabaseUpgrader(db_path)

    # Aplicar mejoras
    results = upgrader.apply_improvements()

    # Verificar resultados
    if results["success"]:
        verification = upgrader.verify_improvements()

        print(f"\n📋 VERIFICACIÓN DE MEJORAS:")
        print(
            f"🔗 Foreign keys habilitado: {'✅' if verification['foreign_keys_enabled'] else '❌'}"
        )
        print(f"📊 Índices creados: {verification['indexes_created']}")
        print(
            f"📝 Tabla de auditoría: {'✅' if verification['audit_table_exists'] else '❌'}"
        )
        print(f"👤 Campos de seguridad: {verification['user_fields_added']}/6")
        print(
            f"⚡ Base optimizada: {'✅' if verification['database_optimized'] else '❌'}"
        )

        # Guardar reporte
        report_path = f"docs/database_upgrade_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        upgrade_report = {
            "upgrade_results": results,
            "verification": verification,
            "recommendations": [
                "Implementar validación Pydantic en modelos",
                "Configurar sistema de logging para auditoría",
                "Implementar rate limiting para APIs",
                "Considerar migración a PostgreSQL para producción",
            ],
        }

        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(upgrade_report, f, indent=2, ensure_ascii=False)

        print(f"\n📄 Reporte guardado en: {report_path}")
        print(f"💾 Backup disponible en: {results['backup_location']}")

    else:
        print(f"\n❌ Las mejoras no se aplicaron correctamente")
        print(f"🔄 Backup restaurado automáticamente")

    print("\n✅ Proceso completado!")


if __name__ == "__main__":
    main()
