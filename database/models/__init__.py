"""
QA Intelligence Database Models
SQLModel implementations with type safety and validation
"""

# Import all models here for easy access
from .users import User, AuditLog, UserRole
# from .applications import Application, Country, Environment
# from .testing import TestRun, PerformanceResult, TestType
# from .rag import RAGDocument, VectorEmbedding

# Export models for external use
__all__ = [
    "User", "AuditLog", "UserRole",
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
