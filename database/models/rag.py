"""
RAG Models for QA Intelligence
SQLModel implementations for RAG documents and collections
Following project SOLID principles with type safety and validation
"""

from __future__ import annotations

from typing import Optional, Dict, Any
from enum import Enum
import json
import hashlib

from sqlmodel import SQLModel, Field, Column, Text
from pydantic import field_validator, computed_field

from ..base import BaseModel, register_timestamp_listeners


class DocumentType(str, Enum):
    """Tipos de documentos RAG"""
    TEST_SCENARIO = "test_scenario"
    API_SUCCESS_PATTERN = "api_success_pattern"
    API_ERROR_PATTERN = "api_error_pattern"
    PERFORMANCE_INSIGHT = "performance_insight"
    AUDIT_PATTERN = "audit_pattern"
    QA_GUIDELINES = "qa_guidelines"
    PERFORMANCE_REPORT = "performance_report"
    TEST_REPORT = "test"


class EmbeddingStatus(str, Enum):
    """Estados de embeddings RAG"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class RAGDocument(BaseModel, table=True):
    """
    Modelo principal para documentos RAG
    Incluye metadatos, validación y gestión de estado
    """
    __tablename__ = "rag_documents"

    # Primary key
    id: Optional[int] = Field(default=None, primary_key=True)

    # Document classification
    document_type: DocumentType = Field(
        index=True,
        description="Tipo de documento para categorización"
    )
    
    source_system: str = Field(
        default="qa_intelligence",
        max_length=100,
        description="Sistema fuente del documento"
    )

    # Content fields
    title: str = Field(
        max_length=500,
        description="Título descriptivo del documento"
    )
    
    content: str = Field(
        sa_column=Column(Text),
        description="Contenido completo del documento"
    )

    # Metadata and hash
    metadata_json: Optional[str] = Field(
        default=None,
        sa_column=Column(Text),
        description="Metadatos adicionales en JSON"
    )
    
    document_hash: str = Field(
        index=True,
        max_length=100,
        description="Hash para detectar duplicados"
    )

    # Document properties
    language: str = Field(
        default="es",
        max_length=10,
        description="Idioma del documento"
    )

    @computed_field
    @property
    def parsed_metadata(self) -> Dict[str, Any]:
        """Parsear metadata JSON automáticamente"""
        if self.metadata_json:
            try:
                return json.loads(self.metadata_json)
            except (json.JSONDecodeError, TypeError):
                return {}
        return {}

    @field_validator('content')
    @classmethod
    def validate_content_length(cls, v):
        """Validar longitud mínima del contenido"""
        if len(v.strip()) < 10:
            raise ValueError("Content must be at least 10 characters long")
        return v.strip()

    @field_validator('title')
    @classmethod
    def validate_title(cls, v):
        """Validar y limpiar título"""
        cleaned = v.strip()
        if len(cleaned) < 3:
            raise ValueError("Title must be at least 3 characters long")
        return cleaned

    @field_validator('document_hash', mode='before')
    @classmethod
    def auto_generate_hash(cls, v, info):
        """Auto-generar hash si no se proporciona"""
        if v is None and 'content' in info.data:
            content = info.data.get('content', '')
            return hashlib.md5(content.encode()).hexdigest()
        return v

    def set_metadata(self, metadata: Dict[str, Any]) -> None:
        """Helper para establecer metadata"""
        self.metadata_json = json.dumps(metadata, ensure_ascii=False)

    def get_source_id(self) -> Optional[str]:
        """Obtener source_id desde metadata"""
        return self.parsed_metadata.get('source_id')


class RAGCollection(BaseModel, table=True):
    """
    Colecciones para organizar documentos RAG
    """
    __tablename__ = "rag_collections"

    # Primary key
    id: Optional[int] = Field(default=None, primary_key=True)

    # Collection info
    name: str = Field(
        max_length=200,
        description="Nombre único de la colección",
        sa_column_kwargs={"unique": True}
    )
    
    description: Optional[str] = Field(
        default=None,
        sa_column=Column(Text),
        description="Descripción de la colección"
    )

    # Configuration
    embedding_model: str = Field(
        default="default",
        max_length=100,
        description="Modelo de embeddings utilizado"
    )
    
    vector_dimension: int = Field(
        default=1536,
        description="Dimensión de los vectores de embedding"
    )

    # Metadata
    metadata_json: Optional[str] = Field(
        default=None,
        sa_column=Column(Text),
        description="Metadatos adicionales en JSON"
    )

    @computed_field
    @property
    def parsed_metadata(self) -> Dict[str, Any]:
        """Parsear metadata JSON automáticamente"""
        if self.metadata_json:
            try:
                return json.loads(self.metadata_json)
            except (json.JSONDecodeError, TypeError):
                return {}
        return {}

    @field_validator('name')
    @classmethod
    def validate_name(cls, v):
        """Validar y limpiar nombre"""
        cleaned = v.strip()
        if len(cleaned) < 2:
            raise ValueError("Collection name must be at least 2 characters long")
        return cleaned

    def set_metadata(self, metadata: Dict[str, Any]) -> None:
        """Helper para establecer metadata"""
        self.metadata_json = json.dumps(metadata, ensure_ascii=False)


class RAGEmbedding(BaseModel, table=True):
    """
    Modelo para embeddings de documentos RAG
    """
    __tablename__ = "rag_embeddings"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    document_id: int = Field(foreign_key="rag_documents.id", index=True)
    embedding_vector: str = Field(description="Vector de embedding serializado")
    model_name: str = Field(max_length=100, default="default")
    status: EmbeddingStatus = Field(default=EmbeddingStatus.PENDING)
    metadata_json: Optional[str] = Field(default=None, sa_column=Column(Text))
    
    @computed_field
    @property
    def metadata_dict(self) -> Dict[str, Any]:
        """Parsear metadata JSON"""
        if self.metadata_json:
            try:
                return json.loads(self.metadata_json)
            except json.JSONDecodeError:
                return {}
        return {}


class RAGModel(BaseModel, table=True):
    """
    Modelo para configuración de modelos RAG
    """
    __tablename__ = "rag_models"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(max_length=100, unique=True)
    model_type: str = Field(max_length=50)  # "embedding", "generative", etc.
    configuration: str = Field(sa_column=Column(Text))
    is_active: bool = Field(default=True, index=True)
    metadata_json: Optional[str] = Field(default=None, sa_column=Column(Text))


class RAGAnalytics(BaseModel, table=True):
    """
    Modelo para analytics y métricas RAG
    """
    __tablename__ = "rag_analytics"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    document_id: Optional[int] = Field(default=None, foreign_key="rag_documents.id")
    collection_id: Optional[int] = Field(default=None, foreign_key="rag_collections.id")
    metric_name: str = Field(max_length=100)
    metric_value: float
    metadata_json: Optional[str] = Field(default=None, sa_column=Column(Text))


# Registrar listeners de timestamp
register_timestamp_listeners(RAGDocument)
register_timestamp_listeners(RAGCollection)
register_timestamp_listeners(RAGEmbedding)
register_timestamp_listeners(RAGModel)
register_timestamp_listeners(RAGAnalytics)


# Exportar para uso fácil
__all__ = [
    "DocumentType",
    "RAGDocument", 
    "RAGCollection"
]
