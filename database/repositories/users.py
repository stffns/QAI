"""
User Repository implementation for QA Intelligence
Implements Single Responsibility Principle (SOLID)
Handles only user-related data operations
"""

from typing import Optional, Sequence, Dict, Any
from sqlmodel import Session, select, col
from sqlalchemy import func
from datetime import datetime, timedelta

from ..models.users import User, UserRole
from .base import BaseRepository
from .interfaces import IUserRepository
from .exceptions import EntityNotFoundError, InvalidEntityError

class UserRepository(BaseRepository[User], IUserRepository[User]):
    """
    User repository with user-specific business logic.
    Follows Single Responsibility Principle - only handles User entities.
    """
    
    def __init__(self, session: Session):
        """Initialize UserRepository with session"""
        super().__init__(session, User)
    
    # ========== IUserRepository Implementation ==========
    
    def get_by_email(self, email: str) -> Optional[User]:
        """Get user by email address"""
        return self.find_one_by(email=email)
    
    def get_by_username(self, username: str) -> Optional[User]:
        """Get user by username"""
        return self.find_one_by(username=username)
    
    def get_by_id_or_raise(self, user_id: int) -> User:
        """Get user by ID or raise EntityNotFoundError"""
        user = self.get_by_id(user_id)
        if not user:
            raise EntityNotFoundError("User", str(user_id))
        return user
    
    def get_active_users(self) -> Sequence[User]:
        """Get all active users"""
        return self.find_by(is_active=True)
    
    def exists_by_email(self, email: str) -> bool:
        """Check if user exists by email"""
        return self.exists_by(email=email)
    
    def exists_by_username(self, username: str) -> bool:
        """Check if user exists by username"""
        return self.exists_by(username=username)
    
    # ========== User-Specific Business Logic ==========
    
    def get_by_role(self, role: UserRole) -> Sequence[User]:
        """Get users by role"""
        return self.find_by(role=role)
    
    def get_verified_users(self) -> Sequence[User]:
        """Get all verified users"""
        return self.find_by(is_verified=True)
    
    def get_unverified_users(self) -> Sequence[User]:
        """Get all unverified users"""
        return self.find_by(is_verified=False)
    
    def get_locked_users(self) -> Sequence[User]:
        """Get currently locked users"""
        try:
            current_time = datetime.utcnow()
            statement = (
                select(User)
                .where(col(User.locked_until) != None)
                .where(col(User.locked_until) > current_time)
            )
            return list(self.session.exec(statement))
        except Exception as e:
            raise EntityNotFoundError("User", f"locked users: {str(e)}")
    
    def get_users_with_failed_attempts(self, min_attempts: int = 1) -> Sequence[User]:
        """Get users with failed login attempts"""
        try:
            statement = select(User).where(User.failed_login_attempts >= min_attempts)
            return list(self.session.exec(statement))
        except Exception as e:
            raise EntityNotFoundError("User", f"users with failed attempts: {str(e)}")
    
    # ========== User Security Operations ==========
    
    def create_user(self, user_data: Dict[str, Any]) -> User:
        """
        Create new user with validation.
        Single responsibility: user creation logic.
        """
        # Prepare data with normalized fields
        normalized_data = user_data.copy()
        
        # Ensure normalized fields are populated
        if 'username' in normalized_data and 'username_norm' not in normalized_data:
            normalized_data['username_norm'] = normalized_data['username'].lower().strip()
            
        if 'email' in normalized_data and 'email_norm' not in normalized_data:
            normalized_data['email_norm'] = normalized_data['email'].lower().strip()
        
        # Validate unique constraints before creating
        if 'email' in normalized_data and self.exists_by_email(normalized_data['email']):
            raise InvalidEntityError("User", [f"Email '{normalized_data['email']}' already exists"])
        
        if 'username' in normalized_data and self.exists_by_username(normalized_data['username']):
            raise InvalidEntityError("User", [f"Username '{normalized_data['username']}' already exists"])
        
        user = User(**normalized_data)
        # Don't commit in UoW context - let the UoW handle transactions
        return self.save(user, commit=False)
    
    def update_password(self, user_id: int, password_hash: str) -> User:
        """Update user password"""
        user = self.get_by_id(user_id)
        if not user:
            raise EntityNotFoundError("User", str(user_id))
        
        user.password_hash = password_hash
        return self.save(user)
    
    def verify_user(self, user_id: int) -> User:
        """Mark user as verified"""
        user = self.get_by_id(user_id)
        if not user:
            raise EntityNotFoundError("User", str(user_id))
        
        user.is_verified = True
        return self.save(user)
    
    def lock_user(self, user_id: int, duration_minutes: int = 30) -> User:
        """Lock user account for specified duration"""
        user = self.get_by_id(user_id)
        if not user:
            raise EntityNotFoundError("User", str(user_id))
        
        user.lock_account(duration_minutes)
        return self.save(user)
    
    def unlock_user(self, user_id: int) -> User:
        """Unlock user account"""
        user = self.get_by_id(user_id)
        if not user:
            raise EntityNotFoundError("User", str(user_id))
        
        user.unlock_account()
        return self.save(user)
    
    def record_login_attempt(self, user_id: int, success: bool, ip_address: Optional[str] = None) -> User:
        """Record login attempt (success or failure)"""
        user = self.get_by_id(user_id)
        if not user:
            raise EntityNotFoundError("User", str(user_id))
        
        if success:
            user.record_successful_login()
        else:
            user.record_failed_login()
        
        return self.save(user)
    
    # ========== User Analytics & Reports ==========
    
    def get_user_stats(self) -> Dict[str, Any]:
        """
        Get user statistics.
        Single responsibility: user analytics.
        """
        try:
            total_users = self.count()
            active_users = self.count(is_active=True)
            verified_users = self.count(is_verified=True)
            locked_users = len(self.get_locked_users())
            
            # Users by role
            role_stats = {}
            for role in UserRole:
                role_stats[role.value] = self.count(role=role)
            
            return {
                'total_users': total_users,
                'active_users': active_users,
                'verified_users': verified_users,
                'locked_users': locked_users,
                'role_distribution': role_stats,
                'verification_rate': (verified_users / total_users * 100) if total_users > 0 else 0
            }
        except Exception as e:
            raise InvalidEntityError("UserStats", [f"Failed to calculate stats: {str(e)}"])
    
    def search_users(self, query: str, limit: int = 10) -> Sequence[User]:
        """
        Search users by username, email, or full name.
        Single responsibility: user search functionality.
        """
        try:
            statement = (
                select(User)
                .where(
                    col(User.username).like(f"%{query}%") |
                    col(User.email).like(f"%{query}%") |
                    col(User.full_name).like(f"%{query}%")
                )
                .limit(limit)
            )
            return list(self.session.exec(statement))
        except Exception as e:
            raise EntityNotFoundError("User", f"search query '{query}': {str(e)}")
    
    # ========== Template Method Hooks (Override from BaseRepository) ==========
    
    def _validate_before_save(self, entity: User) -> None:
        """Validate user before saving"""
        errors = []
        
        # Validate email format (additional business rule)
        if hasattr(entity, 'email') and entity.email:
            import re
            email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
            if not re.match(email_pattern, entity.email):
                errors.append("Invalid email format")
        
        # Validate username format
        if hasattr(entity, 'username') and entity.username:
            import re
            username_pattern = r'^[a-zA-Z0-9_-]+$'
            if not re.match(username_pattern, entity.username):
                errors.append("Username can only contain letters, numbers, underscores, and hyphens")
        
        if errors:
            raise InvalidEntityError("User", errors)
    
    def _after_save(self, entity: User) -> None:
        """Actions after saving user"""
        # Here you could add audit logging, notifications, etc.
        # Following Single Responsibility, this would delegate to other services
        pass
    
    def _validate_before_delete(self, entity: User) -> None:
        """Validate before deleting user"""
        # Business rule: Cannot delete admin users if they're the last admin
        if entity.role == UserRole.ADMIN:
            admin_count = self.count(role=UserRole.ADMIN)
            if admin_count <= 1:
                raise InvalidEntityError("User", ["Cannot delete the last admin user"])
    
    def _after_delete(self, entity: User) -> None:
        """Actions after deleting user"""
        # Here you could add audit logging, cleanup tasks, etc.
        pass
