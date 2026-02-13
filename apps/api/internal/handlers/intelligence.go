package handlers

import (
	"bytes"
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

type IntelligenceHandler struct {
	db           *database.Postgres
	aiServiceURL string
	logger       *zap.Logger
}

func NewIntelligenceHandler(db *database.Postgres, aiServiceURL string, logger *zap.Logger) *IntelligenceHandler {
	return &IntelligenceHandler{
		db:           db,
		aiServiceURL: aiServiceURL,
		logger:       logger,
	}
}

// GetUserLearner returns the learner profile for the current user
func (h *IntelligenceHandler) GetUserLearner(c *gin.Context) {
	userID, exists := middleware.GetUserID(c)
	if !exists {
		c.JSON(http.StatusUnauthorized, gin.H{"error": "unauthorized"})
		return
	}

	query := `SELECT skill, proficiency FROM user_skills WHERE user_id = $1`
	rows, err := h.db.Pool().Query(c.Request.Context(), query, userID)
	if err != nil {
		h.logger.Error("failed to fetch skills", zap.Error(err))
		c.JSON(http.StatusInternalServerError, gin.H{"error": "failed to fetch user skills"})
		return
	}
	defer rows.Close()

	skills := make(map[string]int)
	totalProficiency := 0
	count := 0

	for rows.Next() {
		var skill string
		var proficiency int
		if err := rows.Scan(&skill, &proficiency); err == nil {
			skills[skill] = proficiency
			totalProficiency += proficiency
			count++
		}
	}

	// Calculate global level
	avg := 0.0
	if count > 0 {
		avg = float64(totalProficiency) / float64(count)
	}

	globalLevel := "novice"
	if avg > 7 {
		globalLevel = "expert"
	} else if avg > 4 {
		globalLevel = "intermediate"
	}

	c.JSON(http.StatusOK, models.LearnerProfile{
		UserID:      userID,
		GlobalLevel: globalLevel,
		Skills:      skills,
		LastUpdated: time.Now(),
	})
}

// GetReasoningTrace returns the trace for a specific IVCU
func (h *IntelligenceHandler) GetReasoningTrace(c *gin.Context) {
	ivcuIDStr := c.Param("ivcuId")
	ivcuID, err := uuid.Parse(ivcuIDStr)
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "invalid IVCU ID"})
		return
	}

	// 1. Get SDO ID from IVCU
	var generationParamsJSON []byte
	query := `SELECT generation_params FROM ivcus WHERE id = $1`
	err = h.db.Pool().QueryRow(c.Request.Context(), query, ivcuID).Scan(&generationParamsJSON)
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

	if sdoID == "" {
		c.JSON(http.StatusNotFound, gin.H{"error": "No SDO ID associated with this IVCU"})
		return
	}

	// 2. Fetch SDO from AI Service (which contains history)
	resp, err := http.Get(h.aiServiceURL + "/sdo/" + sdoID)
	if err != nil {
		h.logger.Error("failed to call AI service for SDO", zap.Error(err))
		c.JSON(http.StatusServiceUnavailable, gin.H{"error": "AI service unavailable"})
		return
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		h.logger.Error("AI service returned error for SDO", zap.Int("status", resp.StatusCode))
		c.JSON(http.StatusBadGateway, gin.H{"error": "AI service returned error"})
		return
	}

	var sdoResponse map[string]interface{}
	if err := json.NewDecoder(resp.Body).Decode(&sdoResponse); err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "failed to decode SDO response"})
		return
	}

	// 3. Extract history from the SDO response
	history, _ := sdoResponse["history"]
	c.JSON(http.StatusOK, gin.H{
		"ivcuId": ivcuID,
		"trace":  history,
	})
}

// LearningEvent represents a user learning action
type LearningEvent struct {
	UserID    string                 `json:"user_id"`
	EventType string                 `json:"event_type" binding:"required"`
	Details   map[string]interface{} `json:"details"`
}

// PostLearningEvent handles new learning events
func (h *IntelligenceHandler) PostLearningEvent(c *gin.Context) {
	userID, exists := middleware.GetUserID(c)
	if !exists {
		c.JSON(http.StatusUnauthorized, gin.H{"error": "unauthorized"})
		return
	}

	var req LearningEvent
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}
	req.UserID = userID.String() // Ensure correct user ID

	// Call AI Service
	jsonBody, _ := json.Marshal(req)
	resp, err := http.Post(h.aiServiceURL+"/learner/event", "application/json", bytes.NewBuffer(jsonBody))
	if err != nil {
		h.logger.Error("failed to call AI service for learning event", zap.Error(err))
		// Don't fail the request completely for analytics
		c.JSON(http.StatusAccepted, gin.H{"status": "queued"})
		return
	}
	defer resp.Body.Close()

	if resp.StatusCode == http.StatusOK {
		var result struct {
			UpdatedSkills map[string]int `json:"updated_skills"`
		}
		if err := json.NewDecoder(resp.Body).Decode(&result); err == nil && len(result.UpdatedSkills) > 0 {
			// Update local DB
			for skill, delta := range result.UpdatedSkills {
				query := `
					INSERT INTO user_skills (user_id, skill, proficiency, last_updated)
					VALUES ($1, $2, $3, NOW())
					ON CONFLICT (user_id, skill) 
					DO UPDATE SET proficiency = user_skills.proficiency + $3, last_updated = NOW()
				`
				h.db.Pool().Exec(c.Request.Context(), query, userID, skill, delta)
			}
		}
	}

	c.JSON(http.StatusOK, gin.H{"status": "processed"})
}
