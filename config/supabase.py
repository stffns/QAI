"""
Supabase configuration for QA Intelligence
Handles PostgreSQL connection and Supabase-specific settings
"""

import os
from typing import Optional
from pydantic import BaseModel, field_validator
from pydantic_settings import BaseSettings


class SupabaseConfig(BaseSettings):
    """Configuración para Supabase PostgreSQL"""
    
    # Supabase connection details
    supabase_url: str = ""
    supabase_anon_key: str = ""
    supabase_service_role_key: str = ""
    
    # Database connection string
    database_url: str = ""
    
    # Connection pool settings (optimized for Supabase)
    pool_size: int = 10
    max_overflow: int = 20
    pool_pre_ping: bool = True
    pool_recycle: int = 3600  # 1 hour
    
    # SSL settings (required for Supabase)
    ssl_require: bool = True
    
    class Config:
        env_file = ".env.supabase"
        env_prefix = "SUPABASE_"
        case_sensitive = False
    
    @field_validator("database_url")
    @classmethod
    def validate_database_url(cls, v: str) -> str:
        if not v:
            raise ValueError("DATABASE_URL is required for Supabase connection")
        if not v.startswith("postgresql://"):
            raise ValueError("DATABASE_URL must start with postgresql://")
        return v
    
    @property
    def connection_kwargs(self) -> dict:
        """Get connection arguments for SQLAlchemy engine"""
        kwargs = {
            "pool_size": self.pool_size,
            "max_overflow": self.max_overflow,
            "pool_pre_ping": self.pool_pre_ping,
            "pool_recycle": self.pool_recycle,
            "echo": False,  # Set to True for SQL debugging
        }
        
        if self.ssl_require:
            kwargs["connect_args"] = {"sslmode": "require"}
            
        return kwargs


def get_supabase_config() -> SupabaseConfig:
    """Get Supabase configuration instance"""
    return SupabaseConfig()


def is_supabase_configured() -> bool:
    """Check if Supabase is properly configured"""
    try:
        config = get_supabase_config()
        return bool(config.database_url and config.supabase_url)
    except Exception:
        return False


def get_database_url() -> str:
    """Get database URL with fallback logic"""
    # Try Supabase first
    if is_supabase_configured():
        config = get_supabase_config()
        return config.database_url
    
    # Fallback to environment variable
    env_url = os.getenv("DATABASE_URL")
    if env_url:
        return env_url
    
    # Final fallback to SQLite (for development)
    return "sqlite:///./data/qa_intelligence.db"