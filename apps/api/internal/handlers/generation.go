package handlers

import (
	"bytes"
	"context"
	"encoding/json"
	"io"
	"net/http"
	"time"

	"github.com/axiom/api/internal/database"
	"github.com/axiom/api/internal/middleware"
	"github.com/axiom/api/internal/models"
	"github.com/gin-gonic/gin"
	"github.com/google/uuid"
	"go.uber.org/zap"
)

// GenerationHandler handles code generation endpoints
type GenerationHandler struct {
	db           *database.Postgres
	aiServiceURL string
	logger       *zap.Logger
}

// NewGenerationHandler creates a new generation handler
func NewGenerationHandler(db *database.Postgres, aiServiceURL string, logger *zap.Logger) *GenerationHandler {
	return &GenerationHandler{db: db, aiServiceURL: aiServiceURL, logger: logger}
}

// StartGenerationRequest is the request body for starting generation
type StartGenerationRequest struct {
	IVCUID         uuid.UUID `json:"ivcu_id" binding:"required"`
	Language       string    `json:"language" binding:"required"`
	CandidateCount int       `json:"candidate_count"`
	Strategy       string    `json:"strategy"` // "simple", "parallel", "adaptive"
}

// GenerationStatus represents the status of a generation
type GenerationStatus struct {
	ID        uuid.UUID `json:"id"`
	IVCUID    uuid.UUID `json:"ivcu_id"`
	Status    string    `json:"status"`
	Progress  float64   `json:"progress"`
	Stage     string    `json:"stage"`
	StartedAt time.Time `json:"started_at"`
}

// StartGeneration initiates code generation for an IVCU
func (h *GenerationHandler) StartGeneration(c *gin.Context) {
	var req StartGenerationRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	userID, exists := middleware.GetUserID(c)
	if !exists {
		c.JSON(http.StatusUnauthorized, gin.H{"error": "unauthorized"})
		return
	}

	// Fetch the IVCU
	query := `SELECT raw_intent, contracts, generation_params FROM ivcus WHERE id = $1`
	var rawIntent string
	var contractsJSON []byte
	var generationParamsJSON []byte

	err := h.db.Pool().QueryRow(c.Request.Context(), query, req.IVCUID).Scan(&rawIntent, &contractsJSON, &generationParamsJSON)
	if err != nil {
		c.JSON(http.StatusNotFound, gin.H{"error": "IVCU not found"})
		return
	}

	var sdoID string
	if len(generationParamsJSON) > 0 {
		var params map[string]interface{}
		if err := json.Unmarshal(generationParamsJSON, &params); err == nil {
			if id, ok := params["sdo_id"].(string); ok {
				sdoID = id
			}
		}
	}

	// Update IVCU status to generating
	updateQuery := `UPDATE ivcus SET status = 'generating', updated_at = NOW() WHERE id = $1`
	h.db.Pool().Exec(c.Request.Context(), updateQuery, req.IVCUID)

	// Call AI service to generate code
	go h.generateCode(req.IVCUID, sdoID, rawIntent, req.Language, userID, req.CandidateCount, req.Strategy)

	generationID := uuid.New()
	c.JSON(http.StatusAccepted, gin.H{
		"generation_id": generationID,
		"ivcu_id":       req.IVCUID,
		"status":        "generating",
		"message":       "Generation started",
	})
}

