"""
Base Repository implementation for QA Intelligence
Implements DRY principle and Template Method pattern
Optimized for SQLModel (SQLAlchemy + Pydantic v2)
"""

from __future__ import annotations

from abc import ABC
from typing import Any, Generic, Optional, Sequence, Type, TypeVar

from sqlmodel import SQLModel, Session, select
from sqlalchemy import and_, func, asc, desc
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from .interfaces import IRepository
from .exceptions import (
    EntityNotFoundError,
    EntityAlreadyExistsError,
    InvalidEntityError,          # (reservada para validaciones en hooks)
    DatabaseConnectionError,
)

T = TypeVar("T", bound=SQLModel)


class BaseRepository(Generic[T], IRepository[T], ABC):
    """
    Repositorio base genérico para modelos SQLModel.

    Características:
    - CRUD común con manejo de transacciones/errores
    - Filtros expresivos (None, IN, operadores: gte/lte/gt/lt/ne/like/ilike)
    - count() con scalar_one()
    - exists_by() eficiente (sin cargar entidades)
    - save() con commit/refresh opcional (unit of work)
    - get_all() con order_by/descending
    - paginate() retorna (items, total)
    - Hooks de Template Method para validación/transformación
    """

    def __init__(self, session: Session, model_class: Type[T]):
        self._session = session
        self._model_class = model_class
        self._entity_name = model_class.__name__

    # ---------- Accesores ----------
    @property
    def session(self) -> Session:
        return self._session

    @property
    def model_class(self) -> Type[T]:
        return self._model_class

    # ---------- CRUD ----------
    def get_by_id(self, id: Any) -> Optional[T]:
        try:
            return self._session.get(self._model_class, id)
        except SQLAlchemyError as e:
            raise DatabaseConnectionError(
                f"Failed to get {self._entity_name} by ID: {e}"
            )

    def get_all(
        self,
        limit: Optional[int] = None,
        offset: int = 0,
        order_by: Optional[str] = None,
        descending: bool = False,
    ) -> Sequence[T]:
        try:
            stmt = select(self._model_class)
            if order_by and hasattr(self._model_class, order_by):
                col = getattr(self._model_class, order_by)
                stmt = stmt.order_by(desc(col) if descending else asc(col))
            if offset:
                stmt = stmt.offset(offset)
            if limit is not None:
                stmt = stmt.limit(limit)
            return self._session.exec(stmt).all()
        except SQLAlchemyError as e:
            raise DatabaseConnectionError(
                f"Failed to get {self._entity_name} list: {e}"
            )

    def save(self, entity: T, *, commit: bool = True, refresh: bool = True) -> T:
        """
        Crea o actualiza una entidad.

        Args:
            entity: instancia SQLModel
            commit: si True, hace commit; si False, deja en la UoW
            refresh: si True, refresca desde DB (recupera defaults, triggers, etc.)
        """
        try:
            self._validate_before_save(entity)
            entity = self._transform_before_save(entity)

            self._session.add(entity)
            self._session.flush()  # asegura PKs y defaults del server

            if commit:
                self._session.commit()
            if refresh:
                self._session.refresh(entity)

            self._after_save(entity)
            return entity

        except IntegrityError as e:
            self._session.rollback()
            # Puedes granularizar según códigos de error del dialecto (ej. PG)
            raise EntityAlreadyExistsError(
                self._entity_name, "integrity_error", str(e.orig)
            )
        except SQLAlchemyError as e:
            self._session.rollback()
            raise DatabaseConnectionError(f"Failed to save {self._entity_name}: {e}")

    def delete(self, entity: T) -> bool:
        try:
            self._validate_before_delete(entity)
            self._session.delete(entity)
            self._session.commit()
            self._after_delete(entity)
            return True
        except IntegrityError as e:
            self._session.rollback()
            # Opcional: crear EntityInUseError si necesitas distinguir FK
            raise DatabaseConnectionError(
                f"FK constraint on delete {self._entity_name}: {e.orig}"
            )
        except SQLAlchemyError as e:
            self._session.rollback()
            raise DatabaseConnectionError(
                f"Failed to delete {self._entity_name}: {e}"
            )

    def delete_by_id(self, id: Any) -> bool:
        entity = self.get_by_id(id)
        if not entity:
            # Más estricto/consistente
            raise EntityNotFoundError(self._entity_name, id)
        return self.delete(entity)

    # ---------- Helpers de consultas ----------
    def _build_filters(self, **filters):
        """
        Construye condiciones WHERE a partir de un dict de filtros.
        Soporta:
          - None -> IS NULL
          - list/tuple/set -> IN (...)
          - dict con operadores: gte/lte/gt/lt/ne/like/ilike
          - valor simple -> ==
        Ignora campos inexistentes en el modelo.
        """
        conditions = []
        for field, value in filters.items():
            if not hasattr(self._model_class, field):
                continue
            col = getattr(self._model_class, field)

            if value is None:
                conditions.append(col.is_(None))
            elif isinstance(value, (list, tuple, set)):
                conditions.append(col.in_(list(value)))
            elif isinstance(value, dict):
                for op, v in value.items():
                    if op == "gte":
                        conditions.append(col >= v)
                    elif op == "lte":
                        conditions.append(col <= v)
                    elif op == "gt":
                        conditions.append(col > v)
                    elif op == "lt":
                        conditions.append(col < v)
                    elif op == "ne":
                        conditions.append(col != v)
                    elif op == "like":
                        conditions.append(col.like(v))
                    elif op == "ilike":
                        # Nota: ILIKE solo en algunos dialectos (ej. PostgreSQL)
                        conditions.append(col.ilike(v))
            else:
                conditions.append(col == value)
        return conditions

    def _build_select_query(self, **filters):
        stmt = select(self._model_class)
        conditions = self._build_filters(**filters)
        if conditions:
            stmt = stmt.where(and_(*conditions))
        return stmt

    # ---------- Búsquedas ----------
    def find_by(self, **filters) -> Sequence[T]:
        try:
            stmt = self._build_select_query(**filters)
            return self._session.exec(stmt).all()
        except SQLAlchemyError as e:
            raise DatabaseConnectionError(
                f"Failed to find {self._entity_name}: {e}"
            )

    def find_one_by(self, **filters) -> Optional[T]:
        try:
            stmt = self._build_select_query(**filters)
            return self._session.exec(stmt).first()
        except SQLAlchemyError as e:
            raise DatabaseConnectionError(
                f"Failed to find {self._entity_name}: {e}"
            )

    def exists_by(self, **filters) -> bool:
        try:
            # select(1) + limit(1) evita traer entidades completas
            stmt = self._build_select_query(**filters).with_only_columns(1).limit(1)
            return self._session.exec(stmt).first() is not None
        except SQLAlchemyError as e:
            raise DatabaseConnectionError(
                f"Failed to check existence of {self._entity_name}: {e}"
            )

    def count(self, **filters) -> int:
        try:
            subq = self._build_select_query(**filters).subquery()
            cnt_stmt = select(func.count()).select_from(subq)
            result = self._session.exec(cnt_stmt)
            return int(result.one())
        except SQLAlchemyError as e:
            raise DatabaseConnectionError(
                f"Failed to count {self._entity_name}: {e}"
            )

    # ---------- Paginación ----------
    def paginate(
        self,
        *,
        page: int = 1,
        per_page: int = 20,
        order_by: Optional[str] = None,
        descending: bool = False,
        **filters,
    ) -> tuple[list[T], int]:
        """
        Devuelve (items, total).
        - page: 1-based
        - per_page: tamaño de página
        - order_by: nombre de columna opcional
        """
        page = max(page, 1)
        offset = (page - 1) * per_page
        try:
            stmt = self._build_select_query(**filters)
            if order_by and hasattr(self._model_class, order_by):
                col = getattr(self._model_class, order_by)
                stmt = stmt.order_by(desc(col) if descending else asc(col))
            items = self._session.exec(
                stmt.offset(offset).limit(per_page)
            ).all()
            total = self.count(**filters)
            return items, total
        except SQLAlchemyError as e:
            raise DatabaseConnectionError(
                f"Failed to paginate {self._entity_name}: {e}"
            )

    # ---------- Hooks (Template Method) ----------
    def _validate_before_save(self, entity: T) -> None:
        """Validaciones previas al guardado (override en subclases)."""
        # Ej.: if not entity.name: raise InvalidEntityError(...)
        return None

    def _transform_before_save(self, entity: T) -> T:
        """Transformaciones previas (override en subclases)."""
        return entity

    def _after_save(self, entity: T) -> None:
        """Acciones posteriores al guardado (override en subclases)."""
        return None

    def _validate_before_delete(self, entity: T) -> None:
        """Validaciones previas a eliminar (override en subclases)."""
        return None

    def _after_delete(self, entity: T) -> None:
        """Acciones posteriores a eliminar (override en subclases)."""
        return None