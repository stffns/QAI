#!/usr/bin/env python3
"""
Análisis técnico de la base de datos QA Intelligence
Genera métricas, detecta problemas y propone mejoras específicas
"""

import sqlite3
import json
from pathlib import Path
from typing import Dict, List, Tuple, Any
from datetime import datetime


class QADatabaseAnalyzer:
    """Analizador profesional para la base de datos QA Intelligence"""

    def __init__(self, db_path: str):
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row

    def get_database_info(self) -> Dict[str, Any]:
        """Información general de la base de datos"""
        cursor = self.conn.cursor()

        # Obtener todas las tablas
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]

        # Calcular tamaño total
        cursor.execute("PRAGMA page_count")
        page_count = cursor.fetchone()[0]
        cursor.execute("PRAGMA page_size")
        page_size = cursor.fetchone()[0]
        total_size = page_count * page_size

        return {
            "total_tables": len(tables),
            "table_names": tables,
            "database_size_bytes": total_size,
            "database_size_mb": round(total_size / 1024 / 1024, 2),
        }

    def analyze_table_structure(self) -> Dict[str, Any]:
        """Analiza la estructura de cada tabla"""
        cursor = self.conn.cursor()
        analysis = {}

        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]

        for table in tables:
            # Información de la tabla
            cursor.execute(f"PRAGMA table_info({table})")
            columns = cursor.fetchall()

            # Contar registros
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            row_count = cursor.fetchone()[0]

            # Obtener índices
            cursor.execute(f"PRAGMA index_list({table})")
            indexes = cursor.fetchall()

            # Detectar foreign keys
            cursor.execute(f"PRAGMA foreign_key_list({table})")
            foreign_keys = cursor.fetchall()

            analysis[table] = {
                "columns": len(columns),
                "row_count": row_count,
                "indexes": len(indexes),
                "foreign_keys": len(foreign_keys),
                "column_details": [
                    {
                        "name": col[1],
                        "type": col[2],
                        "not_null": bool(col[3]),
                        "default_value": col[4],
                        "primary_key": bool(col[5]),
                    }
                    for col in columns
                ],
            }

        return analysis

    def detect_data_quality_issues(self) -> Dict[str, List[str]]:
        """Detecta problemas de calidad de datos"""
        cursor = self.conn.cursor()
        issues = {
            "missing_data": [],
            "data_inconsistencies": [],
            "referential_integrity": [],
            "performance_issues": [],
        }

        # Verificar datos faltantes en campos críticos
        critical_tables = ["users", "test_runs", "apps_master"]
        for table in critical_tables:
            try:
                cursor.execute(f"SELECT COUNT(*) FROM {table} WHERE created_at IS NULL")
                null_created = cursor.fetchone()[0]
                if null_created > 0:
                    issues["missing_data"].append(
                        f"Table {table}: {null_created} records missing created_at"
                    )
            except sqlite3.OperationalError:
                pass

        # Verificar integridad referencial
        try:
            cursor.execute(
                """
                SELECT COUNT(*) FROM test_executions te
                LEFT JOIN apps_master am ON te.application_id = am.id
                WHERE am.id IS NULL
            """
            )
            orphaned = cursor.fetchone()[0]
            if orphaned > 0:
                issues["referential_integrity"].append(
                    f"test_executions: {orphaned} records with invalid application_id"
                )
        except sqlite3.OperationalError:
            pass

        # Verificar consistencia de datos
        try:
            cursor.execute(
                """
                SELECT COUNT(*) FROM test_runs 
                WHERE end_time < start_time
            """
            )
            invalid_times = cursor.fetchone()[0]
            if invalid_times > 0:
                issues["data_inconsistencies"].append(
                    f"test_runs: {invalid_times} records with end_time before start_time"
                )
        except sqlite3.OperationalError:
            pass

        return issues

    def analyze_performance_metrics(self) -> Dict[str, Any]:
        """Analiza métricas de performance de la base de datos"""
        cursor = self.conn.cursor()

        # Tablas más grandes
        table_sizes = {}
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]

        for table in tables:
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            count = cursor.fetchone()[0]
            table_sizes[table] = count

        # Ordenar por tamaño
        largest_tables = sorted(table_sizes.items(), key=lambda x: x[1], reverse=True)[
            :10
        ]

        # Verificar índices faltantes
        missing_indexes = []

        # Verificar si tablas grandes tienen índices en columnas de fecha
        for table, count in largest_tables:
            if count > 1000:  # Solo para tablas con datos significativos
                try:
                    cursor.execute(f"PRAGMA table_info({table})")
                    columns = cursor.fetchall()
                    date_columns = [
                        col[1]
                        for col in columns
                        if "date" in col[1].lower() or "time" in col[1].lower()
                    ]

                    for col in date_columns:
                        cursor.execute(f"PRAGMA index_list({table})")
                        indexes = cursor.fetchall()
                        has_index = any(col in str(idx) for idx in indexes)
                        if not has_index:
                            missing_indexes.append(f"{table}.{col}")
                except sqlite3.OperationalError:
                    pass

        return {
            "largest_tables": largest_tables,
            "total_records": sum(table_sizes.values()),
            "missing_indexes": missing_indexes,
            "tables_without_data": [
                table for table, count in table_sizes.items() if count == 0
            ],
        }

    def generate_migration_script(self) -> str:
        """Genera script SQL para mejoras inmediatas"""
        migrations = []

        # Agregar índices faltantes
        performance_analysis = self.analyze_performance_metrics()
        for missing_index in performance_analysis["missing_indexes"]:
            table, column = missing_index.split(".")
            migrations.append(
                f"CREATE INDEX IF NOT EXISTS idx_{table}_{column} ON {table}({column});"
            )

        # Agregar constraints faltantes
        migrations.extend(
            [
                "-- Agregar constraints de integridad",
                "PRAGMA foreign_keys = ON;",
                "",
                "-- Agregar índices para performance",
                "CREATE INDEX IF NOT EXISTS idx_test_runs_status ON test_runs(status);",
                "CREATE INDEX IF NOT EXISTS idx_test_runs_app_country ON test_runs(app_id, country_id);",
                "CREATE INDEX IF NOT EXISTS idx_performance_results_run ON performance_results(run_id);",
                "CREATE INDEX IF NOT EXISTS idx_batch_executions_status ON batch_executions(status);",
                "",
                "-- Agregar índices para RAG queries",
                "CREATE INDEX IF NOT EXISTS idx_rag_metadata_app_env ON rag_metadata(app_name, environment);",
                "CREATE INDEX IF NOT EXISTS idx_rag_vectors_content_type ON rag_vectors(content_type);",
            ]
        )

        return "\n".join(migrations)

    def generate_improvement_recommendations(self) -> Dict[str, List[str]]:
        """Genera recomendaciones específicas de mejora"""
        structure_analysis = self.analyze_table_structure()
        quality_issues = self.detect_data_quality_issues()
        performance_analysis = self.analyze_performance_metrics()

        recommendations = {
            "immediate_fixes": [],
            "security_improvements": [],
            "performance_optimizations": [],
            "data_quality_improvements": [],
            "architectural_changes": [],
        }

        # Fixes inmediatos
        if quality_issues["missing_data"]:
            recommendations["immediate_fixes"].extend(
                [
                    "Corregir registros con campos obligatorios NULL",
                    "Implementar validación de datos en la aplicación",
                ]
            )

        if quality_issues["referential_integrity"]:
            recommendations["immediate_fixes"].extend(
                ["Limpiar registros huérfanos", "Activar PRAGMA foreign_keys = ON"]
            )

        # Mejoras de seguridad
        user_table = structure_analysis.get("users", {})
        if user_table:
            recommendations["security_improvements"].extend(
                [
                    "Implementar hash seguro de passwords (bcrypt/argon2)",
                    "Agregar tabla de audit_logs",
                    "Implementar rate limiting para autenticación",
                    "Agregar campos de seguridad (is_locked, failed_attempts)",
                ]
            )

        # Optimizaciones de performance
        if performance_analysis["missing_indexes"]:
            recommendations["performance_optimizations"].extend(
                [
                    f"Agregar {len(performance_analysis['missing_indexes'])} índices faltantes",
                    "Implementar particionamiento para tablas grandes",
                    "Considerar migración a PostgreSQL para mejor performance",
                ]
            )

        # Mejoras de calidad de datos
        recommendations["data_quality_improvements"].extend(
            [
                "Implementar validaciones Pydantic para todos los modelos",
                "Agregar constraints CHECK para rangos de valores",
                "Implementar limpieza automática de datos obsoletos",
            ]
        )

        # Cambios arquitecturales
        recommendations["architectural_changes"].extend(
            [
                "Separar esquemas por dominio (security, execution, config)",
                "Implementar versionado de esquemas con Alembic",
                "Migrar a PostgreSQL con extensiones (pgvector, pg_stat_statements)",
                "Implementar sistema de eventos para auditoría",
                "Agregar vistas materializadas para analytics",
            ]
        )

        return recommendations

    def generate_report(self) -> Dict[str, Any]:
        """Genera reporte completo de análisis"""
        return {
            "analysis_timestamp": datetime.now().isoformat(),
            "database_info": self.get_database_info(),
            "table_structure": self.analyze_table_structure(),
            "data_quality_issues": self.detect_data_quality_issues(),
            "performance_metrics": self.analyze_performance_metrics(),
            "improvement_recommendations": self.generate_improvement_recommendations(),
            "migration_script": self.generate_migration_script(),
        }

    def close(self):
        """Cierra la conexión a la base de datos"""
        self.conn.close()


