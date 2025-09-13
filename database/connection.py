"""
Database connection management for QA Intelligence
Handles SQLite and PostgreSQL connections with pooling
"""

from sqlmodel import create_engine, Session, SQLModel
from sqlalchemy.engine import Engine
from sqlalchemy.pool import StaticPool, NullPool
from sqlalchemy import text
from contextlib import contextmanager
from typing import Generator, Optional
import os
from .base import DatabaseConfig

class DatabaseManager:
    """Manager centralizado para conexiones de base de datos"""
    
    def __init__(self, database_url: Optional[str] = None, echo: bool = False):
        self.database_url = database_url or self._get_database_url()
        self.echo = echo
        self.engine: Engine = self._setup_engine()
    
    def _get_database_url(self) -> str:
        """Obtener URL de base de datos desde configuración"""
        return os.getenv(
            "DATABASE_URL", 
            "sqlite:///./data/qa_intelligence.db"
        )
    
    def _setup_engine(self) -> Engine:
        """Configurar engine de SQLAlchemy"""
        connect_args = {}
        
        if "sqlite" in self.database_url:
            # Configuración SQLite
            connect_args = {
                "check_same_thread": False,
                "timeout": 30
            }
            
            engine = create_engine(
                self.database_url,
                connect_args=connect_args,
                poolclass=NullPool,  # NullPool es más apropiado para SQLite que StaticPool
                echo=self.echo
            )
            
            # Aplicar PRAGMAs SQLite en cada conexión
            self._setup_sqlite_event_listeners(engine)
            return engine
            
        else:
            # Configuración PostgreSQL
            return create_engine(
                self.database_url,
                pool_size=DatabaseConfig.POSTGRES_POOL_SIZE,
                max_overflow=DatabaseConfig.POSTGRES_MAX_OVERFLOW,
                pool_pre_ping=DatabaseConfig.POSTGRES_POOL_PRE_PING,
                echo=self.echo
            )
    
    def _setup_sqlite_event_listeners(self, engine: Engine):
        """Configurar event listeners para aplicar PRAGMAs en cada conexión SQLite"""
        if "sqlite" not in self.database_url:
            return
            
        from sqlalchemy import event
        
        @event.listens_for(engine, "connect")
        def set_sqlite_pragma(dbapi_connection, connection_record):
            """Aplicar PRAGMAs en cada nueva conexión SQLite"""
            cursor = dbapi_connection.cursor()
            # Define a whitelist of allowed PRAGMA names and (optionally) allowed values
            ALLOWED_PRAGMAS = {
                "journal_mode": {"wal", "delete", "truncate", "persist", "memory", "off"},
                "synchronous": {"off", "normal", "full", "extra", 0, 1, 2, 3},
                "foreign_keys": {0, 1, "on", "off", "true", "false"},
                "cache_size": None,  # None means any integer is allowed
                "temp_store": {0, 1, 2, "default", "file", "memory"},
                # Add more PRAGMAs as needed
            }
            for pragma, value in DatabaseConfig.SQLITE_PRAGMAS.items():
                if pragma not in ALLOWED_PRAGMAS:
                    continue  # or raise ValueError(f"Disallowed PRAGMA: {pragma}")
                allowed_values = ALLOWED_PRAGMAS[pragma]
                if allowed_values is not None:
                    if value not in allowed_values:
                        continue  # or raise ValueError(f"Disallowed value for PRAGMA {pragma}: {value}")
                # If allowed_values is None, allow any integer value (for e.g. cache_size)
                cursor.execute(f"PRAGMA {pragma} = {value}")
            cursor.close()
                
    def create_db_and_tables(self):
        """Crear todas las tablas definidas en los modelos"""
        # Importar modelos críticos para registrar tablas antes de create_all
        try:
            from database.models.performance_endpoint_results import PerformanceEndpointResults  # noqa: F401
        except Exception:
            pass
        try:
            from database.models.performance_test_executions import PerformanceTestExecution  # noqa: F401
        except Exception:
            pass
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
                session.execute(text("SELECT 1"))
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
