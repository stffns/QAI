"""
Security Manager for WebSocket connections

Implements comprehensive security measures following QA Intelligence patterns:
- JWT-based authentication with configurable algorithms
- Rate limiting with sliding window implementation  
- IP-based access control and blocking
- Security event logging with Loguru integration
- Pydantic v2 configuration validation

Architecture:
- Single Responsibility: Handles only security concerns
- Dependency Inversion: Configurable via SecurityConfig abstraction
- Open/Closed: Extensible security policies via inheritance
"""

import asyncio
import time
import hashlib
import secrets
import os
from datetime import datetime, timedelta, timezone
from typing import Dict, Optional, Set, Any, List
from collections import defaultdict, deque

import jwt
from pydantic import ValidationError

try:
    from src.logging_config import get_logger, LogExecutionTime, LogStep
    from config.models import SecurityConfig
except ImportError:
    import sys
    import os
    sys.path.append(os.path.join(os.path.dirname(__file__), "..", ".."))
    from src.logging_config import get_logger, LogExecutionTime, LogStep
    from config.models import SecurityConfig


class SecurityError(Exception):
    """Base exception for security-related errors"""
    pass


class AuthenticationError(SecurityError):
    """Authentication failed"""
    pass


class AuthorizationError(SecurityError):
    """Authorization failed"""
    pass


class RateLimitError(SecurityError):
    """Rate limit exceeded"""
    pass


