package handlers

import (
	"net/http"
	"time"

	"github.com/axiom/api/internal/database"
	"github.com/gin-gonic/gin"
	"github.com/google/uuid"
	"go.uber.org/zap"
)

type TeamHandler struct {
	db     *database.Postgres
	logger *zap.Logger
}

func NewTeamHandler(db *database.Postgres, logger *zap.Logger) *TeamHandler {
	return &TeamHandler{db: db, logger: logger}
}

// AddMemberRequest
type AddMemberRequest struct {
	Email string `json:"email" binding:"required,email"`
	Role  string `json:"role" binding:"required,oneof=viewer editor admin"`
}

// AddMember adds a user to the project
func (h *TeamHandler) AddMember(c *gin.Context) {
	projectID, err := uuid.Parse(c.Param("projectId"))
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "invalid project ID"})
		return
	}

	var req AddMemberRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	// 1. Find user by email
	var userID uuid.UUID
	err = h.db.Pool().QueryRow(c.Request.Context(), "SELECT id FROM users WHERE email = $1", req.Email).Scan(&userID)
	if err != nil {
		c.JSON(http.StatusNotFound, gin.H{"error": "user not found"})
		return
	}

	// 2. Insert into project_members
	query := `
		INSERT INTO project_members (project_id, user_id, role)
		VALUES ($1, $2, $3)
		ON CONFLICT (project_id, user_id) DO UPDATE SET role = $3
	`
	_, err = h.db.Pool().Exec(c.Request.Context(), query, projectID, userID, req.Role)
	if err != nil {
		h.logger.Error("failed to add member", zap.Error(err))
		c.JSON(http.StatusInternalServerError, gin.H{"error": "failed to add member"})
		return
	}

	c.JSON(http.StatusOK, gin.H{"message": "member added"})
}

// RemoveMember removes a user from the project
func (h *TeamHandler) RemoveMember(c *gin.Context) {
	projectID, err := uuid.Parse(c.Param("projectId"))
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "invalid project ID"})
		return
	}

	targetUserID, err := uuid.Parse(c.Param("userId"))
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "invalid user ID"})
		return
	}

	// Make sure we are not removing the owner (TODO: Add check for project owner)

	query := `DELETE FROM project_members WHERE project_id = $1 AND user_id = $2`
	_, err = h.db.Pool().Exec(c.Request.Context(), query, projectID, targetUserID)
	if err != nil {
		h.logger.Error("failed to remove member", zap.Error(err))
		c.JSON(http.StatusInternalServerError, gin.H{"error": "failed to remove member"})
		return
	}

	c.JSON(http.StatusOK, gin.H{"message": "member removed"})
}

// ListMembers lists all members of a project
func (h *TeamHandler) ListMembers(c *gin.Context) {
	projectID, err := uuid.Parse(c.Param("projectId"))
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "invalid project ID"})
		return
	}

	query := `
		SELECT u.id, u.name, u.email, pm.role, pm.added_at
		FROM project_members pm
		JOIN users u ON pm.user_id = u.id
		WHERE pm.project_id = $1
	`

	rows, err := h.db.Pool().Query(c.Request.Context(), query, projectID)
	if err != nil {
		h.logger.Error("failed to list members", zap.Error(err))
		c.JSON(http.StatusInternalServerError, gin.H{"error": "failed to list members"})
		return
	}
	defer rows.Close()

	var members []gin.H
	for rows.Next() {
		var id uuid.UUID
		var name, email, role string
		var addedAt time.Time
		if err := rows.Scan(&id, &name, &email, &role, &addedAt); err != nil {
			continue
		}
		members = append(members, gin.H{
			"id":       id,
			"name":     name,
			"email":    email,
			"role":     role,
			"added_at": addedAt,
		})
	}

	// Also add the owner explicitly if not in members table (though they should be added on creation)
	// For Phase 4 simplification, we assume owner added themselves or query separately.
	// We'll skip complex owner logic for now.

	c.JSON(http.StatusOK, gin.H{"members": members})
}
