package middleware

import (
	"net/http"

	"github.com/gin-gonic/gin"
)

// APIError represents a structured error response
type APIError struct {
	Code       string `json:"code"`
	Message    string `json:"message"`
	Details    string `json:"details,omitempty"`
	RetryAfter int    `json:"retry_after_ms,omitempty"`
}

// Common error codes
const (
	ErrCodeBadRequest           = "BAD_REQUEST"
	ErrCodeUnauthorized         = "UNAUTHORIZED"
	ErrCodeNotFound             = "NOT_FOUND"
	ErrCodeInternalError        = "INTERNAL_ERROR"
	ErrCodeAIServiceUnavailable = "AI_SERVICE_UNAVAILABLE"
	ErrCodeDatabaseError        = "DATABASE_ERROR"
	ErrCodeBudgetExceeded       = "BUDGET_EXCEEDED"
	ErrCodeRateLimited          = "RATE_LIMITED"
)

// RespondError sends a structured error response
func RespondError(c *gin.Context, status int, code string, message string) {
	c.JSON(status, gin.H{
		"error": APIError{
			Code:    code,
			Message: message,
		},
	})
}

// RespondErrorWithDetails sends a structured error response with details
func RespondErrorWithDetails(c *gin.Context, status int, code string, message string, details string) {
	c.JSON(status, gin.H{
		"error": APIError{
			Code:    code,
			Message: message,
			Details: details,
		},
	})
}

// RespondErrorWithRetry sends a structured error response with retry hint
func RespondErrorWithRetry(c *gin.Context, status int, code string, message string, retryAfterMs int) {
	c.JSON(status, gin.H{
		"error": APIError{
			Code:       code,
			Message:    message,
			RetryAfter: retryAfterMs,
		},
	})
}

// BadRequest sends a 400 error
func BadRequest(c *gin.Context, message string) {
	RespondError(c, http.StatusBadRequest, ErrCodeBadRequest, message)
}

// Unauthorized sends a 401 error
func Unauthorized(c *gin.Context, message string) {
	RespondError(c, http.StatusUnauthorized, ErrCodeUnauthorized, message)
}

// NotFound sends a 404 error
func NotFound(c *gin.Context, message string) {
	RespondError(c, http.StatusNotFound, ErrCodeNotFound, message)
}

// InternalError sends a 500 error
func InternalError(c *gin.Context, message string) {
	RespondError(c, http.StatusInternalServerError, ErrCodeInternalError, message)
}

// AIServiceUnavailable sends a 503 error for AI service issues
func AIServiceUnavailable(c *gin.Context) {
	RespondErrorWithRetry(c, http.StatusServiceUnavailable, ErrCodeAIServiceUnavailable, "AI service is temporarily unavailable", 5000)
}