class SecurityManager:
    """
    Comprehensive security manager for WebSocket connections.
    
    Features:
    - JWT token validation with configurable algorithms
    - Sliding window rate limiting per user/IP
    - IP blocking and access control
    - Security audit logging
    - Performance optimized with async operations
    
    Following SOLID principles:
    - Single Responsibility: Only handles security concerns
    - Open/Closed: Extensible via inheritance
    - Dependency Inversion: Configured via SecurityConfig
    """
    
    def __init__(self, config: SecurityConfig):
        self.config = config
        self.logger = get_logger("SecurityManager")
        
        # JWT configuration
        self.jwt_secret = self._get_jwt_secret()
        self.jwt_algorithm = config.authentication.algorithm
        
        # Rate limiting state
        self.rate_limit_windows: Dict[str, deque] = defaultdict(deque)
        self.rate_limit_cleanup_last = time.time()
        
        # Blocked IPs and users
        self.blocked_ips: Set[str] = set()
        self.blocked_users: Set[str] = set()
        
        # Authentication cache
        self.auth_cache: Dict[str, Dict[str, Any]] = {}
        self.cache_expiry: Dict[str, float] = {}
        
        # Security metrics
        self.metrics = {
            'auth_attempts': 0,
            'auth_successes': 0,
            'auth_failures': 0,
            'rate_limit_hits': 0,
            'blocked_attempts': 0
        }
        
        self.logger.info("Security manager initialized")
    
    async def initialize(self) -> None:
        """Initialize security manager and background tasks"""
        try:
            with LogExecutionTime("Security manager initialization", "SecurityManager"):
                
                # Start cleanup tasks
                if self.config.rate_limiting.enabled:
                    asyncio.create_task(self._cleanup_rate_limits())
                
                # Load any persistent security data
                await self._load_security_state()
                
                self.logger.info("Security manager fully initialized")
                
        except Exception as e:
            self.logger.error(f"Failed to initialize security manager: {e}")
            raise SecurityError(f"Security manager initialization failed: {e}")
    
    async def cleanup(self) -> None:
        """Clean up security manager resources"""
        try:
            # Save security state if needed
            await self._save_security_state()
            
            # Clear caches
            self.auth_cache.clear()
            self.cache_expiry.clear()
            self.rate_limit_windows.clear()
            
            self.logger.info("Security manager cleaned up")
            
        except Exception as e:
            self.logger.error(f"Error during security cleanup: {e}")
    
    async def authenticate_token(self, token: Optional[str]) -> Optional[str]:
        """
        Authenticate JWT token and return user ID.
        
        Args:
            token: JWT token string
            
        Returns:
            str: User ID if valid, None if invalid
            
        Raises:
            AuthenticationError: If authentication fails
        """
        if not self.config.authentication.enabled:
            return "anonymous_user"
        
        if not token:
            raise AuthenticationError("No authentication token provided")
        
        self.metrics['auth_attempts'] += 1
        
        try:
            with LogStep("JWT token validation", "SecurityManager"):
                
                # Check cache first
                if token in self.auth_cache and self.cache_expiry.get(token, 0) > time.time():
                    self.logger.debug("Using cached authentication")
                    self.metrics['auth_successes'] += 1
                    return self.auth_cache[token]['user_id']
                
                # Decode and validate JWT
                payload = jwt.decode(
                    token,
                    self.jwt_secret,
                    algorithms=[self.jwt_algorithm],
                    issuer=self.config.authentication.issuer,
                    audience=self.config.authentication.audience
                )
                
                user_id = payload.get('user_id') or payload.get('sub')
                if not user_id:
                    raise AuthenticationError("No user ID in token")
                
                # Check if user is blocked
                if user_id in self.blocked_users:
                    self.metrics['blocked_attempts'] += 1
                    raise AuthenticationError(f"User {user_id} is blocked")
                
                # Cache the result
                self.auth_cache[token] = {
                    'user_id': user_id,
                    'payload': payload
                }
                self.cache_expiry[token] = time.time() + 300  # 5 minute cache
                
                self.metrics['auth_successes'] += 1
                self.logger.info(f"User {user_id} authenticated successfully")
                
                return user_id
                
        except jwt.ExpiredSignatureError:
            self.metrics['auth_failures'] += 1
            raise AuthenticationError("Token has expired")
            
        except jwt.InvalidTokenError as e:
            self.metrics['auth_failures'] += 1
            raise AuthenticationError(f"Invalid token: {e}")
            
        except Exception as e:
            self.metrics['auth_failures'] += 1
            self.logger.error(f"Authentication error: {e}")
            raise AuthenticationError(f"Authentication failed: {e}")
    
    async def check_rate_limit(self, identifier: str) -> bool:
        """
        Check if identifier (user_id or IP) is within rate limits.
        
        Args:
            identifier: User ID or IP address to check
            
        Returns:
            bool: True if within limits, False if exceeded
        """
        if not self.config.rate_limiting.enabled:
            return True
        
        current_time = time.time()
        window_start = current_time - self.config.rate_limiting.window_size
        
        # Get or create request window for this identifier
        requests = self.rate_limit_windows[identifier]
        
        # Remove old requests outside the window
        while requests and requests[0] < window_start:
            requests.popleft()
        
        # Check if within limits
        if len(requests) >= self.config.rate_limiting.max_requests_per_minute:
            self.metrics['rate_limit_hits'] += 1
            self.logger.warning(f"Rate limit exceeded for {identifier}")
            return False
        
        # Add current request
        requests.append(current_time)
        
        # Cleanup old windows periodically
        if current_time - self.rate_limit_cleanup_last > self.config.rate_limiting.cleanup_interval:
            await self._cleanup_old_rate_limit_windows()
            self.rate_limit_cleanup_last = current_time
        
        return True
    
    async def check_ip_access(self, ip_address: str) -> bool:
        """
        Check if IP address is allowed to connect.
        
        Args:
            ip_address: Client IP address
            
        Returns:
            bool: True if allowed, False if blocked
        """
        if ip_address in self.blocked_ips:
            self.metrics['blocked_attempts'] += 1
            self.logger.warning(f"Blocked IP {ip_address} attempted connection")
            return False
        
        return True
    
    def block_user(self, user_id: str, reason: str = "Security violation") -> None:
        """
        Block a user from accessing the system.
        
        Args:
            user_id: User ID to block
            reason: Reason for blocking
        """
        self.blocked_users.add(user_id)
        self.logger.warning(f"User {user_id} blocked: {reason}")
        
        # Remove from auth cache
        self._clear_user_from_cache(user_id)
    
    def block_ip(self, ip_address: str, reason: str = "Security violation") -> None:
        """
        Block an IP address from accessing the system.
        
        Args:
            ip_address: IP address to block
            reason: Reason for blocking
        """
        self.blocked_ips.add(ip_address)
        self.logger.warning(f"IP {ip_address} blocked: {reason}")
    
    def unblock_user(self, user_id: str) -> None:
        """Unblock a user"""
        self.blocked_users.discard(user_id)
        self.logger.info(f"User {user_id} unblocked")
    
    def unblock_ip(self, ip_address: str) -> None:
        """Unblock an IP address"""
        self.blocked_ips.discard(ip_address)
        self.logger.info(f"IP {ip_address} unblocked")
    
    def generate_token(self, user_id: str, additional_claims: Optional[Dict[str, Any]] = None) -> str:
        """
        Generate a JWT token for a user.
        
        Args:
            user_id: User ID
            additional_claims: Additional JWT claims
            
        Returns:
            str: JWT token
        """
        now = datetime.now(timezone.utc)
        expiry = now + timedelta(seconds=self.config.authentication.token_expiry)
        
        payload = {
            'user_id': user_id,
            'sub': user_id,
            'iat': now,
            'exp': expiry,
            'iss': self.config.authentication.issuer,
            'aud': self.config.authentication.audience,
            'jti': secrets.token_hex(16)  # Unique token ID
        }
        
        if additional_claims:
            payload.update(additional_claims)
        
        token = jwt.encode(payload, self.jwt_secret, algorithm=self.jwt_algorithm)
        
        self.logger.info(f"Generated token for user {user_id}")
        return token
    
    def _get_jwt_secret(self) -> str:
        """Get JWT secret from configuration"""
        secret = self.config.authentication.secret_key
        
        if not secret or secret.startswith('${'):
            # Try environment variables
            secret = os.getenv('WEBSOCKET_JWT_SECRET') or os.getenv('JWT_SECRET') or os.getenv('SECRET_KEY')
            
        if not secret or secret.startswith('${'):
            # Generate a fallback secret if not configured
            secret = secrets.token_hex(32)
            self.logger.warning("Using generated JWT secret - configure WEBSOCKET_JWT_SECRET for production")
        
        return secret
    
    def _clear_user_from_cache(self, user_id: str) -> None:
        """Remove user's tokens from authentication cache"""
        tokens_to_remove = []
        
        for token, data in self.auth_cache.items():
            if data.get('user_id') == user_id:
                tokens_to_remove.append(token)
        
        for token in tokens_to_remove:
            del self.auth_cache[token]
            self.cache_expiry.pop(token, None)
    
    async def _cleanup_rate_limits(self) -> None:
        """Background task to clean up old rate limit windows"""
        while True:
            try:
                await asyncio.sleep(self.config.rate_limiting.cleanup_interval)
                await self._cleanup_old_rate_limit_windows()
                
            except Exception as e:
                self.logger.error(f"Error in rate limit cleanup: {e}")
    
    async def _cleanup_old_rate_limit_windows(self) -> None:
        """Clean up old rate limit windows to prevent memory leaks"""
        current_time = time.time()
        window_start = current_time - self.config.rate_limiting.window_size
        
        # Clean up empty or old windows
        identifiers_to_remove = []
        
        for identifier, requests in self.rate_limit_windows.items():
            # Remove old requests
            while requests and requests[0] < window_start:
                requests.popleft()
            
            # Mark empty windows for removal
            if not requests:
                identifiers_to_remove.append(identifier)
        
        # Remove empty windows
        for identifier in identifiers_to_remove:
            del self.rate_limit_windows[identifier]
        
        # Clean up expired auth cache entries
        expired_tokens = [
            token for token, expiry in self.cache_expiry.items()
            if expiry < current_time
        ]
        
        for token in expired_tokens:
            self.auth_cache.pop(token, None)
            self.cache_expiry.pop(token, None)
        
        if identifiers_to_remove or expired_tokens:
            self.logger.debug(f"Cleaned up {len(identifiers_to_remove)} rate limit windows and {len(expired_tokens)} auth cache entries")
    
    async def _load_security_state(self) -> None:
        """Load persistent security state (blocked IPs/users, etc.)"""
        # TODO: Implement persistent storage if needed
        # For now, we start with empty state each time
        pass
    
    async def _save_security_state(self) -> None:
        """Save security state for persistence"""
        # TODO: Implement persistent storage if needed
        pass
    
    @property
    def security_metrics(self) -> Dict[str, Any]:
        """Get security metrics"""
        return {
            **self.metrics,
            'blocked_ips': len(self.blocked_ips),
            'blocked_users': len(self.blocked_users),
            'active_rate_limit_windows': len(self.rate_limit_windows),
            'auth_cache_size': len(self.auth_cache)
        }


