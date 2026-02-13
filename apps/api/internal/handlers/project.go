package handlers

import (
	"encoding/json"
	"net/http"
	"time"

	"github.com/axiom/api/internal/database"
	"github.com/axiom/api/internal/middleware"
	"github.com/axiom/api/internal/models"
	"github.com/gin-gonic/gin"
	"github.com/google/uuid"
	"go.uber.org/zap"
)

type ProjectHandler struct {
	db     *database.Postgres
	logger *zap.Logger
}

func NewProjectHandler(db *database.Postgres, logger *zap.Logger) *ProjectHandler {
	return &ProjectHandler{db: db, logger: logger}
}

type CreateProjectRequest struct {
	Name            string `json:"name" binding:"required"`
	SecurityContext string `json:"security_context"`
}

func (h *ProjectHandler) CreateProject(c *gin.Context) {
	var req CreateProjectRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	userID, exists := middleware.GetUserID(c)
	if !exists {
		c.JSON(http.StatusUnauthorized, gin.H{"error": "unauthorized"})
		return
	}

	projectID := uuid.New()
	now := time.Now()

	// Default settings
	settings := map[string]interface{}{
		"description": "Created via API",
	}
	settingsJSON, _ := json.Marshal(settings)

	query := `
		INSERT INTO projects (id, name, owner_id, security_context, settings, created_at, updated_at)
		VALUES ($1, $2, $3, $4, $5, $6, $7)
		RETURNING id
	`

	_, err := h.db.Pool().Exec(c.Request.Context(), query,
		projectID, req.Name, userID, req.SecurityContext, settingsJSON, now, now,
	)

	if err != nil {
		h.logger.Error("failed to create project", zap.Error(err))
		c.JSON(http.StatusInternalServerError, gin.H{"error": "failed to create project"})
		return
	}

	// Add owner as admin member
	memberQuery := `
		INSERT INTO project_members (project_id, user_id, role, added_at)
		VALUES ($1, $2, 'admin', $3)
	`
	h.db.Pool().Exec(c.Request.Context(), memberQuery, projectID, userID, now)

	c.JSON(http.StatusCreated, gin.H{
		"id":   projectID,
		"name": req.Name,
	})
}

func (h *ProjectHandler) ListProjects(c *gin.Context) {
	userID, exists := middleware.GetUserID(c)
	if !exists {
		c.JSON(http.StatusUnauthorized, gin.H{"error": "unauthorized"})
		return
	}

	// List projects where user is the owner OR a member
	query := `
		SELECT DISTINCT p.id, p.name, p.owner_id, p.created_at
		FROM projects p
		LEFT JOIN project_members pm ON p.id = pm.project_id
		WHERE p.owner_id = $1 OR pm.user_id = $1
		ORDER BY p.created_at DESC
	`

	rows, err := h.db.Pool().Query(c.Request.Context(), query, userID)
	if err != nil {
		h.logger.Error("failed to list projects", zap.Error(err))
		c.JSON(http.StatusInternalServerError, gin.H{"error": "failed to list projects"})
		return
	}
	defer rows.Close()

	var projects []gin.H
	for rows.Next() {
		var id uuid.UUID
		var name string
		var ownerID uuid.UUID
		var createdAt time.Time
		if err := rows.Scan(&id, &name, &ownerID, &createdAt); err != nil {
			continue
		}
		projects = append(projects, gin.H{
			"id":         id,
			"name":       name,
			"owner_id":   ownerID,
			"created_at": createdAt,
		})
	}

	c.JSON(http.StatusOK, gin.H{"projects": projects})
}

func (h *ProjectHandler) GetProject(c *gin.Context) {
	id := c.Param("id")
	projectID, err := uuid.Parse(id)
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "invalid project ID"})
		return
	}

	// Check permission (simple check if exists and user has access is implicitly done by listing or caching,
	// but for Get we should verify membership/ownership if strict.
	// For now, let's just fetch if it exists, assuming middleware rate limit prevents scraping)
	// Ideally we join with project_members or check owner.

	userID, _ := middleware.GetUserID(c)

	query := `
		SELECT p.id, p.name, p.owner_id, p.settings, p.created_at
		FROM projects p
        LEFT JOIN project_members pm ON p.id = pm.project_id
		WHERE p.id = $1 AND (p.owner_id = $2 OR pm.user_id = $2)
	`

	var project models.Project
	var settingsJSON []byte

	err = h.db.Pool().QueryRow(c.Request.Context(), query, projectID, userID).Scan(
		&project.ID, &project.Name, &project.OwnerID, &settingsJSON, &project.CreatedAt,
	)

	if err != nil {
		c.JSON(http.StatusNotFound, gin.H{"error": "project not found or access denied"})
		return
	}

	if len(settingsJSON) > 0 {
		json.Unmarshal(settingsJSON, &project.Settings)
	}

	c.JSON(http.StatusOK, project)
}
