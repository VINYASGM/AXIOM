package handlers

import (
	"context"
	"net/http"
	"time"

	"github.com/axiom/api/internal/database"
	"github.com/gin-gonic/gin"
)

// HealthHandler handles health check endpoints
type HealthHandler struct {
	db           *database.Postgres
	redis        *database.Redis
	aiServiceURL string
}

// NewHealthHandler creates a new health handler
func NewHealthHandler(db *database.Postgres, redis *database.Redis, aiServiceURL string) *HealthHandler {
	return &HealthHandler{
		db:           db,
		redis:        redis,
		aiServiceURL: aiServiceURL,
	}
}

// HealthResponse represents the health check response
type HealthResponse struct {
	Status       string            `json:"status"`
	Service      string            `json:"service"`
	Version      string            `json:"version"`
	Dependencies map[string]string `json:"dependencies"`
}

// Health returns basic health status
func (h *HealthHandler) Health(c *gin.Context) {
	c.JSON(http.StatusOK, gin.H{
		"status":  "healthy",
		"service": "axiom-api",
		"version": "0.1.0",
	})
}

// DeepHealth returns health status with dependency checks
func (h *HealthHandler) DeepHealth(c *gin.Context) {
	ctx, cancel := context.WithTimeout(c.Request.Context(), 5*time.Second)
	defer cancel()

	deps := make(map[string]string)
	allHealthy := true

	// Check PostgreSQL
	if h.db != nil {
		if err := h.db.Pool().Ping(ctx); err != nil {
			deps["database"] = "unhealthy: " + err.Error()
			allHealthy = false
		} else {
			deps["database"] = "healthy"
		}
	} else {
		deps["database"] = "not configured"
	}

	// Check Redis
	if h.redis != nil {
		if err := h.redis.Ping(ctx); err != nil {
			deps["redis"] = "unhealthy: " + err.Error()
			allHealthy = false
		} else {
			deps["redis"] = "healthy"
		}
	} else {
		deps["redis"] = "not configured"
	}

	// Check AI Service
	if h.aiServiceURL != "" {
		aiHealthy := h.checkAIService(ctx)
		if aiHealthy {
			deps["ai_service"] = "healthy"
		} else {
			deps["ai_service"] = "unhealthy"
			allHealthy = false
		}
	} else {
		deps["ai_service"] = "not configured"
	}

	status := "healthy"
	httpStatus := http.StatusOK
	if !allHealthy {
		status = "degraded"
		httpStatus = http.StatusServiceUnavailable
	}

	c.JSON(httpStatus, HealthResponse{
		Status:       status,
		Service:      "axiom-api",
		Version:      "0.1.0",
		Dependencies: deps,
	})
}

func (h *HealthHandler) checkAIService(ctx context.Context) bool {
	client := &http.Client{Timeout: 3 * time.Second}
	req, err := http.NewRequestWithContext(ctx, http.MethodGet, h.aiServiceURL+"/health", nil)
	if err != nil {
		return false
	}

	resp, err := client.Do(req)
	if err != nil {
		return false
	}
	defer resp.Body.Close()

	return resp.StatusCode == http.StatusOK
}