class CORSManager:
    """
    CORS (Cross-Origin Resource Sharing) manager for WebSocket connections.
    
    Handles:
    - Origin validation
    - Headers validation  
    - Methods validation
    - Preflight request handling
    """
    
    def __init__(self, cors_config):
        self.config = cors_config
        self.logger = get_logger("CORSManager")
        
        # Compile allowed origins for efficient checking
        self.allowed_origins = set(cors_config.origins) if cors_config.origins else set()
        self.allow_all_origins = "*" in self.allowed_origins
        
        self.logger.info(f"CORS manager initialized with {len(self.allowed_origins)} allowed origins")
    
    def check_origin(self, origin: Optional[str]) -> bool:
        """
        Check if origin is allowed.
        
        Args:
            origin: Origin header value
            
        Returns:
            bool: True if allowed, False otherwise
        """
        if not self.config.enabled:
            return True
        
        # Allow connections without Origin header for local development
        # This happens with direct WebSocket connections, testing tools, etc.
        if not origin:
            self.logger.debug("Allowing connection without Origin header (development mode)")
            return True
        
        if self.allow_all_origins:
            return True
        
        return origin in self.allowed_origins
    
    def get_cors_headers(self, origin: Optional[str]) -> Dict[str, str]:
        """
        Get CORS headers for response.
        
        Args:
            origin: Request origin
            
        Returns:
            Dict[str, str]: CORS headers
        """
        headers = {}
        
        if not self.config.enabled:
            return headers
        
        if self.check_origin(origin):
            headers['Access-Control-Allow-Origin'] = origin or '*'
            
            if self.config.methods:
                headers['Access-Control-Allow-Methods'] = ', '.join(self.config.methods)
            
            if self.config.headers:
                if '*' in self.config.headers:
                    headers['Access-Control-Allow-Headers'] = '*'
                else:
                    headers['Access-Control-Allow-Headers'] = ', '.join(self.config.headers)
        
        return headers


