package middleware

import (
	"database/sql"
	"net/http"

	"github.com/axiom/api/internal/database"
	"github.com/gin-gonic/gin"
	"github.com/google/uuid"
	"go.uber.org/zap"
)

// Role constants
const (
	RoleViewer = "viewer"
	RoleEditor = "editor"
	RoleAdmin  = "admin"
	RoleOwner  = "owner"
)

// Permission constants
const (
	PermReadProject   = "project:read"
	PermEditProject   = "project:edit"
	PermDeleteProject = "project:delete"
	PermManageTeam    = "team:manage"
	PermViewCost      = "cost:view"
	PermApproveBudget = "budget:approve"
)

// RolePermissions maps roles to their permissions
var RolePermissions = map[string]map[string]bool{
	RoleViewer: {
		PermReadProject: true,
	},
	RoleEditor: {
		PermReadProject: true,
		PermEditProject: true,
		PermViewCost:    true,
	},
	RoleAdmin: {
		PermReadProject:   true,
		PermEditProject:   true,
		PermDeleteProject: true,
		PermManageTeam:    true,
		PermViewCost:      true,
		PermApproveBudget: true,
	},
	RoleOwner: {
		PermReadProject:   true,
		PermEditProject:   true,
		PermDeleteProject: true,
		PermManageTeam:    true,
		PermViewCost:      true,
		PermApproveBudget: true,
	},
}

// RBACMiddleware handles role-based access control
type RBACMiddleware struct {
	db     *database.Postgres
	logger *zap.Logger
}

func NewRBACMiddleware(db *database.Postgres, logger *zap.Logger) *RBACMiddleware {
	return &RBACMiddleware{db: db, logger: logger}
}

// RequireRole checks if the user has the required role (or higher) in the project
// hierarchy: admin > editor > viewer
// RequireRole checks if the user has the required role (or higher) in the project
// hierarchy: owner > admin > editor > viewer
func (m *RBACMiddleware) RequireRole(requiredRole string) gin.HandlerFunc {
	return func(c *gin.Context) {
		m.checkAccess(c, func(userRole string) bool {
			return isRoleAtLeast(userRole, requiredRole)
		})
	}
}

// RequirePermission checks if the user has the specific permission
func (m *RBACMiddleware) RequirePermission(requiredPermission string) gin.HandlerFunc {
	return func(c *gin.Context) {
		m.checkAccess(c, func(userRole string) bool {
			return hasPermission(userRole, requiredPermission)
		})
	}
}

// Helper to centralize role lookup logic
func (m *RBACMiddleware) checkAccess(c *gin.Context, checkFunc func(userRole string) bool) {
	userID, exists := GetUserID(c)
	if !exists {
		c.AbortWithStatusJSON(http.StatusUnauthorized, gin.H{"error": "unauthorized"})
		return
	}

	projectIDStr := c.Param("projectId")
	if projectIDStr == "" {
		c.AbortWithStatusJSON(http.StatusBadRequest, gin.H{"error": "project ID required for access check"})
		return
	}

	projectID, err := uuid.Parse(projectIDStr)
	if err != nil {
		c.AbortWithStatusJSON(http.StatusBadRequest, gin.H{"error": "invalid project ID"})
		return
	}

	var userRole string
	query := `SELECT role FROM project_members WHERE project_id = $1 AND user_id = $2`
	err = m.db.Pool().QueryRow(c.Request.Context(), query, projectID, userID).Scan(&userRole)

	if err == sql.ErrNoRows {
		var ownerID uuid.UUID
		err = m.db.Pool().QueryRow(c.Request.Context(), "SELECT owner_id FROM projects WHERE id = $1", projectID).Scan(&ownerID)
		if err == nil && ownerID == userID {
			userRole = RoleOwner
		} else {
			c.AbortWithStatusJSON(http.StatusForbidden, gin.H{"error": "access denied"})
			return
		}
	} else if err != nil {
		m.logger.Error("failed to check role", zap.Error(err))
		c.AbortWithStatusJSON(http.StatusInternalServerError, gin.H{"error": "internal server error"})
		return
	}

	if !checkFunc(userRole) {
		c.AbortWithStatusJSON(http.StatusForbidden, gin.H{"error": "insufficient permissions"})
		return
	}

	c.Next()
}

func isRoleAtLeast(userRole, requiredRole string) bool {
	roles := map[string]int{
		RoleViewer: 1,
		RoleEditor: 2,
		RoleAdmin:  3,
		RoleOwner:  4,
	}
	return roles[userRole] >= roles[requiredRole]
}

func hasPermission(userRole, requiredPermission string) bool {
	permissions, ok := RolePermissions[userRole]
	if !ok {
		return false
	}
	return permissions[requiredPermission]
}
