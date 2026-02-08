"""
Auth init.
"""
from .models import (
    User,
    Organization,
    Team,
    Role,
    Permission,
    APIKey,
    Session,
    ROLE_PERMISSIONS,
)
from .auth_service import AuthService, get_auth_service, AuthConfig
from .rbac import (
    RBACContext,
    require_auth,
    require_permission,
    require_role,
    require_org_access,
    optional_auth,
    require_developer_or_higher,
    require_admin_or_higher,
    require_owner,
)

__all__ = [
    "User",
    "Organization",
    "Team",
    "Role",
    "Permission",
    "APIKey",
    "Session",
    "ROLE_PERMISSIONS",
    "AuthService",
    "get_auth_service",
    "AuthConfig",
    # RBAC
    "RBACContext",
    "require_auth",
    "require_permission",
    "require_role",
    "require_org_access",
    "optional_auth",
    "require_developer_or_higher",
    "require_admin_or_higher",
    "require_owner",
]
