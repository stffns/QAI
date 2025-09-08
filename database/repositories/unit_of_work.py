"""
Unit of Work implementation for QA Intelligence
Implements Dependency Inversion Principle (SOLID)
Manages transactions and coordinates multiple repositories
"""

from typing import Optional, Type, TypeVar, Any, Dict, cast
from contextlib import contextmanager
from sqlmodel import Session, create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text

from .interfaces import IUnitOfWork, IRepository
from .users import UserRepository
from .app_environment_country_mappings_repository import AppEnvironmentCountryMappingRepository
from .exceptions import RepositoryError

# Generic type for repositories
T = TypeVar('T', bound=IRepository)

class UnitOfWork(IUnitOfWork):
    """
    Unit of Work implementation that manages database sessions and transactions.
    Follows Dependency Inversion Principle - depends on abstractions (IRepository).
    """
    
    def __init__(self, session: Session):
        """Initialize UnitOfWork with a database session"""
        self._session = session
        self._repositories: Dict[str, IRepository] = {}
        self._is_committed = False
        self._is_rolled_back = False
    
    @property
    def session(self) -> Session:
        """Get the database session"""
        return self._session
    
    # ========== Repository Management ==========
    
    @property
    def users(self) -> UserRepository:
        """Get or create UserRepository"""
        if 'users' not in self._repositories:
            self._repositories['users'] = UserRepository(self._session)
        return cast(UserRepository, self._repositories['users'])
    
    @property
    def app_environment_country_mappings(self) -> AppEnvironmentCountryMappingRepository:
        """Get or create AppEnvironmentCountryMapping repository"""
        if 'app_environment_country_mappings' not in self._repositories:
            self._repositories['app_environment_country_mappings'] = AppEnvironmentCountryMappingRepository(self._session)
        return cast(AppEnvironmentCountryMappingRepository, self._repositories['app_environment_country_mappings'])
    
    def get_repository(self, repository_class: Type[T]) -> T:
        """
        Get repository instance by class.
        Implements Dependency Inversion - depends on abstractions.
        """
        repo_name = repository_class.__name__.lower()
        
        if repo_name not in self._repositories:
            # Create new repository instance
            try:
                self._repositories[repo_name] = repository_class(self._session)  # type: ignore
            except TypeError:
                raise RepositoryError(f"Repository class {repository_class.__name__} must accept session parameter")
        
        return cast(T, self._repositories[repo_name])
    
    def add_repository(self, name: str, repository: IRepository) -> None:
        """Add custom repository to unit of work"""
        self._repositories[name] = repository
    
    # ========== Transaction Management ==========
    
    def commit(self) -> None:
        """Commit the current transaction"""
        try:
            if not self._is_committed and not self._is_rolled_back:
                self._session.commit()
                self._is_committed = True
        except Exception as e:
            self.rollback()
            raise RepositoryError(f"Failed to commit transaction: {str(e)}")
    
    def rollback(self) -> None:
        """Rollback the current transaction"""
        try:
            if not self._is_rolled_back:
                self._session.rollback()
                self._is_rolled_back = True
        except Exception as e:
            raise RepositoryError(f"Failed to rollback transaction: {str(e)}")
    
    def flush(self) -> None:
        """Flush pending changes to database without committing"""
        try:
            self._session.flush()
        except Exception as e:
            raise RepositoryError(f"Failed to flush session: {str(e)}")
    
    def refresh(self, entity: Any) -> None:
        """Refresh entity from database"""
        try:
            self._session.refresh(entity)
        except Exception as e:
            raise RepositoryError(f"Failed to refresh entity: {str(e)}")
    
    # ========== Context Manager Support ==========
    
    def __enter__(self):
        """Enter context manager"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit context manager with automatic rollback on exception"""
        if exc_type is not None:
            # Exception occurred, rollback
            self.rollback()
        else:
            # No exception, commit
            self.commit()
        
        # Close session
        self._session.close()
    
    # ========== Advanced Transaction Operations ==========
    
    def begin(self) -> None:
        """Begin a new transaction (implemented from IUnitOfWork)"""
        try:
            # Session already has transaction started by default
            pass
        except Exception as e:
            raise RepositoryError(f"Failed to begin transaction: {str(e)}")
    
    def save_point(self, name: str) -> None:
        """Create a savepoint for nested transactions"""
        try:
            self._session.execute(text(f"SAVEPOINT {name}"))
        except Exception as e:
            raise RepositoryError(f"Failed to create savepoint '{name}': {str(e)}")
    
    def rollback_to_save_point(self, name: str) -> None:
        """Rollback to a specific savepoint"""
        try:
            self._session.execute(text(f"ROLLBACK TO SAVEPOINT {name}"))
        except Exception as e:
            raise RepositoryError(f"Failed to rollback to savepoint '{name}': {str(e)}")
    
    def release_save_point(self, name: str) -> None:
        """Release a savepoint"""
        try:
            self._session.execute(text(f"RELEASE SAVEPOINT {name}"))
        except Exception as e:
            raise RepositoryError(f"Failed to release savepoint '{name}': {str(e)}")


