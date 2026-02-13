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

	query := `SELECT skills, learning_style, updated_at FROM learner_models WHERE user_id = $1`
	var skillsJSON []byte
	var styleJSON []byte
	var updatedAt time.Time

	err := h.db.Pool().QueryRow(c.Request.Context(), query, userID).Scan(&skillsJSON, &styleJSON, &updatedAt)

	skills := make(map[string]int)

	if err != nil {
		// If not found, return empty profile (DB initializes on first event or we return default)
		h.logger.Info("Learner profile not found, returning default", zap.String("user_id", userID.String()))
		// Default empty
	} else {
		if len(skillsJSON) > 0 {
			if err := json.Unmarshal(skillsJSON, &skills); err != nil {
				h.logger.Error("failed to unmarshal skills", zap.Error(err))
			}
		}
	}

	// Calculate global level
	totalProficiency := 0
	count := 0
	for _, p := range skills {
		totalProficiency += p
		count++
	}

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
		LastUpdated: updatedAt,
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
	h.logger.Info("calling AI service for learning event", zap.String("url", h.aiServiceURL+"/learner/event"))

	resp, err := http.Post(h.aiServiceURL+"/learner/event", "application/json", bytes.NewBuffer(jsonBody))
	if err != nil {
		h.logger.Error("failed to call AI service for learning event", zap.Error(err))
		c.JSON(http.StatusServiceUnavailable, gin.H{"error": "AI service unavailable"})
		return
	}
	defer resp.Body.Close()

	h.logger.Info("AI service response", zap.Int("status", resp.StatusCode))

	if resp.StatusCode >= 200 && resp.StatusCode < 300 {
		var result struct {
			UpdatedSkills map[string]int `json:"updated_skills"`
		}
		if err := json.NewDecoder(resp.Body).Decode(&result); err == nil {
			h.logger.Info("AI service returned updated skills", zap.Any("skills", result.UpdatedSkills))
			if len(result.UpdatedSkills) > 0 {
				// 1. Read existing
				var existingSkillsJSON []byte
				queryRead := `SELECT skills FROM learner_models WHERE user_id = $1`
				err := h.db.Pool().QueryRow(c.Request.Context(), queryRead, userID.String()).Scan(&existingSkillsJSON)

				currentSkills := make(map[string]int)
				if err == nil && len(existingSkillsJSON) > 0 {
					_ = json.Unmarshal(existingSkillsJSON, &currentSkills)
				} else {
					h.logger.Info("no existing profile found locally, creating new")
				}

				// 2. Merge
				for k, v := range result.UpdatedSkills {
					currentSkills[k] = v
				}

				// 3. Write back
				mergedJSON, _ := json.Marshal(currentSkills)
				queryUpsert := `
					INSERT INTO learner_models (user_id, skills, updated_at)
					VALUES ($1, $2, NOW())
					ON CONFLICT (user_id) 
					DO UPDATE SET skills = $2, updated_at = NOW()
				`
				_, err = h.db.Pool().Exec(c.Request.Context(), queryUpsert, userID.String(), mergedJSON)
				if err != nil {
					h.logger.Error("failed to update learner profile locally", zap.Error(err))
				} else {
					h.logger.Info("learner profile updated locally")
				}
			}
		} else {
			h.logger.Error("failed to decode AI service response", zap.Error(err))
		}

		c.JSON(http.StatusOK, gin.H{"status": "processed", "updated_skills": result.UpdatedSkills})
		return
	}

	c.JSON(http.StatusBadGateway, gin.H{"error": "AI service returned non-200 status", "status": resp.StatusCode})
}
