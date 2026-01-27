"""
Authentication Service for AXIOM

JWT token management, password hashing, and session handling.
"""
import os
import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, Tuple
import jwt
from passlib.context import CryptContext

from .models import User, Organization, APIKey, Session, Role, Permission, ROLE_PERMISSIONS


class AuthConfig:
    """Auth configuration."""
    JWT_SECRET = os.getenv("JWT_SECRET", "axiom-dev-secret-change-in-prod")
    JWT_ALGORITHM = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES = 60
    REFRESH_TOKEN_EXPIRE_DAYS = 7
    API_KEY_PREFIX = "axm_"


# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class AuthService:
    """
    Authentication and authorization service.
    
    Handles:
    - Password hashing and verification
    - JWT token generation and validation
    - API key management
    - Permission checking
    """
    
    def __init__(self, db_service=None):
        self.db = db_service
        self._cached_users: Dict[str, User] = {}
    
    # =========================================================================
    # Password Management
    # =========================================================================
    
    def hash_password(self, password: str) -> str:
        """Hash a password for storage."""
        return pwd_context.hash(password)
    
    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verify a password against its hash."""
        return pwd_context.verify(plain_password, hashed_password)
    
    # =========================================================================
    # JWT Token Management
    # =========================================================================
    
    def create_access_token(
        self,
        user_id: str,
        org_id: str,
        role: Role,
        expires_delta: Optional[timedelta] = None
    ) -> str:
        """
        Create a JWT access token.
        
        Returns:
            JWT token string
        """
        if expires_delta is None:
            expires_delta = timedelta(minutes=AuthConfig.ACCESS_TOKEN_EXPIRE_MINUTES)
        
        expire = datetime.utcnow() + expires_delta
        
        payload = {
            "sub": user_id,
            "org": org_id,
            "role": role.value,
            "exp": expire,
            "iat": datetime.utcnow(),
            "type": "access"
        }
        
        return jwt.encode(
            payload,
            AuthConfig.JWT_SECRET,
            algorithm=AuthConfig.JWT_ALGORITHM
        )
    
    def create_refresh_token(self, user_id: str) -> str:
        """Create a refresh token for token renewal."""
        expire = datetime.utcnow() + timedelta(days=AuthConfig.REFRESH_TOKEN_EXPIRE_DAYS)
        
        payload = {
            "sub": user_id,
            "exp": expire,
            "iat": datetime.utcnow(),
            "type": "refresh",
            "jti": secrets.token_hex(16)  # Unique token ID
        }
        
        return jwt.encode(
            payload,
            AuthConfig.JWT_SECRET,
            algorithm=AuthConfig.JWT_ALGORITHM
        )
    
    def decode_token(self, token: str) -> Optional[Dict[str, Any]]:
        """
        Decode and validate a JWT token.
        
        Returns:
            Token payload if valid, None otherwise
        """
        try:
            payload = jwt.decode(
                token,
                AuthConfig.JWT_SECRET,
                algorithms=[AuthConfig.JWT_ALGORITHM]
            )
            return payload
        except jwt.ExpiredSignatureError:
            return None
        except jwt.InvalidTokenError:
            return None
    
    def validate_access_token(self, token: str) -> Optional[Tuple[str, str, Role]]:
        """
        Validate an access token and extract user info.
        
        Returns:
            Tuple of (user_id, org_id, role) if valid, None otherwise
        """
        payload = self.decode_token(token)
        if not payload or payload.get("type") != "access":
            return None
        
        try:
            return (
                payload["sub"],
                payload["org"],
                Role(payload["role"])
            )
        except (KeyError, ValueError):
            return None
    
    # =========================================================================
    # API Key Management
    # =========================================================================
    
    def generate_api_key(self) -> Tuple[str, str]:
        """
        Generate a new API key.
        
        Returns:
            Tuple of (full_key, key_hash)
        """
        key = AuthConfig.API_KEY_PREFIX + secrets.token_urlsafe(32)
        key_hash = hashlib.sha256(key.encode()).hexdigest()
        return key, key_hash
    
    def hash_api_key(self, key: str) -> str:
        """Hash an API key for lookup."""
        return hashlib.sha256(key.encode()).hexdigest()
    
    def get_api_key_prefix(self, key: str) -> str:
        """Get the prefix of an API key for identification."""
        return key[:8]
    
    async def validate_api_key(self, key: str) -> Optional[APIKey]:
        """
        Validate an API key.
        
        Returns:
            APIKey object if valid, None otherwise
        """
        if not self.db:
            return None
        
        key_hash = self.hash_api_key(key)
        # Query database for key
        # This would be implemented with actual DB query
        return None
    
    # =========================================================================
    # Permission Checking
    # =========================================================================
    
    def has_permission(self, role: Role, permission: Permission) -> bool:
        """Check if a role has a specific permission."""
        return permission in ROLE_PERMISSIONS.get(role, [])
    
    def get_permissions(self, role: Role) -> list:
        """Get all permissions for a role."""
        return ROLE_PERMISSIONS.get(role, [])
    
    def check_org_access(
        self,
        user_org_id: str,
        target_org_id: str
    ) -> bool:
        """Check if user can access a resource in an org."""
        return user_org_id == target_org_id
    
    # =========================================================================
    # User Context
    # =========================================================================
    
    async def get_current_user(self, token: str) -> Optional[User]:
        """
        Get the current user from a token.
        
        Returns:
            User object if token is valid, None otherwise
        """
        result = self.validate_access_token(token)
        if not result:
            return None
        
        user_id, org_id, role = result
        
        # Check cache
        if user_id in self._cached_users:
            return self._cached_users[user_id]
        
        # Query database (implementation would go here)
        # For now, return a minimal user object
        user = User(
            id=user_id,
            email="",
            name="",
            org_id=org_id,
            role=role
        )
        
        self._cached_users[user_id] = user
        return user


# Singleton instance
_auth_service: Optional[AuthService] = None


def get_auth_service(db_service=None) -> AuthService:
    """Get or create auth service singleton."""
    global _auth_service
    if _auth_service is None:
        _auth_service = AuthService(db_service)
    return _auth_service
