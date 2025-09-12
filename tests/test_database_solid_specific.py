"""
Tests específicos para la implementación SOLID de la base de datos.
Verifica que todos los componentes SOLID funcionen correctamente.
"""

import pytest
import tempfile
import os
from datetime import datetime, timezone
from sqlmodel import create_engine, Session, SQLModel

from database.repositories import UserRepository
from database.repositories.unit_of_work import UnitOfWorkFactory
from database.repositories.exceptions import EntityNotFoundError, InvalidEntityError
from database.models.users import User, UserRole


class TestSOLIDDatabaseImplementation:
    """Test suite específico para validar implementación SOLID"""

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
        return UnitOfWorkFactory(engine)

    def test_database_schema_compatibility(self, uow_factory):
        """Verificar que el esquema de BD es compatible con SOLID"""
        with uow_factory.create_scope() as uow:
            # Test basic CRUD operations
            user_data = {
                "username": "test_solid_user",
                "email": "solid@test.com",
                "password_hash": "hashed_password",
                "full_name": "SOLID Test User",
                "is_active": True
            }
            
            # Create
            user = uow.users.create_user(user_data)
            assert user.id is not None
            assert user.username_norm == "test_solid_user"
            assert user.email_norm == "solid@test.com"
            
            # Read
            found_user = uow.users.get_by_id(user.id)
            assert found_user is not None
            assert found_user.username == user.username
            
            # Update
            found_user.full_name = "Updated Name"
            updated_user = uow.users.save(found_user, commit=False)
            assert updated_user.full_name == "Updated Name"
            
            # Delete
            uow.users.delete(updated_user)

    def test_unit_of_work_transaction_integrity(self, uow_factory):
        """Test que las transacciones del UoW mantienen integridad"""
        
        # Test successful transaction
        with uow_factory.create_scope() as uow:
            user_data = {
                "username": "transaction_test",
                "email": "transaction@test.com",
                "password_hash": "hash",
                "is_active": True
            }
            user = uow.users.create_user(user_data)
            assert user.id is not None
            
        # Verify user was committed
        with uow_factory.create_scope() as uow:
            found_user = uow.users.get_by_email("transaction@test.com")
            assert found_user is not None
            assert found_user.username == "transaction_test"
            
            # Clean up
            uow.users.delete(found_user)

    def test_repository_error_handling(self, uow_factory):
        """Test manejo de errores en repositorios"""
        
        with uow_factory.create_scope() as uow:
            # Test EntityNotFoundError
            with pytest.raises(EntityNotFoundError):
                uow.users.get_by_id_or_raise(99999)
            
            # Test validation errors
            invalid_user_data = {
                "username": "",  # Invalid
                "email": "invalid-email",  # Invalid
                "password_hash": "hash"
            }
            
            with pytest.raises(Exception):  # Should raise validation error
                uow.users.create_user(invalid_user_data)

    def test_solid_principles_compliance(self, uow_factory):
        """Verificar que la implementación cumple principios SOLID"""
        
        with uow_factory.create_scope() as uow:
            # Single Responsibility: UserRepository solo maneja usuarios
            assert hasattr(uow.users, 'create_user')
            assert hasattr(uow.users, 'get_by_email')
            assert hasattr(uow.users, 'get_by_username')
            
            # Open/Closed: Se pueden agregar nuevos repositories
            from database.repositories.base import BaseRepository
            
            class TestRepository(BaseRepository):
                def __init__(self, session):
                    super().__init__(session, User)
            
            test_repo = TestRepository(uow.session)
            assert test_repo is not None
            
            # Liskov Substitution: UserRepository es sustituible por BaseRepository
            base_repo: BaseRepository = uow.users
            assert base_repo.get_all() is not None
            
            # Interface Segregation: Repositories implementan interfaces específicas
            assert hasattr(uow.users, 'create_user')  # User-specific
            assert hasattr(uow.users, 'get_all')      # Generic
            
            # Dependency Inversion: UoW depende de abstracciones
            assert uow.users.__class__.__name__ == 'UserRepository'

    def test_audit_and_security_fields(self, uow_factory):
        """Test que los campos de auditoría y seguridad funcionan"""
        
        with uow_factory.create_scope() as uow:
            user_data = {
                "username": "audit_test",
                "email": "audit@test.com",  
                "password_hash": "hashed_password",
                "is_active": True,
                "created_by": 1,
                "updated_by": 1
            }
            
            user = uow.users.create_user(user_data)
            assert user.created_at is not None
            assert user.updated_at is not None
            assert user.created_by == 1
            assert user.updated_by == 1
            assert user.username_norm == "audit_test"
            assert user.email_norm == "audit@test.com"
            
            # Test security methods
            assert not user.is_locked()
            user.record_failed_login()
            assert user.failed_login_attempts == 1
            
            # Clean up
            uow.users.delete(user)

    def test_role_based_functionality(self, uow_factory):
        """Test funcionalidad basada en roles"""
        
        with uow_factory.create_scope() as uow:
            # Create users with different roles
            admin_data = {
                "username": "test_admin",
                "email": "admin@test.com",
                "password_hash": "hash",
                "role": UserRole.ADMIN,
                "is_active": True
            }
            
            viewer_data = {
                "username": "test_viewer", 
                "email": "viewer@test.com",
                "password_hash": "hash",
                "role": UserRole.VIEWER,
                "is_active": True
            }
            
            admin = uow.users.create_user(admin_data)
            viewer = uow.users.create_user(viewer_data)
            
            # Test role queries
            admins = uow.users.get_by_role(UserRole.ADMIN)
            assert len(admins) >= 1
            assert any(u.id == admin.id for u in admins)
            
            viewers = uow.users.get_by_role(UserRole.VIEWER)
            assert len(viewers) >= 1
            assert any(u.id == viewer.id for u in viewers)
            
            # Clean up (delete viewer first, then admin)
            uow.users.delete(viewer)  # Safe to delete viewer
            # Note: Can't delete admin if it's the last one (business rule)

    def test_performance_and_efficiency(self, uow_factory):
        """Test que la implementación es eficiente"""
        
        with uow_factory.create_scope() as uow:
            # Test bulk operations
            users_data = []
            for i in range(5):
                users_data.append({
                    "username": f"perf_user_{i}",
                    "email": f"perf_{i}@test.com",
                    "password_hash": "hash",
                    "is_active": True
                })
            
            # Create multiple users efficiently
            created_users = []
            for user_data in users_data:
                user = uow.users.create_user(user_data)
                created_users.append(user)
            
            assert len(created_users) == 5
            
            # Test efficient queries
            all_perf_users = uow.users.find_by(username__startswith="perf_user_")
            assert len(all_perf_users) >= 5
            
            # Clean up
            for user in created_users:
                uow.users.delete(user)
