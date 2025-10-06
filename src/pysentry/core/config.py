"""
Phase 1.1: Environment-based Configuration System
Production-grade configuration management with validation
"""
import os
from typing import Optional
from pathlib import Path


class Config:
    """Production-ready configuration with environment variable support"""
    
    def __init__(self):
        """Initialize configuration from environment variables"""
        self._load_from_env()
    
    def _load_from_env(self):
        """Load all configuration from environment variables"""
        # Security
        self.SECRET_KEY: str = os.getenv('SECRET_KEY', '')
        self.JWT_ALGORITHM: str = os.getenv('JWT_ALGORITHM', 'HS256')
        self.JWT_EXPIRATION_HOURS: int = int(os.getenv('JWT_EXPIRATION_HOURS', '24'))
        
        # Database - MongoDB
        self.MONGODB_URL: str = os.getenv('MONGODB_URL', 'mongodb://localhost:27017/')
        self.MONGODB_DB_NAME: str = os.getenv('MONGODB_DB_NAME', 'waf_db')
        self.MONGODB_MAX_POOL_SIZE: int = int(os.getenv('MONGODB_MAX_POOL_SIZE', '50'))
        
        # Database - PostgreSQL (for request logs)
        self.POSTGRESQL_URL: str = os.getenv('POSTGRESQL_URL', '')
        
        # SQLite (fallback for logging)
        self.SQLITE_DB_PATH: str = os.getenv('SQLITE_DB_PATH', './logs/log.db')
        
        # Redis (for caching and rate limiting)
        self.REDIS_URL: Optional[str] = os.getenv('REDIS_URL', None)
        self.REDIS_MAX_CONNECTIONS: int = int(os.getenv('REDIS_MAX_CONNECTIONS', '50'))
        
        # Application
        self.DEBUG: bool = os.getenv('DEBUG', 'False').lower() == 'true'
        self.LOG_LEVEL: str = os.getenv('LOG_LEVEL', 'INFO')
        self.ENVIRONMENT: str = os.getenv('ENVIRONMENT', 'development')
        
        # WAF Settings
        self.DEFAULT_SNIFF_PORT: int = int(os.getenv('DEFAULT_SNIFF_PORT', '80'))
        self.MAX_REQUEST_SIZE: int = int(os.getenv('MAX_REQUEST_SIZE', '10485760'))  # 10MB
        self.BLOCK_MODE: bool = os.getenv('BLOCK_MODE', 'True').lower() == 'true'
        
        # Rate Limiting
        self.RATE_LIMIT_ENABLED: bool = os.getenv('RATE_LIMIT_ENABLED', 'True').lower() == 'true'
        self.RATE_LIMIT_REQUESTS: int = int(os.getenv('RATE_LIMIT_REQUESTS', '100'))
        self.RATE_LIMIT_WINDOW: int = int(os.getenv('RATE_LIMIT_WINDOW', '60'))
        
        # ML Models
        self.THREAT_MODEL_PATH: str = os.getenv('THREAT_MODEL_PATH', './waf/threat_engine/predictor.joblib')
        self.PT_MODEL_PATH: str = os.getenv('PT_MODEL_PATH', './waf/threat_engine/pt_predictor.joblib')
    
    @property
    def mongodb_url(self) -> str:
        """Get MongoDB URL"""
        return self.MONGODB_URL
    
    @property
    def redis_url(self) -> Optional[str]:
        """Get Redis URL"""
        return self.REDIS_URL
    
    @property
    def secret_key(self) -> str:
        """Get secret key"""
        return self.SECRET_KEY
    
    def validate(self) -> None:
        """Validate critical configuration for production"""
        errors = []
        
        # Check SECRET_KEY in production
        if self.ENVIRONMENT == 'production':
            if not self.SECRET_KEY or len(self.SECRET_KEY) < 32:
                errors.append("SECRET_KEY must be set and at least 32 characters for production")
            
            if self.MONGODB_URL == 'mongodb://localhost:27017/':
                errors.append("MONGODB_URL must be configured for production")
            
            if self.DEBUG:
                errors.append("DEBUG must be False in production")
        
        # Check model files exist (only when path is set and not default)
        if self.THREAT_MODEL_PATH != './waf/threat_engine/predictor.joblib':
            if not Path(self.THREAT_MODEL_PATH).exists():
                errors.append(f"Threat model not found at {self.THREAT_MODEL_PATH}")
        
        if self.PT_MODEL_PATH != './waf/threat_engine/pt_predictor.joblib':
            if not Path(self.PT_MODEL_PATH).exists():
                errors.append(f"Parameter tampering model not found at {self.PT_MODEL_PATH}")
        
        if errors:
            raise ValueError("Configuration validation failed:\n" + "\n".join(f"  - {e}" for e in errors))
    
    def get_summary(self) -> dict:
        """Get configuration summary (sanitized for logging)"""
        return {
            'environment': self.ENVIRONMENT,
            'debug': self.DEBUG,
            'log_level': self.LOG_LEVEL,
            'mongodb_configured': bool(self.MONGODB_URL and self.MONGODB_URL != 'mongodb://localhost:27017/'),
            'redis_configured': bool(self.REDIS_URL),
            'rate_limiting_enabled': self.RATE_LIMIT_ENABLED,
            'block_mode': self.BLOCK_MODE,
        }


# Create global config instance
config = Config()
