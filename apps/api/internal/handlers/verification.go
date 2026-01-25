package handlers

import (
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
	db     *database.Postgres
	logger *zap.Logger
}

// NewVerificationHandler creates a new verification handler
func NewVerificationHandler(db *database.Postgres, logger *zap.Logger) *VerificationHandler {
	return &VerificationHandler{db: db, logger: logger}
}

// VerifyRequest is the request body for verification
type VerifyRequest struct {
	IVCUID uuid.UUID `json:"ivcu_id" binding:"required"`
	Code   string    `json:"code" binding:"required"`
}

// VerifyResponse is the response for verification
type VerifyResponse struct {
	VerificationID  uuid.UUID               `json:"verification_id"`
	Passed          bool                    `json:"passed"`
	Confidence      float64                 `json:"confidence"`
	VerifierResults []models.VerifierResult `json:"verifier_results"`
	Limitations     []string                `json:"limitations"`
}

// Verify runs verification on code
func (h *VerificationHandler) Verify(c *gin.Context) {
	var req VerifyRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	startTime := time.Now()

	// Run Tier 1 verifiers (fast, <2s)
	results := []models.VerifierResult{
		h.runSyntaxChecker(req.Code),
		h.runTypeChecker(req.Code),
		h.runLinter(req.Code),
	}

	// Calculate overall confidence
	totalConfidence := 0.0
	allPassed := true
	for _, r := range results {
		totalConfidence += r.Confidence
		if !r.Passed {
			allPassed = false
		}
	}
	avgConfidence := totalConfidence / float64(len(results))

	duration := time.Since(startTime)

	// Update IVCU with verification result
	newStatus := models.IVCUStatusVerified
	if !allPassed {
		newStatus = models.IVCUStatusFailed
	}

	query := `
		UPDATE ivcus 
		SET status = $1, confidence_score = $2, updated_at = NOW()
		WHERE id = $3
	`
	h.db.Pool().Exec(c.Request.Context(), query, newStatus, avgConfidence, req.IVCUID)

	response := VerifyResponse{
		VerificationID:  uuid.New(),
		Passed:          allPassed,
		Confidence:      avgConfidence,
		VerifierResults: results,
		Limitations: []string{
			"Only Tier 1 verifiers run (syntax, types, lint)",
			"Deep verification (SMT, fuzz) not yet implemented",
		},
	}

	h.logger.Info("verification completed",
		zap.String("ivcu_id", req.IVCUID.String()),
		zap.Bool("passed", allPassed),
		zap.Float64("confidence", avgConfidence),
		zap.Duration("duration", duration),
	)

	c.JSON(http.StatusOK, response)
}

// runSyntaxChecker performs basic syntax validation
func (h *VerificationHandler) runSyntaxChecker(code string) models.VerifierResult {
	start := time.Now()

	// Simple syntax check - in production would use language-specific parsers
	passed := len(code) > 0 && code[len(code)-1] != '{'

	return models.VerifierResult{
		Name:       "syntax_checker",
		Tier:       1,
		Passed:     passed,
		Confidence: 0.95,
		Messages:   []string{},
		Duration:   time.Since(start).Milliseconds(),
	}
}

// runTypeChecker performs type analysis
func (h *VerificationHandler) runTypeChecker(code string) models.VerifierResult {
	start := time.Now()

	// Placeholder - in production would use type inference
	return models.VerifierResult{
		Name:       "type_checker",
		Tier:       1,
		Passed:     true,
		Confidence: 0.80,
		Messages:   []string{"Type checking passed (placeholder)"},
		Duration:   time.Since(start).Milliseconds(),
	}
}

// runLinter performs style and pattern checks
func (h *VerificationHandler) runLinter(code string) models.VerifierResult {
	start := time.Now()

	messages := []string{}
	confidence := 1.0

	// Basic checks
	if len(code) > 1000 {
		messages = append(messages, "Consider breaking into smaller functions")
		confidence -= 0.1
	}

	return models.VerifierResult{
		Name:       "linter",
		Tier:       1,
		Passed:     true,
		Confidence: confidence,
		Messages:   messages,
		Duration:   time.Since(start).Milliseconds(),
	}
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

	c.JSON(http.StatusOK, gin.H{
		"ivcu_id":    ivcuID,
		"status":     status,
		"confidence": confidence,
		"passed":     status == models.IVCUStatusVerified,
	})
}