def main():
    """Función principal para ejecutar el análisis"""
    db_path = "data/qa_intelligence.db"

    if not Path(db_path).exists():
        print(f"❌ Error: Base de datos no encontrada en {db_path}")
        return

    print("🔍 Iniciando análisis de QA Intelligence Database...")

    analyzer = QADatabaseAnalyzer(db_path)
    report = analyzer.generate_report()
    analyzer.close()

    # Guardar reporte completo
    report_path = "docs/DATABASE_TECHNICAL_ANALYSIS.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    # Mostrar resumen en consola
    print("\n📊 RESUMEN DEL ANÁLISIS")
    print("=" * 50)

    db_info = report["database_info"]
    print(f"📁 Total de tablas: {db_info['total_tables']}")
    print(f"💾 Tamaño de BD: {db_info['database_size_mb']} MB")

    performance = report["performance_metrics"]
    print(f"📈 Total de registros: {performance['total_records']:,}")
    print(f"🔍 Índices faltantes: {len(performance['missing_indexes'])}")
    print(f"📊 Tablas sin datos: {len(performance['tables_without_data'])}")

    quality = report["data_quality_issues"]
    total_issues = sum(len(issues) for issues in quality.values())
    print(f"⚠️  Issues de calidad: {total_issues}")

    recommendations = report["improvement_recommendations"]
    total_recommendations = sum(len(recs) for recs in recommendations.values())
    print(f"💡 Recomendaciones: {total_recommendations}")

    print(f"\n📄 Reporte completo guardado en: {report_path}")

    # Generar script de migración
    migration_path = "scripts/database_improvements.sql"
    with open(migration_path, "w", encoding="utf-8") as f:
        f.write(f"-- Database Improvements for QA Intelligence\n")
        f.write(f"-- Generated: {datetime.now().isoformat()}\n\n")
        f.write(report["migration_script"])

    print(f"🔧 Script de mejoras guardado en: {migration_path}")
    print("\n✅ Análisis completado!")


if __name__ == "__main__":
    main()
