"""
RBAC Middleware for FastAPI (Design.md Phase 2)

Provides FastAPI dependencies for role-based access control:
- require_auth: Validates JWT and extracts user context
- require_permission: Checks specific permissions
- require_role: Checks minimum role level

Usage:
    @app.post("/generate")
    async def generate(user: User = Depends(require_auth)):
        ...
    
    @app.delete("/ivcu/{id}")
    async def delete_ivcu(
        user: User = Depends(require_permission(Permission.IVCU_DELETE))
    ):
        ...
"""
from functools import wraps
from typing import Optional, List, Callable

from fastapi import Depends, HTTPException, status, Header, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from auth.models import User, Role, Permission, ROLE_PERMISSIONS
from auth.auth_service import get_auth_service, AuthService


# Security scheme
security = HTTPBearer(auto_error=False)


class RBACContext:
    """
    Context object holding user information for the current request.
    
    Attributes:
        user_id: UUID of the authenticated user
        org_id: UUID of the user's organization
        role: User's role (owner, admin, developer, viewer)
        permissions: List of permissions granted to the user
    """
    
    def __init__(
        self,
        user_id: str,
        org_id: str,
        role: Role,
        email: str = ""
    ):
        self.user_id = user_id
        self.org_id = org_id
        self.role = role
        self.email = email
        self._permissions = ROLE_PERMISSIONS.get(role, [])
    
    @property
    def permissions(self) -> List[Permission]:
        """Get all permissions for this user's role."""
        return self._permissions
    
    def has_permission(self, permission: Permission) -> bool:
        """Check if user has a specific permission."""
        return permission in self._permissions
    
    def has_role(self, min_role: Role) -> bool:
        """Check if user has at least the specified role level."""
        role_hierarchy = {
            Role.VIEWER: 0,
            Role.DEVELOPER: 1,
            Role.ADMIN: 2,
            Role.OWNER: 3
        }
        return role_hierarchy.get(self.role, 0) >= role_hierarchy.get(min_role, 0)
    
    def can_access_org(self, target_org_id: str) -> bool:
        """Check if user can access resources in the target organization."""
        return self.org_id == target_org_id


async def get_auth_context(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    x_api_key: Optional[str] = Header(None, alias="X-API-Key")
) -> Optional[RBACContext]:
    """
    Extract auth context from JWT token or API key.
    
    Returns None if no valid credentials provided.
    """
    auth_service = get_auth_service()
    
    # Try JWT token first
    if credentials:
        result = auth_service.validate_access_token(credentials.credentials)
        if result:
            user_id, org_id, role = result
            return RBACContext(
                user_id=user_id,
                org_id=org_id,
                role=role
            )
    
    # Try API key
    if x_api_key:
        api_key = await auth_service.validate_api_key(x_api_key)
        if api_key:
            return RBACContext(
                user_id=api_key.user_id,
                org_id=api_key.org_id,
                role=Role.DEVELOPER  # API keys default to developer role
            )
    
    return None


async def require_auth(
    ctx: Optional[RBACContext] = Depends(get_auth_context)
) -> RBACContext:
    """
    Dependency that requires authentication.
    
    Raises 401 if no valid credentials provided.
    
    Example:
        @app.get("/me")
        async def get_me(user: RBACContext = Depends(require_auth)):
            return {"user_id": user.user_id}
    """
    if ctx is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"}
        )
    return ctx


def require_permission(permission: Permission) -> Callable:
    """
    Dependency factory that requires a specific permission.
    
    Raises 403 if user doesn't have the required permission.
    
    Example:
        @app.delete("/ivcu/{id}")
        async def delete_ivcu(
            user: RBACContext = Depends(require_permission(Permission.IVCU_DELETE))
        ):
            ...
    """
    async def check_permission(
        ctx: RBACContext = Depends(require_auth)
    ) -> RBACContext:
        if not ctx.has_permission(permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission denied: {permission.value} required"
            )
        return ctx
    
    return check_permission


def require_role(min_role: Role) -> Callable:
    """
    Dependency factory that requires at least a specific role level.
    
    Raises 403 if user's role is below the required level.
    
    Role hierarchy: viewer < developer < admin < owner
    
    Example:
        @app.post("/team")
        async def create_team(
            user: RBACContext = Depends(require_role(Role.ADMIN))
        ):
            ...
    """
    async def check_role(
        ctx: RBACContext = Depends(require_auth)
    ) -> RBACContext:
        if not ctx.has_role(min_role):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role required: {min_role.value} or higher"
            )
        return ctx
    
    return check_role


def require_org_access(org_id_param: str = "org_id") -> Callable:
    """
    Dependency factory that checks organization access.
    
    Verifies user can access resources in the specified organization.
    
    Example:
        @app.get("/orgs/{org_id}/ivcu")
        async def list_ivcu(
            org_id: str,
            user: RBACContext = Depends(require_org_access("org_id"))
        ):
            ...
    """
    async def check_org_access(
        request: Request,
        ctx: RBACContext = Depends(require_auth)
    ) -> RBACContext:
        target_org_id = request.path_params.get(org_id_param)
        
        if target_org_id and not ctx.can_access_org(target_org_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this organization"
            )
        return ctx
    
    return check_org_access


# =============================================================================
# Convenience combinations
# =============================================================================

async def require_developer_or_higher(
    ctx: RBACContext = Depends(require_role(Role.DEVELOPER))
) -> RBACContext:
    """Require at least developer role."""
    return ctx


async def require_admin_or_higher(
    ctx: RBACContext = Depends(require_role(Role.ADMIN))
) -> RBACContext:
    """Require at least admin role."""
    return ctx


async def require_owner(
    ctx: RBACContext = Depends(require_role(Role.OWNER))
) -> RBACContext:
    """Require owner role."""
    return ctx


# =============================================================================
# Optional auth for public endpoints
# =============================================================================

async def optional_auth(
    ctx: Optional[RBACContext] = Depends(get_auth_context)
) -> Optional[RBACContext]:
    """
    Optional authentication - returns None if not authenticated.
    
    Useful for endpoints that behave differently for authenticated users.
    
    Example:
        @app.get("/public")
        async def public_endpoint(user: Optional[RBACContext] = Depends(optional_auth)):
            if user:
                return {"message": f"Hello, {user.user_id}"}
            return {"message": "Hello, anonymous"}
    """
    return ctx
