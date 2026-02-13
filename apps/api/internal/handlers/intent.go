package handlers

import (
	"bytes"
	"encoding/json"
	"io"
	"net/http"
	"time"

	"github.com/axiom/api/internal/database"
	"github.com/axiom/api/internal/middleware"
	"github.com/axiom/api/internal/models"
	"github.com/gin-gonic/gin"
	"github.com/google/uuid"
	"go.opentelemetry.io/otel"
	"go.uber.org/zap"
)

var tracer = otel.Tracer("github.com/axiom/api/internal/handlers")

// IntentHandler handles intent-related endpoints
type IntentHandler struct {
	db           *database.Postgres
	aiServiceURL string
	logger       *zap.Logger
}

// NewIntentHandler creates a new intent handler
func NewIntentHandler(db *database.Postgres, aiServiceURL string, logger *zap.Logger) *IntentHandler {
	return &IntentHandler{db: db, aiServiceURL: aiServiceURL, logger: logger}
}

// ParseIntentRequest is the request body for parsing intent
type ParseIntentRequest struct {
	RawIntent      string `json:"raw_intent" binding:"required"`
	ProjectContext string `json:"project_context,omitempty"`
}

// ParseIntentResponse is the response for parsed intent
type ParseIntentResponse struct {
	ParsedIntent         map[string]interface{} `json:"parsed_intent"`
	Confidence           float64                `json:"confidence"`
	SuggestedRefinements []string               `json:"suggested_refinements"`
	ExtractedConstraints []string               `json:"extracted_constraints"`
	SDOID                string                 `json:"sdo_id"`
}

// CreateIVCURequest is the request body for creating an IVCU
type CreateIVCURequest struct {
	ProjectID uuid.UUID         `json:"project_id" binding:"required"`
	RawIntent string            `json:"raw_intent" binding:"required"`
	Contracts []models.Contract `json:"contracts"`
	SDOID     string            `json:"sdo_id"` // Optional, from ParseIntent
}

// ParseIntent parses raw intent into structured format
func (h *IntentHandler) ParseIntent(c *gin.Context) {
	ctx, span := tracer.Start(c.Request.Context(), "ParseIntent")
	defer span.End()

	var req ParseIntentRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	// Call AI Service
	reqBody := map[string]interface{}{
		"intent":  req.RawIntent,
		"context": req.ProjectContext,
	}
	jsonBody, _ := json.Marshal(reqBody)

	// Create request with context to propagate trace context
	aiReq, err := http.NewRequestWithContext(ctx, "POST", h.aiServiceURL+"/parse-intent", bytes.NewBuffer(jsonBody))
	if err != nil {
		h.logger.Error("failed to create request", zap.Error(err))
		c.JSON(http.StatusInternalServerError, gin.H{"error": "internal server error"})
		return
	}
	aiReq.Header.Set("Content-Type", "application/json")

	resp, err := http.DefaultClient.Do(aiReq)
	if err != nil {
		h.logger.Error("failed to call AI service", zap.Error(err))
		c.JSON(http.StatusServiceUnavailable, gin.H{"error": "AI service unavailable"})
		return
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		c.JSON(http.StatusBadGateway, gin.H{"error": "AI service returned error"})
		return
	}

	var parsed ParseIntentResponse
	if err := json.NewDecoder(resp.Body).Decode(&parsed); err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "failed to decode AI response"})
		return
	}

	c.JSON(http.StatusOK, parsed)
}

// CreateIVCU creates a new Intent-Verified Code Unit
func (h *IntentHandler) CreateIVCU(c *gin.Context) {
	ctx, span := tracer.Start(c.Request.Context(), "CreateIVCU")
	defer span.End()

	var req CreateIVCURequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	userID, exists := middleware.GetUserID(c)
	if !exists {
		c.JSON(http.StatusUnauthorized, gin.H{"error": "unauthorized"})
		return
	}

	// Create IVCU
	ivcu := models.IVCU{
		ID:              uuid.New(),
		ProjectID:       req.ProjectID,
		Version:         1,
		RawIntent:       req.RawIntent,
		Contracts:       req.Contracts,
		Status:          models.IVCUStatusDraft,
		ConfidenceScore: 0,
		CreatedAt:       time.Now(),
		UpdatedAt:       time.Now(),
		CreatedBy:       userID,
		GenerationParams: map[string]interface{}{
			"sdo_id": req.SDOID,
		},
	}

	// Convert contracts and params to JSON
	contractsJSON, _ := json.Marshal(ivcu.Contracts)
	paramsJSON, _ := json.Marshal(ivcu.GenerationParams)

	query := `
		INSERT INTO ivcus (id, project_id, version, raw_intent, contracts, status, confidence_score, created_at, updated_at, created_by, generation_params)
		VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
	`

	_, err := h.db.Pool().Exec(ctx, query,
		ivcu.ID, ivcu.ProjectID, ivcu.Version, ivcu.RawIntent, contractsJSON,
		ivcu.Status, ivcu.ConfidenceScore, ivcu.CreatedAt, ivcu.UpdatedAt, ivcu.CreatedBy, paramsJSON,
	)

	if err != nil {
		h.logger.Error("failed to create IVCU", zap.Error(err))
		c.JSON(http.StatusInternalServerError, gin.H{"error": "failed to create IVCU"})
		return
	}

	c.JSON(http.StatusCreated, gin.H{
		"ivcu_id": ivcu.ID,
		"status":  ivcu.Status,
	})
}

