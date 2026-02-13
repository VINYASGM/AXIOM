package handlers

import (
	"context"
	"encoding/json"
	"net/http"
	"time"

	"github.com/axiom/api/internal/database"
	"github.com/axiom/api/internal/economics"
	"github.com/axiom/api/internal/middleware"
	"github.com/axiom/api/internal/models"
	"github.com/gin-gonic/gin"
	"github.com/google/uuid"
	"go.temporal.io/sdk/client"
	"go.uber.org/zap"
)

// GenerationHandler handles code generation endpoints
type GenerationHandler struct {
	db              *database.Postgres
	aiServiceURL    string
	logger          *zap.Logger
	economicService *economics.Service
	temporalClient  client.Client
}

// NewGenerationHandler creates a new generation handler
func NewGenerationHandler(db *database.Postgres, aiServiceURL string, logger *zap.Logger, economicService *economics.Service, temporalClient client.Client) *GenerationHandler {
	return &GenerationHandler{
		db:              db,
		aiServiceURL:    aiServiceURL,
		logger:          logger,
		economicService: economicService,
		temporalClient:  temporalClient,
	}
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
	ctx, span := tracer.Start(c.Request.Context(), "StartGeneration")
	defer span.End()

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

	// Fetch the IVCU and Project ID
	query := `SELECT project_id, raw_intent, contracts, generation_params FROM ivcus WHERE id = $1`
	var projectID uuid.UUID
	var rawIntent string
	var contractsJSON []byte
	var generationParamsJSON []byte

	err := h.db.Pool().QueryRow(ctx, query, req.IVCUID).Scan(&projectID, &rawIntent, &contractsJSON, &generationParamsJSON)
	if err != nil {
		c.JSON(http.StatusNotFound, gin.H{"error": "IVCU not found"})
		return
	}

	// 1. Check Budget
	estimatedCost := 0.05 // Base cost
	if req.CandidateCount > 0 {
		estimatedCost = float64(req.CandidateCount) * 0.02
	}

	budgetStatus, err := h.economicService.CheckBudget(ctx, projectID, estimatedCost)
	if err != nil {
		h.logger.Error("failed to check budget", zap.Error(err))
		// Fail open or closed? Closed for now.
		c.JSON(http.StatusInternalServerError, gin.H{"error": "failed to check budget"})
		return
	}

	if !budgetStatus.Allowed {
		c.JSON(http.StatusPaymentRequired, gin.H{
			"error":   "insufficient budget",
			"details": budgetStatus,
		})
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
	h.db.Pool().Exec(ctx, updateQuery, req.IVCUID)

	// Call AI service to generate code
	go h.generateCode(req.IVCUID, projectID, sdoID, rawIntent, req.Language, userID, req.CandidateCount, req.Strategy, estimatedCost)

	generationID := uuid.New()
	c.JSON(http.StatusAccepted, gin.H{
		"generation_id": generationID,
		"ivcu_id":       req.IVCUID,
		"status":        "generating",
		"message":       "Generation started",
	})
}

// generateCode calls the AI service to generate code (runs async via Temporal)
func (h *GenerationHandler) generateCode(ivcuID uuid.UUID, projectID uuid.UUID, sdoID string, intent string, language string, userID uuid.UUID, candidateCount int, strategy string, estimatedCost float64) {
	startTime := time.Now()

	// Default values
	if candidateCount <= 0 {
		candidateCount = 3
	}
	if strategy == "" {
		strategy = "simple"
	}

	// Prepare Temporal Workflow Input
	input := models.GenerationInput{
		SDOID:          sdoID,
		Intent:         intent,
		Constraints:    []string{}, // Extract constraints if available
		Language:       language,
		CandidateCount: candidateCount,
		ModelTier:      "balanced",
	}

	workflowOptions := client.StartWorkflowOptions{
		ID:        "generation-" + ivcuID.String(),
		TaskQueue: "axiom-task-queue",
	}

	// Use background context for async DB operations
	ctx := context.Background()

	// Check if Temporal is available
	if h.temporalClient == nil {
		h.logger.Error("Temporal client not initialized")
		// Mark IVCU as failed
		query := `UPDATE ivcus SET status = $1, updated_at = NOW() WHERE id = $2`
		h.db.Pool().Exec(ctx, query, models.IVCUStatusFailed, ivcuID)
		return
	}

	// Execute Workflow
	we, err := h.temporalClient.ExecuteWorkflow(ctx, workflowOptions, "CodeGenerationWorkflow", input)

	var code string
	var confidence float64 = 0.0
	var modelID string = "gpt-4"
	status := models.IVCUStatusFailed
	success := false
	actualCost := 0.0

	if err != nil {
		h.logger.Error("failed to start workflow", zap.Error(err))
	} else {
		// Wait for result (in this goroutine)
		var output models.GenerationOutput
		err = we.Get(ctx, &output)

		if err == nil {
			success = true
			code = output.SelectedCode
			status = models.IVCUStatusVerified // Workflows include verification
			actualCost = output.TotalCost
			// Confidence?
			confidence = 0.95 // Placeholder or extract from output
		} else {
			h.logger.Error("workflow execution failed", zap.Error(err))
		}
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

	// Record actual usage
	if !success {
		actualCost = estimatedCost * 0.1 // Small charge for failure handling?
	}

	err = h.economicService.RecordUsage(ctx, projectID, userID, actualCost, "code_generation", map[string]interface{}{
		"ivcu_id":     ivcuID,
		"tokens_in":   len(intent),
		"tokens_out":  len(code),
		"strategy":    strategy,
		"workflow_id": we.GetID(),
		"run_id":      we.GetRunID(),
	})
	if err != nil {
		h.logger.Error("failed to record usage", zap.Error(err))
	}

	// Log generation
	logQuery := `
		INSERT INTO generation_logs (id, ivcu_id, model_id, tokens_in, tokens_out, latency_ms, cost, created_at)
		VALUES ($1, $2, $3, $4, $5, $6, $7, NOW())
	`
	h.db.Pool().Exec(ctx, logQuery, uuid.New(), ivcuID, modelID, len(intent), len(code), latency, actualCost)

	h.logger.Info("generation completed",
		zap.String("ivcu_id", ivcuID.String()),
		zap.String("status", string(status)),
		zap.Int64("latency_ms", latency),
		zap.String("workflow_id", we.GetID()),
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

		// Query Temporal for more details
		if h.temporalClient != nil {
			workflowID := "generation-" + ivcuID.String()
			desc, err := h.temporalClient.DescribeWorkflowExecution(c.Request.Context(), workflowID, "")
			if err == nil && desc.WorkflowExecutionInfo != nil {
				// Map Temporal status (Running, Completed, Failed, etc.)
				// We can also look at PendingActivities if we want deep details
				if desc.WorkflowExecutionInfo.Status.String() == "WORKFLOW_EXECUTION_STATUS_RUNNING" {
					stage = "processing_workflow"
					if len(desc.PendingActivities) > 0 {
						stage = "activity:" + desc.PendingActivities[0].ActivityType.Name
					}
				}
			}
		}

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
