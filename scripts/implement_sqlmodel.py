#!/usr/bin/env python3
"""
Script para implementar SQLModel + SQLAlchemy en QA Intelligence
Migra de SQL crudo a ORM profesional con type safety
"""

import os
import sys
from pathlib import Path
from typing import List, Dict
import subprocess
import json

class SQLModelImplementer:
    """Implementador de SQLModel para QA Intelligence"""
    
    def __init__(self, project_root: str):
        self.project_root = Path(project_root)
        self.database_dir = self.project_root / "database"
        
    def check_prerequisites(self) -> Dict[str, bool]:
        """Verificar prerequisitos para la implementación"""
        checks = {
            "project_exists": self.project_root.exists(),
            "config_exists": (self.project_root / "config").exists(),
            "pydantic_installed": False,
            "sqlite_db_exists": (self.project_root / "data" / "qa_intelligence.db").exists()
        }
        
        # Verificar si Pydantic está instalado
        try:
            import pydantic
            checks["pydantic_installed"] = True
        except ImportError:
            checks["pydantic_installed"] = False
        
        return checks
    
    def install_dependencies(self) -> bool:
        """Instalar dependencias necesarias"""
        dependencies = [
            "sqlmodel>=0.0.8",
            "alembic>=1.12.0", 
            "psycopg2-binary>=2.9.7",
            "python-dotenv>=1.0.0",
            "bcrypt>=4.0.1"
        ]
        
        print("📦 Instalando dependencias SQLModel...")
        
        try:
            for dep in dependencies:
                print(f"  Installing {dep}...")
                result = subprocess.run([
                    sys.executable, "-m", "pip", "install", dep
                ], capture_output=True, text=True, cwd=self.project_root)
                
                if result.returncode != 0:
                    print(f"  ❌ Error installing {dep}: {result.stderr}")
                    return False
                else:
                    print(f"  ✅ {dep} installed")
            
            return True
        except Exception as e:
            print(f"❌ Error installing dependencies: {e}")
            return False
    
    def create_directory_structure(self) -> bool:
        """Crear estructura de directorios para SQLModel"""
        directories = [
            "database",
            "database/models",
            "database/repositories", 
            "database/migrations",
            "database/utils"
        ]
        
        print("📁 Creando estructura de directorios...")
        
        try:
            for dir_path in directories:
                full_path = self.project_root / dir_path
                full_path.mkdir(parents=True, exist_ok=True)
                
                # Crear __init__.py en cada directorio Python
                if not dir_path.endswith("migrations"):
                    init_file = full_path / "__init__.py"
                    if not init_file.exists():
                        init_file.write_text("# SQLModel module\n")
                
                print(f"  ✅ {dir_path}/")
            
            return True
        except Exception as e:
            print(f"❌ Error creating directories: {e}")
            return False
    
    def create_base_files(self) -> bool:
        """Crear archivos base de SQLModel"""
        print("📝 Creando archivos base...")
        
        try:
            # 1. database/__init__.py
            self._create_database_init()
            
            # 2. database/base.py
            self._create_base_models()
            
            # 3. database/connection.py
            self._create_connection_manager()
            
            # 4. database/models/__init__.py
            self._create_models_init()
            
            print("  ✅ Archivos base creados")
            return True
        except Exception as e:
            print(f"❌ Error creating base files: {e}")
            return False
    
    def _create_database_init(self):
        """Crear database/__init__.py"""
        content = '''"""
QA Intelligence Database Module
SQLModel + SQLAlchemy implementation with type safety
"""

from .connection import DatabaseManager, get_db_session
from .base import BaseModel, TimestampMixin, AuditMixin

# Export main components
__all__ = [
    "DatabaseManager",
    "get_db_session",
    "BaseModel", 
    "TimestampMixin",
    "AuditMixin"
]
'''
        (self.database_dir / "__init__.py").write_text(content)
    
    def _create_base_models(self):
        """Crear database/base.py"""
        content = '''"""
Base models and mixins for QA Intelligence
Provides common functionality for all SQLModel models
"""

from sqlmodel import SQLModel, Field
from typing import Optional
from datetime import datetime
from pydantic import validator

class TimestampMixin(SQLModel):
    """Mixin para campos de auditoría temporal"""
    created_at: datetime = Field(default_factory=datetime.now, index=True)
    updated_at: Optional[datetime] = Field(default=None, index=True)

class AuditMixin(SQLModel):
    """Mixin para campos de auditoría de usuario"""
    created_by: Optional[int] = Field(default=None, foreign_key="users.id")
    updated_by: Optional[int] = Field(default=None, foreign_key="users.id")
    is_active: bool = Field(default=True, index=True)

class BaseModel(TimestampMixin, AuditMixin):
    """
    Modelo base con auditoría completa
    Incluye timestamps y campos de auditoría
    """
    __abstract__ = True
    
    @validator('updated_at', pre=True, always=True)
    def set_updated_at(cls, v):
        """Actualizar timestamp automáticamente"""
        return datetime.now()
    
    def dict_for_audit(self) -> dict:
        """Obtener diccionario para auditoría"""
        return {
            key: str(value) if value is not None else None
            for key, value in self.dict().items()
        }

# Model configuration
class DatabaseConfig:
    """Configuración global para modelos de base de datos"""
    
    # SQLite settings
    SQLITE_PRAGMAS = {
        "journal_mode": "WAL",
        "cache_size": -1 * 64000,  # 64MB
        "foreign_keys": 1,
        "ignore_check_constraints": 0,
        "synchronous": 1,  # NORMAL
    }
    
    # PostgreSQL settings (para migración futura)
    POSTGRES_POOL_SIZE = 20
    POSTGRES_MAX_OVERFLOW = 0
    POSTGRES_POOL_PRE_PING = True
'''
        (self.database_dir / "base.py").write_text(content)
    
    def _create_connection_manager(self):
        """Crear database/connection.py"""
        content = '''"""
Database connection management for QA Intelligence
Handles SQLite and PostgreSQL connections with pooling
"""

from sqlmodel import create_engine, Session, SQLModel
from sqlalchemy.engine import Engine
from sqlalchemy.pool import StaticPool
from contextlib import contextmanager
from typing import Generator, Optional
import os
from .base import DatabaseConfig

class DatabaseManager:
    """Manager centralizado para conexiones de base de datos"""
    
    def __init__(self, database_url: Optional[str] = None, echo: bool = False):
        self.database_url = database_url or self._get_database_url()
        self.echo = echo
        self.engine: Optional[Engine] = None
        self._setup_engine()
    
    def _get_database_url(self) -> str:
        """Obtener URL de base de datos desde configuración"""
        return os.getenv(
            "DATABASE_URL", 
            "sqlite:///./data/qa_intelligence.db"
        )
    
    def _setup_engine(self):
        """Configurar engine de SQLAlchemy"""
        connect_args = {}
        
        if "sqlite" in self.database_url:
            # Configuración SQLite
            connect_args = {
                "check_same_thread": False,
                "timeout": 30
            }
            
            self.engine = create_engine(
                self.database_url,
                connect_args=connect_args,
                poolclass=StaticPool,
                echo=self.echo
            )
            
            # Aplicar PRAGMAs SQLite
            self._apply_sqlite_pragmas()
            
        else:
            # Configuración PostgreSQL
            self.engine = create_engine(
                self.database_url,
                pool_size=DatabaseConfig.POSTGRES_POOL_SIZE,
                max_overflow=DatabaseConfig.POSTGRES_MAX_OVERFLOW,
                pool_pre_ping=DatabaseConfig.POSTGRES_POOL_PRE_PING,
                echo=self.echo
            )
    
    def _apply_sqlite_pragmas(self):
        """Aplicar configuraciones SQLite"""
        if "sqlite" not in self.database_url:
            return
        
        with self.engine.connect() as connection:
            for pragma, value in DatabaseConfig.SQLITE_PRAGMAS.items():
                connection.execute(f"PRAGMA {pragma} = {value}")
                
    def create_db_and_tables(self):
        """Crear todas las tablas definidas en los modelos"""
        SQLModel.metadata.create_all(self.engine)
    
    @contextmanager
    def get_session(self) -> Generator[Session, None, None]:
        """Context manager para sesiones de base de datos"""
        session = Session(self.engine)
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()
    
    def get_session_direct(self) -> Session:
        """
        Obtener sesión directa (para dependency injection)
        Nota: El caller debe cerrar la sesión manualmente
        """
        return Session(self.engine)
    
    def health_check(self) -> bool:
        """Verificar conectividad de la base de datos"""
        try:
            with self.get_session() as session:
                session.execute("SELECT 1")
                return True
        except Exception:
            return False

# Instancia global del manager
db_manager = DatabaseManager()

def get_db_session() -> Generator[Session, None, None]:
    """
    Dependency provider para FastAPI/inyección de dependencias
    """
    with db_manager.get_session() as session:
        yield session

def init_database():
    """Inicializar base de datos con tablas"""
    db_manager.create_db_and_tables()
    print("✅ Database initialized with SQLModel tables")

def test_connection():
    """Probar conexión a la base de datos"""
    if db_manager.health_check():
        print("✅ Database connection successful")
        return True
    else:
        print("❌ Database connection failed")
        return False
'''
        (self.database_dir / "connection.py").write_text(content)
    
    def _create_models_init(self):
        """Crear database/models/__init__.py"""
        content = '''"""
QA Intelligence Database Models
SQLModel implementations with type safety and validation
"""

# Import all models here for easy access
# from .users import User, AuditLog
# from .applications import Application, Country, Environment
# from .testing import TestRun, PerformanceResult, TestType
# from .rag import RAGDocument, VectorEmbedding

# Export models for external use
__all__ = [
    # "User", "AuditLog",
    # "Application", "Country", "Environment", 
    # "TestRun", "PerformanceResult", "TestType",
    # "RAGDocument", "VectorEmbedding"
]

# Model registry for migrations
MODEL_REGISTRY = [
    # User.__name__,
    # AuditLog.__name__,
    # Add all models here for Alembic
]
'''
        (self.database_dir / "models" / "__init__.py").write_text(content)
    
    def create_sample_user_model(self) -> bool:
        """Crear modelo de usuario como ejemplo"""
        print("👤 Creando modelo User de ejemplo...")
        
        try:
            content = '''"""
User models for QA Intelligence
Includes User, Role, and AuditLog models with security features
"""

from sqlmodel import SQLModel, Field, Relationship
from typing import Optional, List
from datetime import datetime
from enum import Enum
from ..base import BaseModel

class UserRole(str, Enum):
    """Roles de usuario en el sistema"""
    ADMIN = "admin"
    ANALYST = "analyst" 
    VIEWER = "viewer"
    OPERATOR = "operator"

class User(BaseModel, table=True):
    """
    Modelo de usuario con campos de seguridad
    Incluye validación, auditoría y relaciones
    """
    __tablename__ = "users"
    
    # Primary key
    id: Optional[int] = Field(primary_key=True)
    
    # Basic info
    username: str = Field(
        index=True, 
        min_length=3, 
        max_length=50, 
        unique=True,
        description="Unique username for login"
    )
    email: str = Field(
        unique=True, 
        max_length=255,
        regex=r'^[^@]+@[^@]+\\.[^@]+$',
        description="User email address"
    )
    password_hash: str = Field(
        min_length=60, 
        max_length=255,
        description="Bcrypt hashed password"
    )
    full_name: str = Field(
        min_length=1, 
        max_length=100,
        description="Full display name"
    )
    
    # Security fields (from database upgrade)
    is_verified: bool = Field(default=False, description="Email verified")
    is_locked: bool = Field(default=False, description="Account locked")
    failed_login_attempts: int = Field(
        default=0, 
        ge=0, 
        description="Failed login counter"
    )
    last_login_at: Optional[datetime] = Field(
        default=None,
        description="Last successful login"
    )
    last_login_attempt: Optional[datetime] = Field(
        default=None,
        description="Last login attempt (success or fail)"
    )
    password_changed_at: Optional[datetime] = Field(
        default=None,
        description="When password was last changed"
    )
    
    # API access
    api_key_hash: Optional[str] = Field(
        default=None,
        max_length=255,
        description="Hashed API key for programmatic access"
    )
    api_key_expires_at: Optional[datetime] = Field(
        default=None,
        description="API key expiration"
    )
    session_timeout_minutes: int = Field(
        default=480,  # 8 hours
        gt=0,
        description="Session timeout in minutes"
    )
    
    # Role
    role: UserRole = Field(
        default=UserRole.VIEWER,
        description="User role for permissions"
    )
    
    # Additional fields
    department: Optional[str] = Field(
        default=None,
        max_length=100,
        description="User department"
    )
    preferences: Optional[str] = Field(
        default=None,
        description="JSON string of user preferences"
    )
    
    # Relationships will be added when other models are created
    # test_runs: List["TestRun"] = Relationship(back_populates="triggered_by_user")
    # audit_logs: List["AuditLog"] = Relationship(back_populates="user")
    
    class Config:
        """Pydantic config"""
        use_enum_values = True
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }
    
    def is_api_key_valid(self) -> bool:
        """Check if API key is still valid"""
        if not self.api_key_expires_at:
            return True
        return datetime.now() < self.api_key_expires_at
    
    def should_reset_failed_attempts(self) -> bool:
        """Check if failed attempts should be reset"""
        if not self.last_login_attempt:
            return False
        
        # Reset after 1 hour
        reset_time = datetime.now() - timedelta(hours=1)
        return self.last_login_attempt < reset_time

class AuditLog(BaseModel, table=True):
    """
    Audit log for tracking all database operations
    Provides complete traceability for compliance
    """
    __tablename__ = "audit_logs"
    
    id: Optional[int] = Field(primary_key=True)
    
    # User context
    user_id: Optional[int] = Field(
        default=None,
        foreign_key="users.id", 
        index=True,
        description="User who performed the action"
    )
    
    # Action details
    table_name: str = Field(
        max_length=100, 
        index=True,
        description="Table that was modified"
    )
    record_id: Optional[str] = Field(
        default=None,
        max_length=255,
        description="ID of the modified record"
    )
    action_type: str = Field(
        max_length=20, 
        index=True,
        description="Type of action: INSERT, UPDATE, DELETE, SELECT"
    )
    
    # Change data
    old_values: Optional[str] = Field(
        default=None,
        description="JSON of old values (for updates/deletes)"
    )
    new_values: Optional[str] = Field(
        default=None,
        description="JSON of new values (for inserts/updates)"
    )
    
    # Session context
    ip_address: Optional[str] = Field(
        default=None,
        max_length=45,
        description="IP address of the client"
    )
    user_agent: Optional[str] = Field(
        default=None,
        description="Browser/client user agent"
    )
    session_id: Optional[str] = Field(
        default=None,
        max_length=255,
        description="Session identifier"
    )
    
    # Additional context
    business_reason: Optional[str] = Field(
        default=None,
        description="Business justification for the change"
    )
    
    # Relationship to user
    # user: Optional[User] = Relationship(back_populates="audit_logs")
'''
            
            user_model_path = self.database_dir / "models" / "users.py"
            user_model_path.write_text(content)
            
            print("  ✅ User model created")
            return True
        except Exception as e:
            print(f"❌ Error creating user model: {e}")
            return False
    
    def create_test_script(self) -> bool:
        """Crear script de prueba para SQLModel"""
        print("🧪 Creando script de prueba...")
        
        try:
            content = '''#!/usr/bin/env python3
"""
Test script for SQLModel implementation
Verifies that all components work correctly
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def test_imports():
    """Test that all SQLModel components import correctly"""
    print("🔍 Testing imports...")
    
    try:
        from database import DatabaseManager, get_db_session
        print("  ✅ Database manager imports")
        
        from database.base import BaseModel, TimestampMixin, AuditMixin
        print("  ✅ Base models import")
        
        from database.models.users import User, UserRole, AuditLog
        print("  ✅ User models import")
        
        return True
    except Exception as e:
        print(f"  ❌ Import error: {e}")
        return False

def test_database_connection():
    """Test database connection and health check"""
    print("🔗 Testing database connection...")
    
    try:
        from database.connection import db_manager, test_connection
        
        if test_connection():
            print("  ✅ Database connection successful")
            return True
        else:
            print("  ❌ Database connection failed")
            return False
    except Exception as e:
        print(f"  ❌ Connection error: {e}")
        return False

def test_model_creation():
    """Test creating a model instance"""
    print("👤 Testing model creation...")
    
    try:
        from database.models.users import User, UserRole
        from datetime import datetime
        
        # Create user instance (not saved to DB)
        user = User(
            username="test_user",
            email="test@example.com", 
            password_hash="$2b$12$dummy_hash_for_testing",
            full_name="Test User",
            role=UserRole.VIEWER
        )
        
        print(f"  ✅ User created: {user.username} ({user.email})")
        print(f"  ✅ Role: {user.role}")
        print(f"  ✅ Created at: {user.created_at}")
        
        return True
    except Exception as e:
        print(f"  ❌ Model creation error: {e}")
        return False

def test_validation():
    """Test Pydantic validation"""
    print("✅ Testing validation...")
    
    try:
        from database.models.users import User
        
        # Test invalid email
        try:
            user = User(
                username="test",
                email="invalid-email",  # Should fail
                password_hash="hash",
                full_name="Test"
            )
            print("  ❌ Validation should have failed for invalid email")
            return False
        except Exception:
            print("  ✅ Email validation working")
        
        # Test valid user
        user = User(
            username="valid_user",
            email="valid@example.com",
            password_hash="valid_hash",
            full_name="Valid User"
        )
        print("  ✅ Valid user created successfully")
        
        return True
    except Exception as e:
        print(f"  ❌ Validation error: {e}")
        return False

def main():
    """Run all tests"""
    print("🚀 SQLMODEL IMPLEMENTATION TEST")
    print("=" * 40)
    
    tests = [
        ("Imports", test_imports),
        ("Database Connection", test_database_connection),
        ("Model Creation", test_model_creation),
        ("Validation", test_validation)
    ]
    
    results = []
    for test_name, test_func in tests:
        print(f"\\n📋 {test_name}")
        result = test_func()
        results.append((test_name, result))
    
    print(f"\\n📊 TEST RESULTS")
    print("=" * 40)
    
    passed = 0
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{test_name}: {status}")
        if result:
            passed += 1
    
    print(f"\\nTotal: {passed}/{len(tests)} tests passed")
    
    if passed == len(tests):
        print("\\n🎉 All tests passed! SQLModel is ready to use.")
        return True
    else:
        print("\\n⚠️  Some tests failed. Check the implementation.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
'''
            
            test_script_path = self.project_root / "test_sqlmodel.py"
            test_script_path.write_text(content)
            
            print("  ✅ Test script created")
            return True
        except Exception as e:
            print(f"❌ Error creating test script: {e}")
            return False
    
    def generate_implementation_report(self) -> Dict:
        """Generar reporte de implementación"""
        return {
            "implementation_date": "2025-09-03",
            "components_created": [
                "database/ - Main module",
                "database/base.py - Base models and mixins",
                "database/connection.py - Database manager",
                "database/models/ - Model definitions",
                "database/models/users.py - User and audit models",
                "test_sqlmodel.py - Test suite"
            ],
            "next_steps": [
                "Run test script: python test_sqlmodel.py",
                "Create additional models (testing, applications)",
                "Implement repositories pattern",
                "Setup Alembic migrations",
                "Integrate with existing QA Agent"
            ],
            "dependencies_installed": [
                "sqlmodel>=0.0.8",
                "alembic>=1.12.0",
                "psycopg2-binary>=2.9.7",
                "python-dotenv>=1.0.0",
                "bcrypt>=4.0.1"
            ]
        }

