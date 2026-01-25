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
)

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
func (m *RBACMiddleware) RequireRole(requiredRole string) gin.HandlerFunc {
	return func(c *gin.Context) {
		userID, exists := GetUserID(c)
		if !exists {
			c.AbortWithStatusJSON(http.StatusUnauthorized, gin.H{"error": "unauthorized"})
			return
		}

		// Try to get Project ID from Param, then Query, then Body (if needed, but usually Param)
		projectIDStr := c.Param("projectId")
		if projectIDStr == "" {
			// If not in param, check if we have an IVCU ID and resolve project from that
			// This covers /ivcu/:id routes
			// For now, let's strictly require projectId param for project-scoped routes
			c.AbortWithStatusJSON(http.StatusBadRequest, gin.H{"error": "project ID required for access check"})
			return
		}

		projectID, err := uuid.Parse(projectIDStr)
		if err != nil {
			c.AbortWithStatusJSON(http.StatusBadRequest, gin.H{"error": "invalid project ID"})
			return
		}

		// Check role in DB
		// Note: Owners are implicit admins. We should check if user is owner of project or org too.
		// For simplicity in Phase 4, we check project_members and strict ownership.

		var userRole string
		query := `
			SELECT role FROM project_members 
			WHERE project_id = $1 AND user_id = $2
		`
		err = m.db.Pool().QueryRow(c.Request.Context(), query, projectID, userID).Scan(&userRole)

		if err == sql.ErrNoRows {
			// Check if is owner of project (fallback)
			var ownerID uuid.UUID
			err = m.db.Pool().QueryRow(c.Request.Context(), "SELECT owner_id FROM projects WHERE id = $1", projectID).Scan(&ownerID)
			if err == nil && ownerID == userID {
				userRole = RoleAdmin // Owner is implicit admin
			} else {
				c.AbortWithStatusJSON(http.StatusForbidden, gin.H{"error": "access denied"})
				return
			}
		} else if err != nil {
			m.logger.Error("failed to check role", zap.Error(err))
			c.AbortWithStatusJSON(http.StatusInternalServerError, gin.H{"error": "internal server error"})
			return
		}

		if !hasPermission(userRole, requiredRole) {
			c.AbortWithStatusJSON(http.StatusForbidden, gin.H{"error": "insufficient permissions"})
			return
		}

		c.Next()
	}
}

func hasPermission(userRole, requiredRole string) bool {
	roles := map[string]int{
		RoleViewer: 1,
		RoleEditor: 2,
		RoleAdmin:  3,
	}

	return roles[userRole] >= roles[requiredRole]
}
