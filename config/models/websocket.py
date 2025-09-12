"""
WebSocket configuration models
Contains all WebSocket-related configuration classes migrated from src/websocket/config.py
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ServerConfig(BaseModel):
    """WebSocket server configuration"""

    host: str = Field(default="localhost", description="Server host")
    port: int = Field(default=8765, ge=1024, le=65535, description="Server port")
    max_connections: int = Field(
        default=100, ge=1, description="Maximum concurrent connections"
    )
    max_message_size: int = Field(
        default=1048576, ge=1024, description="Maximum message size in bytes (1MB)"
    )
    max_queue_size: int = Field(
        default=32, ge=1, description="Maximum message queue size"
    )
    ping_interval: Optional[int] = Field(
        default=20, ge=1, description="Ping interval in seconds"
    )
    ping_timeout: Optional[int] = Field(
        default=20, ge=1, description="Ping timeout in seconds"
    )
    close_timeout: Optional[int] = Field(
        default=10, ge=1, description="Connection close timeout"
    )

    model_config = ConfigDict(case_sensitive=False)


class AuthenticationConfig(BaseModel):
    """Authentication configuration"""

    enabled: bool = Field(default=True, description="Enable authentication")
    token_expiry: int = Field(
        default=3600, ge=60, description="Token expiry in seconds"
    )
    secret_key: Optional[str] = Field(default=None, description="Secret key for JWT")
    algorithm: str = Field(default="HS256", description="JWT algorithm")
    issuer: str = Field(default="qa-intelligence", description="Token issuer")
    audience: str = Field(default="websocket-client", description="Token audience")

    @field_validator("secret_key")
    @classmethod
    def validate_secret_key(cls, v):
        if v is None:
            v = os.getenv("WEBSOCKET_SECRET_KEY")
            if v is None:
                # Generate a default secret key for development
                import secrets

                v = secrets.token_urlsafe(32)
        return v

    model_config = ConfigDict(case_sensitive=False)


class CorsConfig(BaseModel):
    """CORS configuration"""

    enabled: bool = Field(default=True, description="Enable CORS")
    origins: List[str] = Field(
        default=[
            "http://localhost:3000",
            "http://localhost:8080",
            "http://localhost:5173",
        ],
        description="Allowed origins",
    )
    methods: List[str] = Field(
        default=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        description="Allowed HTTP methods",
    )
    headers: List[str] = Field(default=["*"], description="Allowed headers")

    model_config = ConfigDict(case_sensitive=False)


class RateLimitConfig(BaseModel):
    """Rate limiting configuration"""

    enabled: bool = Field(default=True, description="Enable rate limiting")
    max_requests_per_minute: int = Field(
        default=60, ge=1, description="Maximum requests per minute"
    )
    burst_limit: int = Field(default=10, ge=1, description="Burst limit")
    window_size: int = Field(default=60, ge=1, description="Window size in seconds")
    cleanup_interval: int = Field(
        default=300, ge=60, description="Cleanup interval in seconds"
    )

    model_config = ConfigDict(case_sensitive=False)


class SecurityConfig(BaseModel):
    """Security configuration container"""

    authentication: AuthenticationConfig = Field(default_factory=AuthenticationConfig)
    cors: CorsConfig = Field(default_factory=CorsConfig)
    rate_limiting: RateLimitConfig = Field(default_factory=RateLimitConfig)

    model_config = ConfigDict(case_sensitive=False)


class SSLConfig(BaseModel):
    """SSL/TLS configuration"""

    enabled: bool = Field(default=False, description="Enable SSL")
    cert_file: Optional[str] = Field(default=None, description="Certificate file path")
    key_file: Optional[str] = Field(default=None, description="Private key file path")
    ca_certs: Optional[str] = Field(
        default=None, description="CA certificates file path"
    )
    verify_mode: str = Field(
        default="CERT_REQUIRED", description="SSL verification mode"
    )

    @field_validator("cert_file", "key_file", "ca_certs")
    @classmethod
    def validate_ssl_files(cls, v):
        """Validate that SSL files exist if specified"""
        if v is not None and not Path(v).exists():
            raise ValueError(f"SSL file not found: {v}")
        return v

    model_config = ConfigDict(case_sensitive=False)


class WebSocketLoggingConfig(BaseModel):
    """WebSocket-specific logging configuration"""

    level: str = Field(default="INFO", description="Logging level")
    file: Optional[str] = Field(
        default="logs/websocket.log", description="Log file path"
    )
    max_file_size: str = Field(default="10MB", description="Maximum log file size")
    backup_count: int = Field(default=5, ge=1, description="Number of backup files")
    format: str = Field(
        default="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        description="Log format",
    )
    log_connections: bool = Field(
        default=True, description="Enable WebSocket connection logging"
    )

    @field_validator("level")
    @classmethod
    def validate_level(cls, v):
        valid_levels = {
            "TRACE",
            "DEBUG",
            "INFO",
            "SUCCESS",
            "WARNING",
            "ERROR",
            "CRITICAL",
        }
        if v.upper() not in valid_levels:
            raise ValueError(f"Invalid log level: {v}. Must be one of {valid_levels}")
        return v.upper()

    model_config = ConfigDict(case_sensitive=False)


class WebSocketConfig(BaseModel):
    """Main WebSocket system configuration"""

    enabled: bool = Field(default=False, description="Enable WebSocket system")

    server: ServerConfig = Field(default_factory=ServerConfig)
    security: SecurityConfig = Field(default_factory=SecurityConfig)
    ssl: SSLConfig = Field(default_factory=SSLConfig)
    logging: WebSocketLoggingConfig = Field(default_factory=WebSocketLoggingConfig)

    # Advanced settings
    enable_compression: bool = Field(
        default=False, description="Enable message compression"
    )
    enable_metrics: bool = Field(default=True, description="Enable performance metrics")
    metrics_interval: int = Field(
        default=60, ge=10, description="Metrics collection interval"
    )

    def get_server_address(self) -> str:
        """Get complete server address"""
        protocol = "wss" if self.ssl.enabled else "ws"
        return f"{protocol}://{self.server.host}:{self.server.port}"

    model_config = ConfigDict(case_sensitive=False)
