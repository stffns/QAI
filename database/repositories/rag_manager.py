"""
🚀 RAG Manager SOLID - SQLModel Implementation  
===============================================
Sistema RAG usando SQLModel con validaciones Pydantic
Migrado para usar database.models.rag para consistencia arquitectónica

✅ SOLID Principles:
- Single Responsibility: Solo maneja operaciones RAG
- Open/Closed: Extensible via interfaces
- Liskov Substitution: Implementación intercambiable
- Interface Segregation: Métodos específicos
- Dependency Inversion: Factory pattern

Autor: QA Intelligence Team  
Fecha: 8 de Septiembre de 2025
"""

from sqlalchemy import create_engine
from sqlmodel import SQLModel, Session, select, desc, and_, or_, func
from typing import List, Dict, Optional, Any, Union
from datetime import datetime
import json
import hashlib
from pathlib import Path

# Importar modelos SQLModel del proyecto
from database.models.rag import RAGDocument, RAGCollection, DocumentType

class RAGManager:
    """
    🚀 RAG Manager SOLID con SQLModel
    =================================
    
    Gestor centralizado para operaciones RAG usando SQLModel
    con validaciones Pydantic y consistencia arquitectónica.
    
    ✅ Características:
    - SOLID compliance total
    - SQLModel + Pydantic validations
    - Operaciones RAG completas
    - Consistencia arquitectónica
    """
    
    def __init__(self, db_path: Union[str, Path]):
        """Inicializar RAG Manager con SQLModel"""
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Crear engine para SQLModel
        self.engine = create_engine(
            f"sqlite:///{self.db_path}",
            connect_args={"check_same_thread": False},
            echo=False
        )
        
        # Crear tablas usando SQLModel
        SQLModel.metadata.create_all(self.engine)
        
        print(f"✅ RAG Manager inicializado: {self.db_path}")
    
    def _get_session(self) -> Session:
        """Crear nueva sesión SQLModel"""
        return Session(self.engine)
    
    # ==========================================
    # 📄 OPERACIONES DE DOCUMENTOS RAG
    # ==========================================
    
    def create_document(
        self,
        document_type: DocumentType,
        title: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
        source_system: str = "qa_intelligence",
        language: str = "es"
    ) -> int:
        """
        ✨ Crear nuevo documento RAG usando SQLModel
        
        Args:
            document_type: Tipo de documento según enum
            title: Título del documento  
            content: Contenido completo
            metadata: Metadatos adicionales
            source_system: Sistema origen
            language: Idioma del documento
            
        Returns:
            ID del documento creado
        """
        try:
            with self._get_session() as session:
                # Generar hash para el documento
                import hashlib
                document_hash = hashlib.md5(content.encode()).hexdigest()
                
                # Crear documento usando SQLModel con validaciones automáticas
                document = RAGDocument(
                    document_type=document_type,
                    title=title,
                    content=content,
                    source_system=source_system,
                    language=language,
                    document_hash=document_hash
                )
                
                # Usar helper del modelo para metadata
                if metadata:
                    document.set_metadata(metadata)
                
                session.add(document)
                session.commit()
                session.refresh(document)
                
                print(f"✅ Documento RAG creado: ID {document.id}")
                return document.id or 0
                
        except Exception as e:
            print(f"❌ Error creando documento RAG: {e}")
            raise
    
    def search_documents(
        self,
        query: Optional[str] = None,
        document_type: Optional[DocumentType] = None,
        limit: int = 10,
        source_system: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        🔍 Buscar documentos RAG con filtros
        
        Args:
            query: Texto a buscar en título/contenido
            document_type: Filtrar por tipo de documento
            limit: Límite de resultados
            source_system: Filtrar por sistema origen
            
        Returns:
            Lista de documentos encontrados
        """
        try:
            with self._get_session() as session:
                stmt = select(RAGDocument)
                
                # Aplicar filtros activos
                stmt = stmt.where(RAGDocument.is_active == True)
                
                if query:
                    from sqlmodel import col
                    stmt = stmt.where(
                        or_(
                            col(RAGDocument.title).like(f'%{query}%'),
                            col(RAGDocument.content).like(f'%{query}%')
                        )
                    )
                
                if document_type:
                    stmt = stmt.where(RAGDocument.document_type == document_type.value)
                
                if source_system:
                    stmt = stmt.where(RAGDocument.source_system == source_system)
                
                # Ordenar por fecha de creación
                stmt = stmt.order_by(desc(RAGDocument.created_at)).limit(limit)
                
                results = session.exec(stmt).all()
                
                documents = []
                for doc in results:
                    documents.append({
                        "id": doc.id,
                        "document_type": doc.document_type,
                        "title": doc.title,
                        "content": doc.content,
                        "source_system": doc.source_system,
                        "metadata": json.loads(doc.metadata_json) if doc.metadata_json else {},
                        "document_hash": doc.document_hash,
                        "language": doc.language,
                        "created_at": doc.created_at.isoformat() if doc.created_at else None,
                        "updated_at": doc.updated_at.isoformat() if doc.updated_at else None
                    })
                
                print(f"🔍 Encontrados {len(documents)} documentos RAG")
                return documents
                
        except Exception as e:
            print(f"❌ Error buscando documentos RAG: {e}")
            return []
    
    def get_document_by_id(self, document_id: int) -> Optional[Dict[str, Any]]:
        """
        📄 Obtener documento RAG por ID
        
        Args:
            document_id: ID del documento
            
        Returns:
            Documento encontrado o None
        """
        try:
            with self._get_session() as session:
                stmt = select(RAGDocument).where(
                    and_(
                        RAGDocument.id == document_id,
                        RAGDocument.is_active == True
                    )
                )
                result = session.exec(stmt).first()
                
                if result:
                    doc = result
                    return {
                        "id": doc.id,
                        "document_type": doc.document_type,
                        "title": doc.title,
                        "content": doc.content,
                        "source_system": doc.source_system,
                        "metadata": doc.parsed_metadata,  # Usar computed field
                        "document_hash": doc.document_hash,
                        "language": doc.language,
                        "created_at": doc.created_at.isoformat() if doc.created_at else None,
                        "updated_at": doc.updated_at.isoformat() if doc.updated_at else None
                    }
                    
                print(f"📄 Documento RAG encontrado: ID {document_id}")
                return None
                
        except Exception as e:
            print(f"❌ Error obteniendo documento RAG {document_id}: {e}")
            return None
    
    def update_document(
        self,
        document_id: int,
        title: Optional[str] = None,
        content: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        📝 Actualizar documento RAG existente
        
        Args:
            document_id: ID del documento
            title: Nuevo título (opcional)
            content: Nuevo contenido (opcional)
            metadata: Nuevos metadatos (opcional)
            
        Returns:
            True si se actualizó correctamente
        """
        try:
            with self._get_session() as session:
                stmt = select(RAGDocument).where(
                    and_(
                        RAGDocument.id == document_id,
                        RAGDocument.is_active == True
                    )
                )
                result = session.exec(stmt).first()
                
                if result:
                    document = result
                    
                    if title:
                        document.title = title
                    if content:
                        document.content = content
                        # Re-generar hash cuando cambia el contenido
                        import hashlib
                        document.document_hash = hashlib.md5(content.encode()).hexdigest()
                    if metadata:
                        document.set_metadata(metadata)  # Usar helper del modelo
                    
                    from datetime import datetime
                    document.updated_at = datetime.utcnow()
                    
                    session.add(document)
                    session.commit()
                    print(f"📝 Documento RAG actualizado: ID {document_id}")
                    return True
                    
                print(f"❌ Documento RAG no encontrado: ID {document_id}")
                return False
                
        except Exception as e:
            print(f"❌ Error actualizando documento RAG {document_id}: {e}")
            return False
    
    def delete_document(self, document_id: int, soft_delete: bool = True) -> bool:
        """
        🗑️ Eliminar documento RAG (soft delete por defecto)
        
        Args:
            document_id: ID del documento
            soft_delete: Si True, marca como inactivo; si False, elimina físicamente
            
        Returns:
            True si se eliminó correctamente
        """
        try:
            with self._get_session() as session:
                stmt = select(RAGDocument).where(RAGDocument.id == document_id)
                result = session.exec(stmt).first()
                
                if result:
                    document = result
                    
                    if soft_delete:
                        document.is_active = False
                        from datetime import datetime
                        document.updated_at = datetime.utcnow()
                        session.add(document)
                        session.commit()
                        print(f"🗑️ Documento RAG desactivado: ID {document_id}")
                    else:
                        session.delete(document)
                        session.commit()
                        print(f"🗑️ Documento RAG eliminado permanentemente: ID {document_id}")
                    
                    return True
                    
                print(f"❌ Documento RAG no encontrado: ID {document_id}")
                return False
                
        except Exception as e:
            print(f"❌ Error eliminando documento RAG {document_id}: {e}")
            return False
    
    
    # ==========================================
    # � OPERACIONES DE COLECCIONES RAG
    # ==========================================
    
    def create_collection(
        self,
        name: str,
        description: Optional[str] = None,
        embedding_model: str = "default",
        metadata: Optional[Dict[str, Any]] = None
    ) -> int:
        """
        ✨ Crear nueva colección RAG
        
        Args:
            name: Nombre único de la colección
            description: Descripción de la colección
            embedding_model: Modelo de embedding a usar
            metadata: Metadatos adicionales
            
        Returns:
            ID de la colección creada
        """
        try:
            with self._get_session() as session:
                collection = RAGCollection(
                    name=name,
                    description=description,
                    embedding_model=embedding_model
                )
                
                # Usar helper del modelo para metadata si existe
                if metadata and hasattr(collection, 'set_metadata'):
                    collection.set_metadata(metadata)
                elif metadata:
                    import json
                    collection.metadata_json = json.dumps(metadata)
                
                session.add(collection)
                session.commit()
                session.refresh(collection)
                
                print(f"✅ Colección RAG creada: ID {collection.id}")
                return collection.id or 0  # Manejar el caso Optional[int]
                
        except Exception as e:
            print(f"❌ Error creando colección RAG: {e}")
            raise
    
    def get_collections(self, active_only: bool = True) -> List[Dict[str, Any]]:
        """
        � Obtener lista de colecciones RAG
        
        Args:
            active_only: Si True, solo colecciones activas
            
        Returns:
            Lista de colecciones
        """
        try:
            with self._get_session() as session:
                stmt = select(RAGCollection)
                
                if active_only:
                    stmt = stmt.where(RAGCollection.is_active == True)
                
                stmt = stmt.order_by(desc(RAGCollection.created_at))
                results = session.exec(stmt).all()
                
                collections = []
                for col in results:
                    collections.append({
                        "id": col.id,
                        "name": col.name,
                        "description": col.description,
                        "embedding_model": col.embedding_model,
                        "metadata": col.parsed_metadata if hasattr(col, 'parsed_metadata') else {},
                        "is_active": col.is_active,
                        "created_at": col.created_at.isoformat() if col.created_at else None,
                        "updated_at": col.updated_at.isoformat() if col.updated_at else None
                    })
                
                print(f"📂 Encontradas {len(collections)} colecciones RAG")
                return collections
                
        except Exception as e:
            print(f"❌ Error obteniendo colecciones RAG: {e}")
            return []
    
    # ==========================================
    # � OPERACIONES DE ESTADÍSTICAS
    # ==========================================
    
    def get_stats(self) -> Dict[str, Any]:
        """
        📊 Obtener estadísticas del sistema RAG
        
        Returns:
            Diccionario con estadísticas
        """
        try:
            with self._get_session() as session:
                # Contar documentos totales usando SQLModel
                from sqlmodel import func
                total_docs_result = session.exec(
                    select(func.count()).select_from(RAGDocument).where(RAGDocument.is_active == True)
                ).first()
                total_docs = total_docs_result or 0
                
                # Contar por tipo de documento
                type_stats = {}
                for doc_type in DocumentType:
                    count_result = session.exec(
                        select(func.count()).select_from(RAGDocument).where(
                            and_(
                                RAGDocument.document_type == doc_type.value,
                                RAGDocument.is_active == True
                            )
                        )
                    ).first()
                    type_stats[doc_type.value] = count_result or 0
                
                # Contar colecciones
                total_collections_result = session.exec(
                    select(func.count()).select_from(RAGCollection).where(RAGCollection.is_active == True)
                ).first()
                total_collections = total_collections_result or 0
                
                from datetime import datetime
                stats = {
                    "total_documents": total_docs,
                    "total_collections": total_collections,
                    "documents_by_type": type_stats,
                    "database_path": str(self.db_path),
                    "last_updated": datetime.utcnow().isoformat()
                }
                
                print(f"📊 Estadísticas RAG: {total_docs} docs, {total_collections} collections")
                return stats
                
        except Exception as e:
            print(f"❌ Error obteniendo estadísticas RAG: {e}")
            return {}

# ==========================================
# 🏭 FACTORY FUNCTION (Compatibilidad)
# ==========================================

def create_rag_manager(db_path: str = "data/qa_intelligence_rag_v3.db") -> RAGManager:
    """
    🏭 Factory para crear RAGManager con dependency injection
    Permite fácil substitución e intercambio de implementaciones
    Compatible con el patrón original del proyecto
    """
    return RAGManager(db_path=db_path)


# ==========================================
# 🧪 FUNCIONES DE TESTING
# ==========================================

if __name__ == "__main__":
    print("🧪 Ejecutando tests básicos de RAG Manager...")
    
    # Test de creación
    manager = create_rag_manager()
    
    # Test de creación de documento
    doc_id = manager.create_document(
        document_type=DocumentType.TEST_SCENARIO,
        title="Test de escenario básico",
        content="Este es un contenido de prueba para validar el sistema RAG.",
        metadata={"test": True, "version": "1.0"}
    )
    
    # Test de búsqueda
    docs = manager.search_documents(query="prueba")
    print(f"� Documentos encontrados: {len(docs)}")
    
    # Test de estadísticas
    stats = manager.get_stats()
    print(f"📊 Stats: {stats}")
    
    print("✅ Tests básicos completados!")