# Example usage
if __name__ == "__main__":
    import asyncio
    from config.models import SecurityConfig, AuthenticationConfig, CorsConfig, RateLimitConfig
    
    async def test_security_manager():
        """Test security manager functionality"""
        
        # Create test configuration
        auth_config = AuthenticationConfig(
            enabled=True,
            secret_key="test-secret-key",
            token_expiry=3600,
            algorithm="HS256",
            issuer="qa-intelligence",
            audience="websocket-client"
        )
        
        cors_config = CorsConfig(
            enabled=True,
            origins=["http://localhost:3000"],
            methods=["GET", "POST"],
            headers=["Content-Type", "Authorization"]
        )
        
        rate_limit_config = RateLimitConfig(
            enabled=True,
            max_requests_per_minute=10,
            burst_limit=5,
            window_size=60,
            cleanup_interval=300
        )
        
        security_config = SecurityConfig(
            authentication=auth_config,
            cors=cors_config,
            rate_limiting=rate_limit_config
        )
        
        # Test security manager
        security_manager = SecurityManager(security_config)
        await security_manager.initialize()
        
        # Test token generation and validation
        user_id = "test_user"
        token = security_manager.generate_token(user_id)
        print(f"Generated token: {token[:50]}...")
        
        # Test authentication
        validated_user = await security_manager.authenticate_token(token)
        print(f"Validated user: {validated_user}")
        
        # Test rate limiting
        for i in range(12):
            allowed = await security_manager.check_rate_limit(user_id)
            print(f"Request {i+1}: {'ALLOWED' if allowed else 'RATE LIMITED'}")
        
        # Display metrics
        print(f"Security metrics: {security_manager.security_metrics}")
        
        await security_manager.cleanup()
    
    asyncio.run(test_security_manager())
