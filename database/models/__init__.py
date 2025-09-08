"""
QA Intelligence Database Models
SQLModel implementations with type safety and validation

SOLO MODELOS RAG ACTIVOS - Otros modelos comentados para evitar conflictos
"""

# === MODELOS RAG ÚNICAMENTE ===
from ..base import BaseModel
#     RAGDocument, RAGCollection, RAGEmbedding, RAGModel, RAGAnalytics,
#     DocumentType, EmbeddingStatus
# )
# 
# NOTA: RAG Manager usa modelos internos independientes para evitar dependencias circulares
# Para usar RAG, importar directamente: from database.repositories.rag_manager import RAGManagerFactory

# === MODELOS BÁSICOS NECESARIOS ===
from .users import User, AuditLog, UserRole

# === MODELOS COMENTADOS TEMPORALMENTE ===
# from .applications import Application, Country, Environment  
# from .testing import TestRun, PerformanceResult, TestType

# Database Query Tool Models - COMENTADOS para evitar conflictos
# from .apps import Apps
# from .countries import Countries
# from .app_environment_country_mappings import AppEnvironmentCountryMapping
# from .application_endpoints import ApplicationEndpoint

# Performance and SLA Models - COMENTADOS temporalmente
# from .performance_slas import PerformanceSLAs
# from .sla_violations import SlaViolations, ViolationType, ExecutionStatus, RiskLevel

# Export SOLO modelos RAG + User básico
__all__ = [
    # Usuarios y autenticación
    "User", "AuditLog", "UserRole",
    
    # RAG - usar RAGManagerFactory en lugar de modelos directos
    # "RAGDocument", "RAGCollection", "RAGEmbedding", "RAGModel", "RAGAnalytics",
    # "DocumentType", "EmbeddingStatus",
    
    # Base
    "BaseModel",
]

# Model registry para migrations - SOLO RAG
MODEL_REGISTRY = [
    "RAGDocument",
    "RAGCollection", 
    "RAGEmbedding",
    "RAGModel",
    "RAGAnalytics",
    "User",
    "AuditLog"
]
