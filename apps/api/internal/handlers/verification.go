package handlers

import (
	"bytes"
	"encoding/json"
	"net/http"
	"time"

	"github.com/axiom/api/internal/database"
	"github.com/axiom/api/internal/models"
	"github.com/gin-gonic/gin"
	"github.com/google/uuid"
	"go.uber.org/zap"
)

// VerificationHandler handles verification endpoints
type VerificationHandler struct {
	db           *database.Postgres
	aiServiceURL string
	logger       *zap.Logger
}

// NewVerificationHandler creates a new verification handler
func NewVerificationHandler(db *database.Postgres, aiServiceURL string, logger *zap.Logger) *VerificationHandler {
	return &VerificationHandler{db: db, aiServiceURL: aiServiceURL, logger: logger}
}

// VerifyRequest is the request body for verification
type VerifyRequest struct {
	IVCUID uuid.UUID `json:"ivcu_id" binding:"required"`
	Code   string    `json:"code" binding:"required"`
}

// VerifyResponse is the response for verification
type VerifyResponse struct {
	VerificationID  uuid.UUID                `json:"verification_id"`
	Passed          bool                     `json:"passed"`
	Confidence      float64                  `json:"confidence"`
	VerifierResults []map[string]interface{} `json:"verifier_results"`
	Limitations     []string                 `json:"limitations"`
}

// Verify runs verification on code
func (h *VerificationHandler) Verify(c *gin.Context) {
	var req VerifyRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	startTime := time.Now()

	// Call AI Service
	aiReq := map[string]interface{}{
		"code":      req.Code,
		"language":  "python", // Defaulting to python for now, ideally should come from IVCU
		"run_tier2": true,
	}
	jsonBody, _ := json.Marshal(aiReq)

	resp, err := http.Post(h.aiServiceURL+"/verify", "application/json", bytes.NewBuffer(jsonBody))
	if err != nil {
		h.logger.Error("failed to call AI service for verification", zap.Error(err))
		c.JSON(http.StatusServiceUnavailable, gin.H{"error": "AI service unavailable"})
		return
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		c.JSON(http.StatusBadGateway, gin.H{"error": "AI service verification failed"})
		return
	}

	var aiResult struct {
		Passed          bool                     `json:"passed"`
		Confidence      float64                  `json:"confidence"`
		VerifierResults []map[string]interface{} `json:"verifier_results"`
	}
	if err := json.NewDecoder(resp.Body).Decode(&aiResult); err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "failed to decode AI response"})
		return
	}

	duration := time.Since(startTime)

	// Update IVCU with verification result
	newStatus := models.IVCUStatusVerified
	if !aiResult.Passed {
		newStatus = models.IVCUStatusFailed
	}

	// Store verification result details as JSONB
	resultsJSON, _ := json.Marshal(aiResult.VerifierResults)

	query := `
		UPDATE ivcus 
		SET status = $1, confidence_score = $2, verification_result = $3, updated_at = NOW()
		WHERE id = $4
	`
	_, err = h.db.Pool().Exec(c.Request.Context(), query, newStatus, aiResult.Confidence, resultsJSON, req.IVCUID)
	if err != nil {
		h.logger.Error("failed to update verification result", zap.Error(err))
		c.JSON(http.StatusInternalServerError, gin.H{"error": "failed to store verification result"})
		return
	}

	response := VerifyResponse{
		VerificationID:  uuid.New(),
		Passed:          aiResult.Passed,
		Confidence:      aiResult.Confidence,
		VerifierResults: aiResult.VerifierResults,
		Limitations:     []string{},
	}

	h.logger.Info("verification completed",
		zap.String("ivcu_id", req.IVCUID.String()),
		zap.Bool("passed", aiResult.Passed),
		zap.Float64("confidence", aiResult.Confidence),
		zap.Duration("duration", duration),
	)

	c.JSON(http.StatusOK, response)
}

// GetResult retrieves a verification result
func (h *VerificationHandler) GetResult(c *gin.Context) {
	id := c.Param("id")
	ivcuID, err := uuid.Parse(id)
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "invalid ID"})
		return
	}

	query := `
		SELECT status, confidence_score, verification_result
		FROM ivcus WHERE id = $1
	`

	var status models.IVCUStatus
	var confidence float64
	var verificationJSON []byte

	err = h.db.Pool().QueryRow(c.Request.Context(), query, ivcuID).Scan(&status, &confidence, &verificationJSON)
	if err != nil {
		c.JSON(http.StatusNotFound, gin.H{"error": "IVCU not found"})
		return
	}

	var verifierResults []map[string]interface{}
	if len(verificationJSON) > 0 {
		json.Unmarshal(verificationJSON, &verifierResults)
	}

	c.JSON(http.StatusOK, gin.H{
		"ivcu_id":          ivcuID,
		"status":           status,
		"confidence":       confidence,
		"passed":           status == models.IVCUStatusVerified,
		"verifier_results": verifierResults,
	})
}