def main():
    """Función principal"""
    project_root = "/Users/jaysonsteffens/Documents/QAI"
    
    print("🚀 IMPLEMENTANDO SQLMODEL EN QA INTELLIGENCE")
    print("=" * 50)
    
    implementer = SQLModelImplementer(project_root)
    
    # 1. Verificar prerequisites
    print("🔍 Verificando prerequisites...")
    checks = implementer.check_prerequisites()
    
    for check, result in checks.items():
        status = "✅" if result else "❌"
        print(f"  {status} {check}")
    
    if not all(checks.values()):
        print("❌ Prerequisites no cumplidos. Abortando.")
        return False
    
    # 2. Instalar dependencias
    if not implementer.install_dependencies():
        print("❌ Error instalando dependencias")
        return False
    
    # 3. Crear estructura
    if not implementer.create_directory_structure():
        print("❌ Error creando estructura")
        return False
    
    # 4. Crear archivos base
    if not implementer.create_base_files():
        print("❌ Error creando archivos base")
        return False
    
    # 5. Crear modelo ejemplo
    if not implementer.create_sample_user_model():
        print("❌ Error creando modelo User")
        return False
    
    # 6. Crear script de prueba
    if not implementer.create_test_script():
        print("❌ Error creando script de prueba")
        return False
    
    # 7. Generar reporte
    report = implementer.generate_implementation_report()
    
    print(f"\n🎉 IMPLEMENTACIÓN COMPLETADA!")
    print("=" * 50)
    print(f"📁 Componentes creados: {len(report['components_created'])}")
    print(f"📦 Dependencias: {len(report['dependencies_installed'])}")
    
    print(f"\n✅ PRÓXIMOS PASOS:")
    for i, step in enumerate(report['next_steps'], 1):
        print(f"  {i}. {step}")
    
    print(f"\n🧪 Para probar la implementación:")
    print(f"  cd {project_root}")
    print(f"  python test_sqlmodel.py")
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