// GetIVCU retrieves an IVCU by ID
func (h *IntentHandler) GetIVCU(c *gin.Context) {
	id := c.Param("id")
	ivcuID, err := uuid.Parse(id)
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "invalid IVCU ID"})
		return
	}

	query := `
		SELECT id, project_id, version, raw_intent, parsed_intent, contracts,
		       verification_result, confidence_score, code, language,
		       model_id, model_version, status, created_at, updated_at, created_by
		FROM ivcus WHERE id = $1
	`

	var ivcu models.IVCU
	var parsedIntentJSON, contractsJSON, verificationJSON []byte
	var code, language, modelID, modelVersion *string

	err = h.db.Pool().QueryRow(c.Request.Context(), query, ivcuID).Scan(
		&ivcu.ID, &ivcu.ProjectID, &ivcu.Version, &ivcu.RawIntent,
		&parsedIntentJSON, &contractsJSON, &verificationJSON,
		&ivcu.ConfidenceScore, &code, &language,
		&modelID, &modelVersion, &ivcu.Status, &ivcu.CreatedAt, &ivcu.UpdatedAt, &ivcu.CreatedBy,
	)

	if err != nil {
		c.JSON(http.StatusNotFound, gin.H{"error": "IVCU not found"})
		return
	}

	// Parse JSON fields
	if len(parsedIntentJSON) > 0 {
		json.Unmarshal(parsedIntentJSON, &ivcu.ParsedIntent)
	}
	if len(contractsJSON) > 0 {
		json.Unmarshal(contractsJSON, &ivcu.Contracts)
	}
	if code != nil {
		ivcu.Code = *code
	}
	if language != nil {
		ivcu.Language = *language
	}
	if modelID != nil {
		ivcu.ModelID = *modelID
	}
	if modelVersion != nil {
		ivcu.ModelVersion = *modelVersion
	}

	c.JSON(http.StatusOK, ivcu)
}

// UpdateIVCU updates an existing IVCU
func (h *IntentHandler) UpdateIVCU(c *gin.Context) {
	id := c.Param("id")
	ivcuID, err := uuid.Parse(id)
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "invalid IVCU ID"})
		return
	}

	var req struct {
		RawIntent string            `json:"raw_intent"`
		Contracts []models.Contract `json:"contracts"`
	}

	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	contractsJSON, _ := json.Marshal(req.Contracts)

	query := `
		UPDATE ivcus 
		SET raw_intent = COALESCE(NULLIF($1, ''), raw_intent),
		    contracts = $2,
		    version = version + 1,
		    updated_at = NOW()
		WHERE id = $3
		RETURNING version
	`

	var newVersion int
	err = h.db.Pool().QueryRow(c.Request.Context(), query, req.RawIntent, contractsJSON, ivcuID).Scan(&newVersion)

	if err != nil {
		c.JSON(http.StatusNotFound, gin.H{"error": "IVCU not found"})
		return
	}

	c.JSON(http.StatusOK, gin.H{
		"ivcu_id":               ivcuID,
		"version":               newVersion,
		"regeneration_required": true,
	})
}

// DeleteIVCU deletes an IVCU
func (h *IntentHandler) DeleteIVCU(c *gin.Context) {
	id := c.Param("id")
	ivcuID, err := uuid.Parse(id)
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "invalid IVCU ID"})
		return
	}

	query := `DELETE FROM ivcus WHERE id = $1`
	result, err := h.db.Pool().Exec(c.Request.Context(), query, ivcuID)

	if err != nil || result.RowsAffected() == 0 {
		c.JSON(http.StatusNotFound, gin.H{"error": "IVCU not found"})
		return
	}

	c.JSON(http.StatusOK, gin.H{"deleted": true})
}

// ListProjectIVCUs lists all IVCUs for a project
func (h *IntentHandler) ListProjectIVCUs(c *gin.Context) {
	projectID := c.Param("projectId")
	pID, err := uuid.Parse(projectID)
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "invalid project ID"})
		return
	}

	query := `
		SELECT id, version, raw_intent, status, confidence_score, created_at
		FROM ivcus 
		WHERE project_id = $1
		ORDER BY created_at DESC
	`

	rows, err := h.db.Pool().Query(c.Request.Context(), query, pID)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "failed to fetch IVCUs"})
		return
	}
	defer rows.Close()

	var ivcus []gin.H
	for rows.Next() {
		var id uuid.UUID
		var version int
		var rawIntent string
		var status models.IVCUStatus
		var confidence float64
		var createdAt time.Time

		rows.Scan(&id, &version, &rawIntent, &status, &confidence, &createdAt)

		ivcus = append(ivcus, gin.H{
			"id":         id,
			"version":    version,
			"raw_intent": rawIntent,
			"status":     status,
			"confidence": confidence,
			"created_at": createdAt,
		})
	}

	c.JSON(http.StatusOK, gin.H{"ivcus": ivcus})
}

// GetGraph retrieves the SDE graph (nodes and edges)
func (h *IntentHandler) GetGraph(c *gin.Context) {
	// Proxy to AI Service which holds the SDO graph source of truth
	resp, err := http.Get(h.aiServiceURL + "/api/v1/graph")
	if err != nil {
		h.logger.Error("failed to call AI service", zap.Error(err))
		c.JSON(http.StatusServiceUnavailable, gin.H{"error": "AI service unavailable"})
		return
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		c.JSON(http.StatusBadGateway, gin.H{"error": "AI service returned error"})
		return
	}

	// Stream response back
	c.Header("Content-Type", "application/json")
	c.Status(http.StatusOK)
	_, _ = io.Copy(c.Writer, resp.Body)
}

// Unused import workaround
var _ = bytes.Buffer{}
var _ = io.Copy
