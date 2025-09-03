"""
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
