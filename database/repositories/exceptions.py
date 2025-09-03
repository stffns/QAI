"""
Repository-specific exceptions for QA Intelligence
Implements Single Responsibility Principle
"""

from typing import Optional, List

class RepositoryError(Exception):
    """Base repository exception"""
    
    def __init__(self, message: str, entity_type: Optional[str] = None, entity_id: Optional[str] = None):
        self.message = message
        self.entity_type = entity_type
        self.entity_id = entity_id
        super().__init__(self.message)

class EntityNotFoundError(RepositoryError):
    """Raised when entity is not found"""
    
    def __init__(self, entity_type: str, entity_id: str):
        message = f"{entity_type} with ID '{entity_id}' not found"
        super().__init__(message, entity_type, entity_id)

class DuplicateEntityError(RepositoryError):
    """Raised when entity already exists (unique constraint violation)"""
    
    def __init__(self, entity_type: str, field: str, value: str):
        message = f"{entity_type} with {field} '{value}' already exists"
        super().__init__(message, entity_type, value)
        self.field = field
        self.value = value

# Alias for backward compatibility
EntityAlreadyExistsError = DuplicateEntityError

class InvalidEntityError(RepositoryError):
    """Raised when entity fails validation"""
    
    def __init__(self, entity_type: str, validation_errors: List[str]):
        message = f"Invalid {entity_type}: {', '.join(validation_errors)}"
        super().__init__(message, entity_type)
        self.errors = validation_errors  # For consistency with other error classes
        self.validation_errors = validation_errors  # For backward compatibility

class ValidationError(RepositoryError):
    """Raised when business rule validation fails"""
    
    def __init__(self, rule: str, details: str):
        message = f"Business rule violation [{rule}]: {details}"
        super().__init__(message)
        self.rule = rule
        self.details = details

class DatabaseConnectionError(RepositoryError):
    """Raised when database connection fails"""
    
    def __init__(self, message: str = "Database connection failed"):
        super().__init__(message)

class TransactionError(RepositoryError):
    """Raised when transaction fails"""
    
    def __init__(self, operation: str, message: Optional[str] = None):
        if not message:
            message = f"Transaction failed during {operation}"
        super().__init__(message)
        self.operation = operation
