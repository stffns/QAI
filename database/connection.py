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
            
            # Aplicar PRAGMAs SQLite
            self._apply_sqlite_pragmas(engine)
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
    
    def _apply_sqlite_pragmas(self, engine: Engine):
        """Aplicar configuraciones SQLite"""
        if "sqlite" not in self.database_url:
            return
        
        with engine.connect() as connection:
            for pragma, value in DatabaseConfig.SQLITE_PRAGMAS.items():
                connection.execute(text(f"PRAGMA {pragma} = {value}"))
                connection.commit()
                
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