class UnitOfWorkFactory:
    """
    Factory for creating UnitOfWork instances.
    Implements Dependency Inversion Principle - abstracts session creation.
    """
    
    def __init__(self, engine: Engine):
        """Initialize factory with database engine"""
        self.engine = engine
        self.session_factory = sessionmaker(bind=engine, class_=Session)
    
    def create(self) -> UnitOfWork:
        """Create new UnitOfWork instance with fresh session"""
        session = self.session_factory()
        return UnitOfWork(session)
    
    @contextmanager
    def create_scope(self):
        """
        Create UnitOfWork within a context manager scope.
        Automatically handles commit/rollback and session cleanup.
        """
        uow = self.create()
        try:
            yield uow
        except Exception:
            uow.rollback()
            raise
        else:
            uow.commit()
        finally:
            uow.session.close()


# ========== Convenience Functions ==========

def create_unit_of_work_factory(database_url: str) -> UnitOfWorkFactory:
    """
    Create UnitOfWorkFactory from database URL.
    Factory function for easy setup.
    """
    engine = create_engine(database_url)
    return UnitOfWorkFactory(engine)


# ========== Usage Examples in Comments ==========

"""
Example Usage:

1. Basic Usage with Context Manager:
    ```python
    factory = create_unit_of_work_factory("sqlite:///qa_intelligence.db")
    
    with factory.create_scope() as uow:
        # Create user
        user_data = {"username": "john", "email": "john@example.com"}
        user = uow.users.create_user(user_data)
        
        # Operations are automatically committed
        # Rollback happens automatically on exceptions
    ```

2. Manual Transaction Control:
    ```python
    factory = create_unit_of_work_factory("sqlite:///qa_intelligence.db")
    uow = factory.create()
    
    try:
        # Create multiple users
        user1 = uow.users.create_user({"username": "user1", "email": "user1@example.com"})
        user2 = uow.users.create_user({"username": "user2", "email": "user2@example.com"})
        
        # Commit all changes together
        uow.commit()
    except Exception as e:
        uow.rollback()
        raise
    finally:
        uow.session.close()
    ```

3. Savepoints for Complex Operations:
    ```python
    with factory.create_scope() as uow:
        # Create first user
        user1 = uow.users.create_user({"username": "user1", "email": "user1@example.com"})
        
        # Create savepoint before risky operation
        uow.save_point("before_user2")
        
        try:
            # Risky operation that might fail
            user2 = uow.users.create_user({"username": "invalid", "email": "invalid"})
        except Exception:
            # Rollback only to savepoint, keep user1
            uow.rollback_to_save_point("before_user2")
        else:
            # Release savepoint if successful
            uow.release_save_point("before_user2")
    ```

4. Multiple Repository Coordination:
    ```python
    with factory.create_scope() as uow:
        # Use multiple repositories in same transaction
        user = uow.users.create_user({"username": "john", "email": "john@example.com"})
        
        # When we add more repositories:
        # project = uow.projects.create_project({"name": "Test Project", "owner_id": user.id})
        # test_run = uow.test_runs.create_test_run({"project_id": project.id})
        
        # All operations committed together
    ```
"""
