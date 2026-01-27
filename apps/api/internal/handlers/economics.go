package handlers

import (
	"bytes"
	"encoding/json"
	"net/http"

	"github.com/axiom/api/internal/database"
	"github.com/gin-gonic/gin"
	"go.uber.org/zap"
)

type EconomicsHandler struct {
	db           *database.Postgres
	aiServiceURL string
	logger       *zap.Logger
}

func NewEconomicsHandler(db *database.Postgres, aiServiceURL string, logger *zap.Logger) *EconomicsHandler {
	return &EconomicsHandler{
		db:           db,
		aiServiceURL: aiServiceURL,
		logger:       logger,
	}
}

type EstimateCostRequest struct {
	Intent         string `json:"intent" binding:"required"`
	Language       string `json:"language"`
	CandidateCount int    `json:"candidate_count"`
}

func (h *EconomicsHandler) EstimateCost(c *gin.Context) {
	var req EstimateCostRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	// Default values
	if req.Language == "" {
		req.Language = "python"
	}
	if req.CandidateCount == 0 {
		req.CandidateCount = 3
	}

	// Call AI Service
	reqBody := map[string]interface{}{
		"intent":          req.Intent,
		"language":        req.Language,
		"candidate_count": req.CandidateCount,
	}
	jsonBody, _ := json.Marshal(reqBody)

	resp, err := http.Post(h.aiServiceURL+"/cost/estimate", "application/json", bytes.NewBuffer(jsonBody))
	if err != nil {
		h.logger.Error("failed to call AI service for cost estimation", zap.Error(err))
		c.JSON(http.StatusServiceUnavailable, gin.H{"error": "AI service unavailable"})
		return
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		c.JSON(http.StatusBadGateway, gin.H{"error": "AI service returned error"})
		return
	}

	var result map[string]interface{}
	if err := json.NewDecoder(resp.Body).Decode(&result); err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "failed to decode AI response"})
		return
	}

	c.JSON(http.StatusOK, result)
}

func (h *EconomicsHandler) GetSessionCost(c *gin.Context) {
	sessionID := c.Param("sessionId")
	if sessionID == "" {
		c.JSON(http.StatusBadRequest, gin.H{"error": "session ID required"})
		return
	}

	resp, err := http.Get(h.aiServiceURL + "/cost/session/" + sessionID)
	if err != nil {
		h.logger.Error("failed to call AI service for session cost", zap.Error(err))
		c.JSON(http.StatusServiceUnavailable, gin.H{"error": "AI service unavailable"})
		return
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		c.JSON(http.StatusBadGateway, gin.H{"error": "AI service returned error"})
		return
	}

	var result map[string]interface{}
	if err := json.NewDecoder(resp.Body).Decode(&result); err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "failed to decode AI response"})
		return
	}

	c.JSON(http.StatusOK, result)
}
