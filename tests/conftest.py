"""
Pytest configuration and fixtures for PySentry WAF tests
"""
import sys
from pathlib import Path
import pytest

# Add src to path for imports
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))


@pytest.fixture
def sample_config():
    """Sample configuration for testing"""
    return {
        "SECRET_KEY": "test_secret_key_32_characters_long!",
        "MONGODB_URL": "mongodb://localhost:27017/test_db",
        "DEBUG": True,
        "ENVIRONMENT": "testing",
    }


@pytest.fixture
def auth_manager():
    """Create auth manager for testing"""
    from pysentry.core.auth import AuthManager
    return AuthManager(secret_key="test_secret_key_32_characters_long!")


@pytest.fixture
def input_validator():
    """Create input validator for testing"""
    from pysentry.core.validator import InputValidator
    return InputValidator()


@pytest.fixture
def rate_limiter():
    """Create in-memory rate limiter for testing"""
    from pysentry.core.rate_limiter import InMemoryRateLimiter
    return InMemoryRateLimiter(requests_per_window=5, window_seconds=10)


# Test markers
def pytest_configure(config):
    """Register custom markers"""
    config.addinivalue_line("markers", "unit: mark test as a unit test")
    config.addinivalue_line("markers", "integration: mark test as an integration test")
    config.addinivalue_line("markers", "security: mark test as a security test")
    config.addinivalue_line("markers", "slow: mark test as slow running")
