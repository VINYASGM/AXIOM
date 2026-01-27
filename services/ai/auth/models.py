"""
RBAC Models for AXIOM

User, Organization, Team, and Role models for multi-tenant access control.
"""
from datetime import datetime
from enum import Enum
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
import uuid


class Role(str, Enum):
    """User roles with hierarchical permissions."""
    OWNER = "owner"       # Full org control, billing, delete org
    ADMIN = "admin"       # Manage users, teams, settings
    DEVELOPER = "developer"  # Create/edit IVCUs, run generations
    VIEWER = "viewer"     # Read-only access


class Permission(str, Enum):
    """Granular permissions for RBAC."""
    # Organization
    ORG_DELETE = "org:delete"
    ORG_SETTINGS = "org:settings"
    ORG_BILLING = "org:billing"
    
    # User management
    USER_INVITE = "user:invite"
    USER_REMOVE = "user:remove"
    USER_ROLE_CHANGE = "user:role_change"
    
    # Team management
    TEAM_CREATE = "team:create"
    TEAM_DELETE = "team:delete"
    TEAM_MANAGE = "team:manage"
    
    # IVCU operations
    IVCU_CREATE = "ivcu:create"
    IVCU_EDIT = "ivcu:edit"
    IVCU_DELETE = "ivcu:delete"
    IVCU_APPROVE = "ivcu:approve"
    
    # Generation
    GENERATE_RUN = "generate:run"
    GENERATE_CANCEL = "generate:cancel"
    
    # Read operations
    READ_CODE = "read:code"
    READ_HISTORY = "read:history"
    READ_ANALYTICS = "read:analytics"


# Role -> Permissions mapping
ROLE_PERMISSIONS: Dict[Role, List[Permission]] = {
    Role.OWNER: list(Permission),  # All permissions
    Role.ADMIN: [
        Permission.USER_INVITE,
        Permission.USER_REMOVE,
        Permission.USER_ROLE_CHANGE,
        Permission.TEAM_CREATE,
        Permission.TEAM_DELETE,
        Permission.TEAM_MANAGE,
        Permission.IVCU_CREATE,
        Permission.IVCU_EDIT,
        Permission.IVCU_DELETE,
        Permission.IVCU_APPROVE,
        Permission.GENERATE_RUN,
        Permission.GENERATE_CANCEL,
        Permission.READ_CODE,
        Permission.READ_HISTORY,
        Permission.READ_ANALYTICS,
    ],
    Role.DEVELOPER: [
        Permission.IVCU_CREATE,
        Permission.IVCU_EDIT,
        Permission.GENERATE_RUN,
        Permission.GENERATE_CANCEL,
        Permission.READ_CODE,
        Permission.READ_HISTORY,
    ],
    Role.VIEWER: [
        Permission.READ_CODE,
        Permission.READ_HISTORY,
    ],
}


class Organization(BaseModel):
    """Organization model for multi-tenant structure."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    slug: str  # URL-friendly identifier
    plan: str = "free"  # free, pro, enterprise
    settings: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        from_attributes = True


class User(BaseModel):
    """User model with organization membership."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    email: str
    name: str
    password_hash: Optional[str] = None  # None for SSO users
    org_id: str
    role: Role = Role.DEVELOPER
    teams: List[str] = Field(default_factory=list)
    settings: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_login: Optional[datetime] = None
    is_active: bool = True
    
    def has_permission(self, permission: Permission) -> bool:
        """Check if user has a specific permission."""
        return permission in ROLE_PERMISSIONS.get(self.role, [])
    
    class Config:
        from_attributes = True


class Team(BaseModel):
    """Team model for grouping users within an organization."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    org_id: str
    description: Optional[str] = None
    members: List[str] = Field(default_factory=list)  # User IDs
    settings: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        from_attributes = True


class APIKey(BaseModel):
    """API key for programmatic access."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    key_hash: str  # Only store hash, not actual key
    key_prefix: str  # First 8 chars for identification
    user_id: str
    org_id: str
    permissions: List[Permission] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_used: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    is_active: bool = True
    
    class Config:
        from_attributes = True


class Session(BaseModel):
    """User session for JWT tracking."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    org_id: str
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    expires_at: datetime
    is_active: bool = True
