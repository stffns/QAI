"""
Tests for SOLID Repository Pattern Implementation
Validates Single Responsibility, Open/Closed, Liskov Substitution, 
Interface Segregation, and Dependency Inversion principles
"""

import pytest
import tempfile
import os
from datetime import datetime, timedelta
from sqlmodel import create_engine, Session, SQLModel

# Import our repository components
from database.repositories import (
    create_unit_of_work_factory,
    UserRepository,
    EntityNotFoundError,
    InvalidEntityError,
    DuplicateEntityError
)
from database.models.users import User, UserRole


class TestSOLIDRepositoryPattern:
    """Test suite validating SOLID principles in repository implementation"""
    
    @pytest.fixture
    def temp_db_url(self):
        """Create temporary in-memory database for testing"""
        return "sqlite:///:memory:"
    
    @pytest.fixture
    def engine(self, temp_db_url):
        """Create database engine"""
        engine = create_engine(temp_db_url, echo=False)
        SQLModel.metadata.create_all(engine)
        return engine
    
    @pytest.fixture
    def uow_factory(self, engine):
        """Create UnitOfWork factory"""
        from database.repositories.unit_of_work import UnitOfWorkFactory
        return UnitOfWorkFactory(engine)
    
    @pytest.fixture
    def sample_user_data(self):
        """Sample user data for testing"""
        return {
            "username": "test_user",
            "email": "test@example.com",
            "password_hash": "hashed_password_123",
            "full_name": "Test User",
            "role": UserRole.VIEWER,
            "is_active": True,
            "is_verified": True
        }
    
    # ========== Single Responsibility Principle Tests ==========
    
    def test_user_repository_single_responsibility(self, uow_factory, sample_user_data):
        """Test that UserRepository only handles User entities (SRP)"""
        with uow_factory.create_scope() as uow:
            # UserRepository should only handle User operations
            user = uow.users.create_user(sample_user_data)
            
            # Verify it's focused on user operations only
            assert isinstance(user, User)
            assert user.username == sample_user_data["username"]
            assert user.email == sample_user_data["email"]
    
    def test_unit_of_work_single_responsibility(self, uow_factory):
        """Test that UnitOfWork only handles transaction management (SRP)"""
        with uow_factory.create_scope() as uow:
            # UoW should only manage transactions and provide repositories
            assert hasattr(uow, 'commit')
            assert hasattr(uow, 'rollback')
            assert hasattr(uow, 'users')
            
            # Should not have business logic methods
            assert not hasattr(uow, 'create_user')
            assert not hasattr(uow, 'validate_user')
    
    # ========== Open/Closed Principle Tests ==========
    
    def test_repository_extensibility(self, uow_factory):
        """Test that repositories are open for extension, closed for modification (OCP)"""
        # We can extend UserRepository without modifying base classes
        class ExtendedUserRepository(UserRepository):
            def get_premium_users(self):
                """Extended functionality without modifying base"""
                return self.find_by(role=UserRole.ADMIN)  # Example extension
        
        # Should work with existing UoW infrastructure
        with uow_factory.create_scope() as uow:
            # Can add new repository without changing UoW
            extended_repo = ExtendedUserRepository(uow.session)
            assert hasattr(extended_repo, 'get_premium_users')
            assert hasattr(extended_repo, 'create_user')  # Inherits base functionality
    
    # ========== Liskov Substitution Principle Tests ==========
    
    def test_repository_substitution(self, uow_factory, sample_user_data):
        """Test that derived repositories can substitute base repositories (LSP)"""
        class TestUserRepository(UserRepository):
            """Custom implementation that should be substitutable"""
            def create_user(self, user_data):
                # Custom logic but same interface
                user_data['full_name'] = user_data.get('full_name', 'Default Name')
                return super().create_user(user_data)
        
        with uow_factory.create_scope() as uow:
            # Should be able to substitute custom repository
            custom_repo = TestUserRepository(uow.session)
            user = custom_repo.create_user(sample_user_data)
            
            # Same interface, potentially different behavior
            assert isinstance(user, User)
            assert user.full_name == sample_user_data["full_name"]
    
    # ========== Interface Segregation Principle Tests ==========
    
    def test_interface_segregation(self, uow_factory):
        """Test that interfaces are segregated appropriately (ISP)"""
        with uow_factory.create_scope() as uow:
            # UserRepository implements IUserRepository with user-specific methods
            user_repo = uow.users
            
            # Should have user-specific interface methods
            assert hasattr(user_repo, 'get_by_email')
            assert hasattr(user_repo, 'get_by_username')
            assert hasattr(user_repo, 'get_active_users')
            
            # Should also have base repository methods
            assert hasattr(user_repo, 'get_by_id')
            assert hasattr(user_repo, 'save')
            assert hasattr(user_repo, 'delete')
    
    # ========== Dependency Inversion Principle Tests ==========
    
    def test_dependency_inversion(self, uow_factory):
        """Test that high-level modules don't depend on low-level modules (DIP)"""
        # UnitOfWork depends on IRepository abstraction, not concrete repositories
        with uow_factory.create_scope() as uow:
            # UoW works with repository interface
            user_repo = uow.users
            
            # Repository depends on Session abstraction
            assert hasattr(user_repo, 'session')
            
            # Can inject different session implementations
            assert isinstance(user_repo.session, Session)
    
    # ========== Functional Tests ==========
    
    def test_repository_crud_operations(self, uow_factory, sample_user_data):
        """Test basic CRUD operations work correctly"""
        with uow_factory.create_scope() as uow:
            # Create
            user = uow.users.create_user(sample_user_data)
            assert user.id is not None
            
            # Read
            found_user = uow.users.get_by_id(user.id)
            assert found_user is not None
            assert found_user.username == sample_user_data["username"]
            
            # Update
            found_user.full_name = "Updated Name"
            updated_user = uow.users.save(found_user)
            assert updated_user.full_name == "Updated Name"
            
            # Delete
            uow.users.delete(updated_user)
            deleted_user = uow.users.get_by_id(user.id)
            assert deleted_user is None
    
    def test_user_specific_operations(self, uow_factory, sample_user_data):
        """Test user-specific repository operations"""
        with uow_factory.create_scope() as uow:
            # Create test user
            user = uow.users.create_user(sample_user_data)
            
            # Test user-specific queries
            found_by_email = uow.users.get_by_email(sample_user_data["email"])
            assert found_by_email.id == user.id
            
            found_by_username = uow.users.get_by_username(sample_user_data["username"])
            assert found_by_username.id == user.id
            
            # Test role-based queries
            users_by_role = uow.users.get_by_role(UserRole.VIEWER)
            assert len(users_by_role) >= 1
            assert any(u.id == user.id for u in users_by_role)
    
    def test_transaction_rollback(self, uow_factory, sample_user_data):
        """Test transaction rollback functionality"""
        # Test automatic rollback on exception
        with pytest.raises(InvalidEntityError):
            with uow_factory.create_scope() as uow:
                # Create valid user
                user = uow.users.create_user(sample_user_data)
                
                # Try to create duplicate (should fail)
                uow.users.create_user(sample_user_data)  # Same email/username
        
        # Verify rollback - user should not exist
        with uow_factory.create_scope() as uow:
            users = uow.users.get_all()
            assert len(users) == 0  # Transaction was rolled back
    
    def test_error_handling(self, uow_factory, sample_user_data):
        """Test proper error handling"""
        with uow_factory.create_scope() as uow:
            # Test EntityNotFoundError
            with pytest.raises(EntityNotFoundError):
                uow.users.get_by_id_or_raise(99999)  # Non-existent ID
            
            # Test duplicate handling
            user = uow.users.create_user(sample_user_data)
            
            with pytest.raises(InvalidEntityError):
                # Should raise validation error for duplicate email
                uow.users.create_user(sample_user_data)
    
    def test_business_rules(self, uow_factory):
        """Test business rule enforcement"""
        with uow_factory.create_scope() as uow:
            # Create admin user
            admin_data = {
                "username": "admin",
                "email": "admin@example.com",
                "password_hash": "hashed_password",
                "role": UserRole.ADMIN,
                "is_active": True
            }
            admin = uow.users.create_user(admin_data)
            
            # Try to delete last admin (should fail)
            with pytest.raises(InvalidEntityError) as exc_info:
                uow.users.delete(admin)
            
            assert "Cannot delete the last admin user" in str(exc_info.value)
    
    def test_search_functionality(self, uow_factory):
        """Test search functionality"""
        with uow_factory.create_scope() as uow:
            # Create test users
            users_data = [
                {"username": "john_doe", "email": "john@example.com", "full_name": "John Doe"},
                {"username": "jane_smith", "email": "jane@example.com", "full_name": "Jane Smith"},
                {"username": "bob_jones", "email": "bob@example.com", "full_name": "Bob Jones"}
            ]
            
            for user_data in users_data:
                complete_user_data = {**user_data, "password_hash": "hash", "is_active": True}
                uow.users.create_user(complete_user_data)
            
            # Test search
            results = uow.users.search_users("john")
            assert len(results) >= 1
            assert any("john" in (r.username or "").lower() or "john" in (r.full_name or "").lower() for r in results)
    
    # ========== Performance and Integration Tests ==========
    
    def test_bulk_operations_performance(self, uow_factory):
        """Test bulk operations work efficiently"""
        with uow_factory.create_scope() as uow:
            # Create multiple users in single transaction
            users = []
            for i in range(10):
                user_data = {
                    "username": f"user_{i}",
                    "email": f"user_{i}@example.com",
                    "password_hash": "hash",
                    "is_active": True
                }
                user = uow.users.create_user(user_data)
                users.append(user)
            
            # Verify all created
            assert len(users) == 10
            
            # Test bulk query
            all_users = uow.users.get_all()
            assert len(all_users) >= 10
    
    def test_savepoint_functionality(self, uow_factory, sample_user_data):
        """Test savepoint functionality for nested transactions"""
        with uow_factory.create_scope() as uow:
            # Create first user
            user1 = uow.users.create_user(sample_user_data)
            
            # Create savepoint
            uow.save_point("test_savepoint")
            
            try:
                # Try to create invalid user
                invalid_data = sample_user_data.copy()
                invalid_data["email"] = "invalid-email"  # Invalid format
                uow.users.create_user(invalid_data)
            except InvalidEntityError:
                # Rollback to savepoint
                uow.rollback_to_save_point("test_savepoint")
            
            # First user should still exist
            found_user = uow.users.get_by_id(user1.id)
            assert found_user is not None


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v", "--tb=short"])
