package handlers

import (
	"encoding/json"
	"net/http"
	"time"

	"github.com/axiom/api/internal/database"
	"github.com/axiom/api/internal/models"
	"github.com/axiom/api/internal/verification"
	"github.com/axiom/api/internal/verifier"
	"github.com/gin-gonic/gin"
	"github.com/google/uuid"
	"go.uber.org/zap"
)

// VerificationHandler handles verification endpoints
type VerificationHandler struct {
	db                 *database.Postgres
	aiServiceURL       string
	verifierClient     verifier.Client
	certificateService *verification.CertificateService
	logger             *zap.Logger
}

// NewVerificationHandler creates a new verification handler
func NewVerificationHandler(db *database.Postgres, aiServiceURL string, verifierClient verifier.Client, certificateService *verification.CertificateService, logger *zap.Logger) *VerificationHandler {
	return &VerificationHandler{
		db:                 db,
		aiServiceURL:       aiServiceURL,
		verifierClient:     verifierClient,
		certificateService: certificateService,
		logger:             logger,
	}
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

	// Call Verifier Service (Rust)
	passed, confidence, err := h.verifierClient.Verify(c.Request.Context(), req.Code, "python")
	if err != nil {
		h.logger.Error("failed to call Verifier service", zap.Error(err))
		c.JSON(http.StatusServiceUnavailable, gin.H{"error": "Verifier service unavailable"})
		return
	}

	// Construct Result (Simplified for integration check)
	aiResult := struct {
		Passed          bool                     `json:"passed"`
		Confidence      float64                  `json:"confidence"`
		VerifierResults []map[string]interface{} `json:"verifier_results"`
	}{
		Passed:     passed,
		Confidence: confidence,
		VerifierResults: []map[string]interface{}{
			{"name": "rust_verifier", "passed": passed, "score": confidence},
		},
	}

	duration := time.Since(startTime)

	// Update IVCU with verification result
	newStatus := models.IVCUStatusVerified
	if !aiResult.Passed {
		newStatus = models.IVCUStatusFailed
	}

	// Store verification result details as JSONB
	resultsJSON, _ := json.Marshal(aiResult.VerifierResults)

	// Transaction to update IVCU and insert Certificate
	tx, err := h.db.Pool().Begin(c.Request.Context())
	if err != nil {
		h.logger.Error("failed to begin transaction", zap.Error(err))
		c.JSON(http.StatusInternalServerError, gin.H{"error": "internal server error"})
		return
	}
	defer tx.Rollback(c.Request.Context())

	// 1. Update IVCU
	query := `
		UPDATE ivcus 
		SET status = $1, confidence_score = $2, verification_result = $3, updated_at = NOW()
		WHERE id = $4
	`
	_, err = tx.Exec(c.Request.Context(), query, newStatus, aiResult.Confidence, resultsJSON, req.IVCUID)
	if err != nil {
		h.logger.Error("failed to update verification result", zap.Error(err))
		c.JSON(http.StatusInternalServerError, gin.H{"error": "failed to store verification result"})
		return
	}

	// 2. Generate and Insert Proof Certificate (only if passed)
	var proofCertID *uuid.UUID
	if aiResult.Passed {
		// Mock intent ID for now - in real implementation, we fetch it from IVCU
		intentID := uuid.Nil

		// Convert generic verifier results to models.VerifierResult
		var modelResults []models.VerifierResult
		for _, r := range aiResult.VerifierResults {
			modelResults = append(modelResults, models.VerifierResult{
				Name:       r["name"].(string),
				Passed:     r["passed"].(bool),
				Confidence: r["score"].(float64),
				// Tier, Messages, Duration would be populated here
			})
		}

		cert, err := h.certificateService.GenerateCertificate(
			c.Request.Context(),
			req.IVCUID,
			intentID,
			req.Code,
			models.ProofTypeContractCompliance, // Default type for now
			modelResults,
		)
		if err != nil {
			h.logger.Error("failed to generate certificate", zap.Error(err))
			// Decide if this should fail the request or just log. Failing for strictness.
			c.JSON(http.StatusInternalServerError, gin.H{"error": "failed to generate proof certificate"})
			return
		}

		proofCertID = &cert.ID

		certQuery := `
			INSERT INTO proof_certificates (
				id, ivcu_id, proof_type, verifier_version, timestamp, intent_id,
				ast_hash, code_hash, verifier_signatures, assertions, proof_data,
				hash_chain, signature, created_at
			) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14)
		`

		verifierSigsJSON, _ := json.Marshal(cert.VerifierSignatures)
		assertionsJSON, _ := json.Marshal(cert.Assertions)

		_, err = tx.Exec(c.Request.Context(), certQuery,
			cert.ID, cert.IVCUID, cert.ProofType, cert.VerifierVersion, cert.Timestamp, cert.IntentID,
			cert.ASTHash, cert.CodeHash, verifierSigsJSON, assertionsJSON, cert.ProofData,
			cert.HashChain, cert.Signature, cert.CreatedAt,
		)
		if err != nil {
			h.logger.Error("failed to insert proof certificate", zap.Error(err))
			c.JSON(http.StatusInternalServerError, gin.H{"error": "failed to store proof certificate"})
			return
		}
	}

	if err := tx.Commit(c.Request.Context()); err != nil {
		h.logger.Error("failed to commit transaction", zap.Error(err))
		c.JSON(http.StatusInternalServerError, gin.H{"error": "failed to commit transaction"})
		return
	}

	response := VerifyResponse{
		VerificationID:  uuid.New(),
		Passed:          aiResult.Passed,
		Confidence:      aiResult.Confidence,
		VerifierResults: aiResult.VerifierResults,
		Limitations:     []string{},
	}

	if proofCertID != nil {
		// Could add certificate ID to response if needed
		h.logger.Info("proof certificate generated", zap.String("cert_id", proofCertID.String()))
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
