"""
Phase 1.1: Environment-based Configuration System
Production-grade configuration management with validation
"""
import os
from typing import Optional
from pathlib import Path


class Config:
    """Production-ready configuration with environment variable support"""
    
    # Security
    SECRET_KEY: str = os.getenv('SECRET_KEY', '')
    JWT_ALGORITHM: str = os.getenv('JWT_ALGORITHM', 'HS256')
    JWT_EXPIRATION_HOURS: int = int(os.getenv('JWT_EXPIRATION_HOURS', '24'))
    
    # Database - MongoDB
    MONGODB_URL: str = os.getenv('MONGODB_URL', 'mongodb://localhost:27017/')
    MONGODB_DB_NAME: str = os.getenv('MONGODB_DB_NAME', 'waf_db')
    MONGODB_MAX_POOL_SIZE: int = int(os.getenv('MONGODB_MAX_POOL_SIZE', '50'))
    
    # Database - PostgreSQL (for request logs)
    POSTGRESQL_URL: str = os.getenv('POSTGRESQL_URL', '')
    
    # SQLite (fallback for logging)
    SQLITE_DB_PATH: str = os.getenv('SQLITE_DB_PATH', './logs/log.db')
    
    # Redis (for caching and rate limiting)
    REDIS_URL: Optional[str] = os.getenv('REDIS_URL', None)
    REDIS_MAX_CONNECTIONS: int = int(os.getenv('REDIS_MAX_CONNECTIONS', '50'))
    
    # Application
    DEBUG: bool = os.getenv('DEBUG', 'False').lower() == 'true'
    LOG_LEVEL: str = os.getenv('LOG_LEVEL', 'INFO')
    ENVIRONMENT: str = os.getenv('ENVIRONMENT', 'development')
    
    # WAF Settings
    DEFAULT_SNIFF_PORT: int = int(os.getenv('DEFAULT_SNIFF_PORT', '80'))
    MAX_REQUEST_SIZE: int = int(os.getenv('MAX_REQUEST_SIZE', '10485760'))  # 10MB
    BLOCK_MODE: bool = os.getenv('BLOCK_MODE', 'True').lower() == 'true'
    
    # Rate Limiting
    RATE_LIMIT_ENABLED: bool = os.getenv('RATE_LIMIT_ENABLED', 'True').lower() == 'true'
    RATE_LIMIT_REQUESTS: int = int(os.getenv('RATE_LIMIT_REQUESTS', '100'))
    RATE_LIMIT_WINDOW: int = int(os.getenv('RATE_LIMIT_WINDOW', '60'))
    
    # ML Models
    THREAT_MODEL_PATH: str = os.getenv('THREAT_MODEL_PATH', './waf/threat_engine/predictor.joblib')
    PT_MODEL_PATH: str = os.getenv('PT_MODEL_PATH', './waf/threat_engine/pt_predictor.joblib')
    
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
    
    @classmethod
    def validate(cls) -> None:
        """Validate critical configuration for production"""
        errors = []
        
        # Check SECRET_KEY in production
        if cls.ENVIRONMENT == 'production':
            if not cls.SECRET_KEY or len(cls.SECRET_KEY) < 32:
                errors.append("SECRET_KEY must be set and at least 32 characters for production")
            
            if cls.MONGODB_URL == 'mongodb://localhost:27017/':
                errors.append("MONGODB_URL must be configured for production")
            
            if cls.DEBUG:
                errors.append("DEBUG must be False in production")
        
        # Check model files exist
        if not Path(cls.THREAT_MODEL_PATH).exists():
            errors.append(f"Threat model not found at {cls.THREAT_MODEL_PATH}")
        
        if not Path(cls.PT_MODEL_PATH).exists():
            errors.append(f"Parameter tampering model not found at {cls.PT_MODEL_PATH}")
        
        if errors:
            raise ValueError("Configuration validation failed:\n" + "\n".join(f"  - {e}" for e in errors))
    
    @classmethod
    def get_summary(cls) -> dict:
        """Get configuration summary (sanitized for logging)"""
        return {
            'environment': cls.ENVIRONMENT,
            'debug': cls.DEBUG,
            'log_level': cls.LOG_LEVEL,
            'mongodb_configured': bool(cls.MONGODB_URL and cls.MONGODB_URL != 'mongodb://localhost:27017/'),
            'redis_configured': bool(cls.REDIS_URL),
            'rate_limiting_enabled': cls.RATE_LIMIT_ENABLED,
            'block_mode': cls.BLOCK_MODE,
        }


# Create global config instance
config = Config()
