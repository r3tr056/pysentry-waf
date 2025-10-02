"""
Phase 1 Tests: Configuration System
Test environment-based configuration and validation
"""
import pytest
import os
from pathlib import Path
import sys

# Add phase1_implementation to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.pysentry.core.config import Config


class TestConfiguration:
    """Test configuration management"""
    
    def test_default_values(self):
        """Test default configuration values"""
        config = Config()
        
        assert config.ENVIRONMENT == 'development'
        assert config.LOG_LEVEL == 'INFO'
        assert config.DEBUG is False
        assert config.RATE_LIMIT_ENABLED is True
        assert config.RATE_LIMIT_REQUESTS == 100
        assert config.RATE_LIMIT_WINDOW == 60
    
    def test_environment_variable_override(self, monkeypatch):
        """Test configuration from environment variables"""
        monkeypatch.setenv('ENVIRONMENT', 'production')
        monkeypatch.setenv('DEBUG', 'true')
        monkeypatch.setenv('RATE_LIMIT_REQUESTS', '200')
        
        # Create new config instance after env vars are set
        config = Config()
        assert config.ENVIRONMENT == 'production'
        assert config.DEBUG is True
        assert config.RATE_LIMIT_REQUESTS == 200
    
    def test_secret_key_validation_production(self, monkeypatch):
        """Test SECRET_KEY validation in production"""
        monkeypatch.setenv('ENVIRONMENT', 'production')
        monkeypatch.setenv('SECRET_KEY', 'short')
        
        # Create new config instance after env vars are set
        config = Config()
        
        with pytest.raises(ValueError, match="SECRET_KEY must be set"):
            config.validate()
    
    def test_model_path_validation(self, monkeypatch):
        """Test ML model path validation"""
        # Set a non-default path that doesn't exist
        monkeypatch.setenv('THREAT_MODEL_PATH', '/nonexistent/path.joblib')
        
        config = Config()
        
        with pytest.raises(ValueError, match="Threat model not found"):
            config.validate()
    
    def test_get_summary(self):
        """Test configuration summary"""
        config = Config()
        summary = config.get_summary()
        
        assert 'environment' in summary
        assert 'debug' in summary
        assert 'log_level' in summary
        assert isinstance(summary['mongodb_configured'], bool)
        assert isinstance(summary['rate_limiting_enabled'], bool)


class TestEnvironmentFile:
    """Test .env.example file"""
    
    def test_env_example_exists(self):
        """Test .env.example file exists"""
        # Look in repository root config directory
        env_file = Path(__file__).parent.parent.parent / 'config' / '.env.example'
        assert env_file.exists()
    
    def test_env_example_has_required_vars(self):
        """Test .env.example contains required variables"""
        # Look in repository root config directory
        env_file = Path(__file__).parent.parent.parent / 'config' / '.env.example'
        content = env_file.read_text()
        
        required_vars = [
            'SECRET_KEY',
            'MONGODB_URL',
            'ENVIRONMENT',
            'DEBUG',
            'RATE_LIMIT_ENABLED'
        ]
        
        for var in required_vars:
            assert var in content, f"Missing {var} in .env.example"


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
