"""
Repository Interfaces and Protocols for QA Intelligence
Implements Dependency Inversion Principle (SOLID)
"""

from abc import ABC, abstractmethod
from typing import Protocol, TypeVar, Generic, Optional, List, Dict, Any, Sequence
from sqlmodel import Session

T = TypeVar('T')

class IRepository(Protocol[T]):
    """
    Repository interface defining the contract for all repositories.
    Implements Interface Segregation Principle (SOLID)
    """
    
    def get_by_id(self, id: int) -> Optional[T]:
        """Get entity by ID"""
        ...
    
    def get_all(self, limit: Optional[int] = None, offset: int = 0) -> Sequence[T]:
        """Get all entities with pagination"""
        ...
    
    def save(self, entity: T) -> T:
        """Save entity (create or update)"""
        ...
    
    def delete(self, entity: T) -> bool:
        """Delete entity"""
        ...
    
    def delete_by_id(self, id: int) -> bool:
        """Delete entity by ID"""
        ...

class IUserRepository(IRepository[T], Protocol):
    """
    User-specific repository interface.
    Extends base repository with user-specific operations.
    Follows Interface Segregation Principle
    """
    
    def get_by_email(self, email: str) -> Optional[T]:
        """Get user by email"""
        ...
    
    def get_by_username(self, username: str) -> Optional[T]:
        """Get user by username"""
        ...
    
    def get_active_users(self) -> Sequence[T]:
        """Get all active users"""
        ...
    
    def exists_by_email(self, email: str) -> bool:
        """Check if user exists by email"""
        ...
    
    def exists_by_username(self, username: str) -> bool:
        """Check if user exists by username"""
        ...

class IUnitOfWork(Protocol):
    """
    Unit of Work pattern interface.
    Manages transactions and coordinates multiple repositories.
    """
    
    def begin(self) -> None:
        """Begin transaction"""
        ...
    
    def commit(self) -> None:
        """Commit transaction"""
        ...
    
    def rollback(self) -> None:
        """Rollback transaction"""
        ...
    
    def __enter__(self) -> 'IUnitOfWork':
        """Context manager entry"""
        ...
    
    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager exit"""
        ...