// generateCode calls the AI service to generate code (runs async)
func (h *GenerationHandler) generateCode(ivcuID uuid.UUID, sdoID string, intent string, language string, userID uuid.UUID, candidateCount int, strategy string) {
	startTime := time.Now()

	// Default values
	if candidateCount <= 0 {
		candidateCount = 3
	}
	if strategy == "" {
		strategy = "simple"
	}

	// Determine endpoint and body based on strategy
	endpoint := "/generate"
	reqBody := map[string]interface{}{
		"sdo_id":   sdoID,
		"intent":   intent,
		"language": language,
	}

	if strategy == "parallel" || strategy == "adaptive" {
		endpoint = "/generate/parallel"
		if strategy == "adaptive" {
			endpoint = "/generate/adaptive"
			reqBody["early_stop_threshold"] = 0.9
		} else {
			reqBody["candidate_count"] = candidateCount
		}
	}

	jsonBody, _ := json.Marshal(reqBody)

	// Call AI service
	resp, err := http.Post(h.aiServiceURL+endpoint, "application/json", bytes.NewBuffer(jsonBody))

	var code string
	var confidence float64 = 0.0
	var modelID string = "gpt-4"
	status := models.IVCUStatusFailed
	// var verificationResult []byte

	// Use background context for async DB operations
	ctx := context.Background()

	if err == nil && resp.StatusCode == http.StatusOK {
		defer resp.Body.Close()
		body, _ := io.ReadAll(resp.Body)

		if strategy == "simple" {
			var result struct {
				Code       string  `json:"code"`
				Confidence float64 `json:"confidence"`
				ModelID    string  `json:"model_id"`
			}
			if json.Unmarshal(body, &result) == nil {
				code = result.Code
				confidence = result.Confidence
				modelID = result.ModelID
				status = models.IVCUStatusVerifying
			}
		} else {
			// Handle complex response for parallel/adaptive
			var result struct {
				SelectedCode string  `json:"selected_code"`
				Confidence   float64 `json:"confidence"`
				Status       string  `json:"status"`
			}
			if json.Unmarshal(body, &result) == nil {
				code = result.SelectedCode
				confidence = result.Confidence
				status = models.IVCUStatusVerified // Usually parallel returns verified result
				if result.Status != "verified" {
					status = models.IVCUStatusVerifying // Or back to verifying if not fully done
				}
			}
		}
	} else {
		h.logger.Error("AI generation failed", zap.Error(err))
	}

	latency := time.Since(startTime).Milliseconds()

	// Update IVCU with generated code
	query := `
		UPDATE ivcus
		SET code = $1, language = $2, confidence_score = $3, model_id = $4,
		    status = $5, updated_at = NOW()
		WHERE id = $6
	`
	h.db.Pool().Exec(ctx, query, code, language, confidence, modelID, status, ivcuID)

	// Log generation
	logQuery := `
		INSERT INTO generation_logs (id, ivcu_id, model_id, tokens_in, tokens_out, latency_ms, cost, created_at)
		VALUES ($1, $2, $3, $4, $5, $6, $7, NOW())
	`
	h.db.Pool().Exec(ctx, logQuery, uuid.New(), ivcuID, modelID, len(intent), len(code), latency, 0.01)

	h.logger.Info("generation completed",
		zap.String("ivcu_id", ivcuID.String()),
		zap.String("status", string(status)),
		zap.Int64("latency_ms", latency),
		zap.String("strategy", strategy),
	)
}

// GetGenerationStatus returns the status of a generation
func (h *GenerationHandler) GetGenerationStatus(c *gin.Context) {
	id := c.Param("id")
	ivcuID, err := uuid.Parse(id)
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "invalid ID"})
		return
	}

	// Get IVCU status
	query := `SELECT status, confidence_score, updated_at FROM ivcus WHERE id = $1`
	var status models.IVCUStatus
	var confidence float64
	var updatedAt time.Time

	err = h.db.Pool().QueryRow(c.Request.Context(), query, ivcuID).Scan(&status, &confidence, &updatedAt)
	if err != nil {
		c.JSON(http.StatusNotFound, gin.H{"error": "IVCU not found"})
		return
	}

	progress := 0.0
	stage := "queued"

	switch status {
	case models.IVCUStatusGenerating:
		progress = 0.5
		stage = "generating"
	case models.IVCUStatusVerifying:
		progress = 0.75
		stage = "verifying"
	case models.IVCUStatusVerified:
		progress = 1.0
		stage = "completed"
	case models.IVCUStatusFailed:
		progress = 1.0
		stage = "failed"
	}

	c.JSON(http.StatusOK, gin.H{
		"ivcu_id":    ivcuID,
		"status":     status,
		"progress":   progress,
		"stage":      stage,
		"confidence": confidence,
		"updated_at": updatedAt,
	})
}

// CancelGeneration cancels an ongoing generation
func (h *GenerationHandler) CancelGeneration(c *gin.Context) {
	id := c.Param("id")
	ivcuID, err := uuid.Parse(id)
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "invalid ID"})
		return
	}

	// Update status to failed (cancelled)
	query := `UPDATE ivcus SET status = 'failed', updated_at = NOW() WHERE id = $1 AND status = 'generating'`
	result, _ := h.db.Pool().Exec(c.Request.Context(), query, ivcuID)

	if result.RowsAffected() == 0 {
		c.JSON(http.StatusNotFound, gin.H{"error": "no active generation found"})
		return
	}

	c.JSON(http.StatusOK, gin.H{"cancelled": true})
}
