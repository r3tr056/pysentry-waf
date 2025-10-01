"""
Phase 1 Tests: Authentication System
Test JWT authentication and API key management
"""
import pytest
from datetime import timedelta
import jwt
import sys
from pathlib import Path

# Add phase1_implementation to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from auth.authentication import AuthManager, APIKeyManager
from fastapi import HTTPException


class TestAuthManager:
    """Test JWT authentication manager"""
    
    @pytest.fixture
    def auth_manager(self):
        """Create auth manager for testing"""
        return AuthManager(secret_key="test_secret_key_32_characters_long!", algorithm="HS256")
    
    def test_initialization_with_short_key(self):
        """Test error with short secret key"""
        with pytest.raises(ValueError, match="SECRET_KEY must be at least 32 characters"):
            AuthManager(secret_key="short")
    
    def test_password_hashing(self, auth_manager):
        """Test password hashing and verification"""
        password = "secure_password_123"
        hashed = auth_manager.hash_password(password)
        
        assert hashed != password
        assert auth_manager.verify_password(password, hashed)
        assert not auth_manager.verify_password("wrong_password", hashed)
    
    def test_create_access_token(self, auth_manager):
        """Test JWT token creation"""
        data = {"sub": "user123", "username": "testuser", "role": "admin"}
        token = auth_manager.create_access_token(data)
        
        assert isinstance(token, str)
        assert len(token) > 0
        
        # Decode and verify
        decoded = jwt.decode(token, auth_manager.secret_key, algorithms=[auth_manager.algorithm])
        assert decoded["sub"] == "user123"
        assert decoded["username"] == "testuser"
        assert decoded["role"] == "admin"
        assert "exp" in decoded
        assert "iat" in decoded
        assert decoded["type"] == "access"
    
    def test_create_token_with_custom_expiration(self, auth_manager):
        """Test token creation with custom expiration"""
        data = {"sub": "user123"}
        expires_delta = timedelta(hours=1)
        token = auth_manager.create_access_token(data, expires_delta=expires_delta)
        
        decoded = jwt.decode(token, auth_manager.secret_key, algorithms=[auth_manager.algorithm])
        
        # Check expiration is approximately 1 hour from now
        import time
        exp_time = decoded["exp"]
        current_time = time.time()
        time_diff = exp_time - current_time
        
        assert 3500 < time_diff < 3700  # Around 1 hour (3600 seconds)
    
    def test_verify_valid_token(self, auth_manager):
        """Test token verification with valid token"""
        from fastapi.security import HTTPAuthorizationCredentials
        
        data = {"sub": "user123", "username": "testuser"}
        token = auth_manager.create_access_token(data)
        
        # Create mock credentials
        credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)
        
        # This would normally be called through dependency injection
        # For testing, we call the method directly
        payload = auth_manager.verify_token(credentials)
        
        assert payload["sub"] == "user123"
        assert payload["username"] == "testuser"
    
    def test_verify_expired_token(self, auth_manager):
        """Test token verification with expired token"""
        from fastapi.security import HTTPAuthorizationCredentials
        
        # Create token that expires immediately
        data = {"sub": "user123"}
        expires_delta = timedelta(seconds=-1)  # Already expired
        token = auth_manager.create_access_token(data, expires_delta=expires_delta)
        
        credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)
        
        with pytest.raises(HTTPException) as exc_info:
            auth_manager.verify_token(credentials)
        
        assert exc_info.value.status_code == 401
        assert "expired" in exc_info.value.detail.lower()
    
    def test_verify_invalid_token(self, auth_manager):
        """Test token verification with invalid token"""
        from fastapi.security import HTTPAuthorizationCredentials
        
        credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials="invalid_token")
        
        with pytest.raises(HTTPException) as exc_info:
            auth_manager.verify_token(credentials)
        
        assert exc_info.value.status_code == 401
    
    def test_get_current_user(self, auth_manager):
        """Test extracting current user from token"""
        token_payload = {
            "sub": "user123",
            "username": "testuser",
            "role": "admin"
        }
        
        user = auth_manager.get_current_user(token_payload)
        
        assert user["user_id"] == "user123"
        assert user["username"] == "testuser"
        assert user["role"] == "admin"
    
    def test_require_role_admin(self, auth_manager):
        """Test role requirement for admin"""
        admin_user = {"user_id": "123", "username": "admin", "role": "admin"}
        regular_user = {"user_id": "456", "username": "user", "role": "user"}
        
        admin_checker = auth_manager.require_role("admin")
        
        # Admin should pass
        result = admin_checker(admin_user)
        assert result == admin_user
        
        # Regular user should fail
        with pytest.raises(HTTPException) as exc_info:
            admin_checker(regular_user)
        
        assert exc_info.value.status_code == 403


class TestAPIKeyManager:
    """Test API key management"""
    
    @pytest.fixture
    def api_key_manager(self):
        """Create API key manager for testing"""
        return APIKeyManager(secret_key="test_secret_key_32_characters_long!")
    
    def test_create_api_key(self, api_key_manager):
        """Test API key creation"""
        service_name = "test_service"
        api_key = api_key_manager.create_api_key(service_name, expires_days=30)
        
        assert isinstance(api_key, str)
        assert len(api_key) > 0
        
        # Decode and verify
        decoded = jwt.decode(api_key, api_key_manager.secret_key, algorithms=["HS256"])
        assert decoded["service"] == service_name
        assert decoded["type"] == "api_key"
        assert "exp" in decoded
    
    def test_verify_valid_api_key(self, api_key_manager):
        """Test API key verification"""
        api_key = api_key_manager.create_api_key("test_service")
        
        payload = api_key_manager.verify_api_key(api_key)
        
        assert payload["service"] == "test_service"
        assert payload["type"] == "api_key"
    
    def test_verify_expired_api_key(self, api_key_manager):
        """Test verification of expired API key"""
        # Create expired key
        api_key = api_key_manager.create_api_key("test_service", expires_days=-1)
        
        with pytest.raises(HTTPException) as exc_info:
            api_key_manager.verify_api_key(api_key)
        
        assert exc_info.value.status_code == 401
        assert "expired" in exc_info.value.detail.lower()
    
    def test_verify_invalid_api_key(self, api_key_manager):
        """Test verification of invalid API key"""
        with pytest.raises(HTTPException) as exc_info:
            api_key_manager.verify_api_key("invalid_key")
        
        assert exc_info.value.status_code == 401


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
