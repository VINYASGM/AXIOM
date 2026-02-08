package handlers

import (
	"net/http"

	"github.com/axiom/api/internal/speculation"
	"github.com/gin-gonic/gin"
	"go.uber.org/zap"
)

type SpeculationHandler struct {
	engine *speculation.Engine
	logger *zap.Logger
}

func NewSpeculationHandler(engine *speculation.Engine, logger *zap.Logger) *SpeculationHandler {
	return &SpeculationHandler{
		engine: engine,
		logger: logger,
	}
}

type AnalyzeIntentRequest struct {
	Intent string `json:"intent" binding:"required"`
}

func (h *SpeculationHandler) AnalyzeIntent(c *gin.Context) {
	var req AnalyzeIntentRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	paths, err := h.engine.AnalyzeIntent(c.Request.Context(), req.Intent)
	if err != nil {
		h.logger.Error("failed to analyze intent", zap.Error(err))
		c.JSON(http.StatusInternalServerError, gin.H{"error": "failed to analyze intent"})
		return
	}

	c.JSON(http.StatusOK, gin.H{"paths": paths})
}
