"""
Phase 1.4: JWT Authentication System
Production-grade authentication with role-based access control
"""
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from passlib.context import CryptContext
import logging

logger = logging.getLogger(__name__)

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Security scheme
security = HTTPBearer()


class AuthManager:
    """
    JWT-based authentication manager with role-based access control.
    
    Features:
    - JWT token generation and validation
    - Password hashing with bcrypt
    - Role-based access control
    - Token expiration handling
    """
    
    def __init__(self, secret_key: str, algorithm: str = "HS256", 
                 expiration_hours: int = 24):
        """
        Initialize authentication manager.
        
        Args:
            secret_key: Secret key for JWT encoding
            algorithm: JWT algorithm (default: HS256)
            expiration_hours: Token expiration time in hours
        """
        if not secret_key or len(secret_key) < 32:
            raise ValueError("SECRET_KEY must be at least 32 characters")
        
        self.secret_key = secret_key
        self.algorithm = algorithm
        self.expiration_hours = expiration_hours
    
    def hash_password(self, password: str) -> str:
        """
        Hash a password using bcrypt.
        
        Args:
            password: Plain text password
            
        Returns:
            Hashed password
        """
        return pwd_context.hash(password)
    
    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """
        Verify a password against its hash.
        
        Args:
            plain_password: Plain text password
            hashed_password: Hashed password to verify against
            
        Returns:
            True if password matches, False otherwise
        """
        return pwd_context.verify(plain_password, hashed_password)
    
    def create_access_token(self, data: Dict[str, Any], 
                           expires_delta: Optional[timedelta] = None) -> str:
        """
        Create a JWT access token.
        
        Args:
            data: Data to encode in the token (should include 'sub' for user ID)
            expires_delta: Optional custom expiration time
            
        Returns:
            JWT token string
        """
        to_encode = data.copy()
        
        if expires_delta:
            expire = datetime.now(timezone.utc) + expires_delta
        else:
            expire = datetime.now(timezone.utc) + timedelta(hours=self.expiration_hours)
        
        to_encode.update({
            "exp": expire,
            "iat": datetime.now(timezone.utc),
            "type": "access"
        })
        
        try:
            encoded_jwt = jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)
            return encoded_jwt
        except Exception as e:
            logger.error(f"Error creating access token: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Could not create access token"
            )
    
    def verify_token(self, credentials: HTTPAuthorizationCredentials = Depends(security)) -> Dict[str, Any]:
        """
        Verify and decode a JWT token.
        
        Args:
            credentials: HTTP Bearer credentials from request
            
        Returns:
            Decoded token payload
            
        Raises:
            HTTPException: If token is invalid or expired
        """
        try:
            payload = jwt.decode(
                credentials.credentials, 
                self.secret_key, 
                algorithms=[self.algorithm]
            )
            
            # Validate token type
            if payload.get("type") != "access":
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid token type"
                )
            
            return payload
            
        except jwt.ExpiredSignatureError:
            logger.warning("Expired token used")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has expired"
            )
        except Exception as e:
            logger.warning(f"Invalid token: {e}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials"
            )
    
    def get_current_user(self, token_payload: Dict[str, Any] = Depends(verify_token)) -> Dict[str, Any]:
        """
        Get current user from validated token.
        
        Args:
            token_payload: Decoded token payload
            
        Returns:
            User information from token
        """
        user_id = token_payload.get("sub")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token payload"
            )
        
        return {
            "user_id": user_id,
            "username": token_payload.get("username"),
            "role": token_payload.get("role", "user")
        }
    
    def require_role(self, required_role: str):
        """
        Dependency to require a specific role.
        
        Args:
            required_role: Role required to access the endpoint
            
        Returns:
            Dependency function
        """
        def role_checker(current_user: Dict[str, Any] = Depends(self.get_current_user)):
            user_role = current_user.get("role", "user")
            
            # Admin has access to everything
            if user_role == "admin":
                return current_user
            
            # Check specific role
            if user_role != required_role:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Requires {required_role} role"
                )
            
            return current_user
        
        return role_checker


class APIKeyManager:
    """
    API Key management for service-to-service authentication.
    
    Features:
    - API key generation
    - API key validation
    - Key expiration
    """
    
    def __init__(self, secret_key: str):
        """
        Initialize API key manager.
        
        Args:
            secret_key: Secret key for API key encoding
        """
        self.secret_key = secret_key
    
    def create_api_key(self, service_name: str, expires_days: int = 365) -> str:
        """
        Create an API key for a service.
        
        Args:
            service_name: Name of the service
            expires_days: Days until key expires
            
        Returns:
            API key string
        """
        expire = datetime.now(timezone.utc) + timedelta(days=expires_days)
        
        payload = {
            "service": service_name,
            "exp": expire,
            "iat": datetime.now(timezone.utc),
            "type": "api_key"
        }
        
        api_key = jwt.encode(payload, self.secret_key, algorithm="HS256")
        return api_key
    
    def verify_api_key(self, api_key: str) -> Dict[str, Any]:
        """
        Verify an API key.
        
        Args:
            api_key: API key to verify
            
        Returns:
            Decoded API key payload
            
        Raises:
            HTTPException: If API key is invalid or expired
        """
        try:
            payload = jwt.decode(api_key, self.secret_key, algorithms=["HS256"])
            
            if payload.get("type") != "api_key":
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid API key type"
                )
            
            return payload
            
        except jwt.ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="API key has expired"
            )
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid API key"
            )
