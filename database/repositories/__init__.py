"""
QA Intelligence Repository Module
Implements SOLID principles and clean architecture patterns

This module provides:
- Repository pattern with proper abstraction
- Unit of Work for transaction management  
- Custom exceptions for error handling
- SOLID-compliant architecture
"""

# ========== Base Components ==========
from .base import BaseRepository
from .interfaces import IRepository, IUserRepository, IUnitOfWork
from .exceptions import (
    RepositoryError,
    EntityNotFoundError, 
    InvalidEntityError,
    DuplicateEntityError,
    ValidationError
)

# ========== Specific Repositories ==========
from .users import UserRepository
from .apps_repository import AppsRepository
from .countries_repository import CountriesRepository
from .mappings_repository import MappingsRepository

# ========== Transaction Management ==========
from .unit_of_work import UnitOfWork, UnitOfWorkFactory, create_unit_of_work_factory

# ========== Public API ==========
__all__ = [
    # Base Repository Components
    "BaseRepository",
    "IRepository", 
    "IUserRepository",
    "IUnitOfWork",
    
    # Exceptions
    "RepositoryError",
    "EntityNotFoundError",
    "InvalidEntityError", 
    "DuplicateEntityError",
    "ValidationError",
    
    # Specific Repositories
    "UserRepository",
    "AppsRepository",
    "CountriesRepository",
    "MappingsRepository",
    
    # Unit of Work Pattern
    "UnitOfWork",
    "UnitOfWorkFactory",
    "create_unit_of_work_factory",
]

# ========== Version Information ==========
__version__ = "1.0.0"
__author__ = "QA Intelligence Team"
__description__ = "SOLID-compliant repository pattern implementation"

# ========== Usage Documentation ==========
"""
Quick Start Guide:

1. **Basic Repository Usage:**
   ```python
   from database.repositories import create_unit_of_work_factory
   
   # Create factory
   factory = create_unit_of_work_factory("sqlite:///qa_intelligence.db")
   
   # Use with context manager (recommended)
   with factory.create_scope() as uow:
       user = uow.users.create_user({
           "username": "john_doe",
           "email": "john@example.com", 
           "password_hash": "hashed_password"
       })
       print(f"Created user: {user.username}")
   ```

2. **Manual Transaction Control:**
   ```python
   uow = factory.create()
   try:
       user1 = uow.users.create_user({"username": "user1", "email": "user1@example.com"})
       user2 = uow.users.create_user({"username": "user2", "email": "user2@example.com"})
       uow.commit()
   except Exception as e:
       uow.rollback()
       raise
   finally:
       uow.session.close()
   ```

3. **Repository-Specific Operations:**
   ```python
   with factory.create_scope() as uow:
       # User-specific queries
       active_users = uow.users.get_active_users()
       admin_users = uow.users.get_by_role(UserRole.ADMIN)
       
       # Search functionality
       users = uow.users.search_users("john")
       
       # Security operations
       user = uow.users.get_by_email("user@example.com")
       if user:
           uow.users.record_login_attempt(user.id, success=True)
   ```

4. **Error Handling:**
   ```python
   from database.repositories import EntityNotFoundError, InvalidEntityError
   
   try:
       with factory.create_scope() as uow:
           user = uow.users.get_by_email("nonexistent@example.com")
           if not user:
               raise EntityNotFoundError("User", "nonexistent@example.com")
   except EntityNotFoundError as e:
       print(f"User not found: {e}")
   except InvalidEntityError as e:
       print(f"Validation errors: {e.errors}")
   ```

5. **Advanced Features:**
   ```python
   with factory.create_scope() as uow:
       # Create savepoint for risky operations
       uow.save_point("before_bulk_update")
       
       try:
           # Bulk operations
           for user_data in bulk_user_data:
               uow.users.create_user(user_data)
       except Exception:
           # Rollback to savepoint only
           uow.rollback_to_save_point("before_bulk_update")
       else:
           # Release savepoint if successful
           uow.release_save_point("before_bulk_update")
   ```

Architecture Benefits:
- **Single Responsibility:** Each repository handles one entity type
- **Open/Closed:** Easy to extend with new repositories
- **Liskov Substitution:** All repositories implement same interface
- **Interface Segregation:** Specific interfaces for different needs
- **Dependency Inversion:** Depends on abstractions, not concretions

Performance Features:
- Connection pooling via SQLAlchemy engine
- Transaction management with automatic rollback
- Lazy loading of related entities
- Batch operations support
- Query optimization hooks

Testing Support:
- In-memory SQLite for unit tests
- Transaction rollback for test isolation  
- Mock-friendly interfaces
- Dependency injection ready
"""
