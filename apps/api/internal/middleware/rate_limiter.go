package middleware

import (
	"net/http"
	"sync"
	"time"

	"github.com/gin-gonic/gin"
	"github.com/google/uuid"
)

// RateLimiter implements a simple token bucket rate limiter
type RateLimiter struct {
	mu           sync.Mutex
	tokens       map[string]int
	lastRefill   map[string]time.Time
	maxTokens    int
	refillRate   int           // tokens per refill
	refillPeriod time.Duration // how often to refill
}

// NewRateLimiter creates a new rate limiter
// maxTokens: maximum tokens per user
// refillRate: how many tokens to add per refill period
// refillPeriod: how often to refill tokens
func NewRateLimiter(maxTokens, refillRate int, refillPeriod time.Duration) *RateLimiter {
	return &RateLimiter{
		tokens:       make(map[string]int),
		lastRefill:   make(map[string]time.Time),
		maxTokens:    maxTokens,
		refillRate:   refillRate,
		refillPeriod: refillPeriod,
	}
}

// Allow checks if a request should be allowed for the given key
func (rl *RateLimiter) Allow(key string) bool {
	rl.mu.Lock()
	defer rl.mu.Unlock()

	now := time.Now()

	// Initialize if first time
	if _, exists := rl.tokens[key]; !exists {
		rl.tokens[key] = rl.maxTokens
		rl.lastRefill[key] = now
	}

	// Refill tokens
	elapsed := now.Sub(rl.lastRefill[key])
	refills := int(elapsed / rl.refillPeriod)
	if refills > 0 {
		rl.tokens[key] += refills * rl.refillRate
		if rl.tokens[key] > rl.maxTokens {
			rl.tokens[key] = rl.maxTokens
		}
		rl.lastRefill[key] = now
	}

	// Check if we have tokens
	if rl.tokens[key] > 0 {
		rl.tokens[key]--
		return true
	}

	return false
}

// Remaining returns the remaining tokens for a key
func (rl *RateLimiter) Remaining(key string) int {
	rl.mu.Lock()
	defer rl.mu.Unlock()
	return rl.tokens[key]
}

// RateLimitMiddleware creates a rate limiting middleware
// Uses user ID from context or falls back to IP address
func RateLimitMiddleware(rl *RateLimiter) gin.HandlerFunc {
	return func(c *gin.Context) {
		// Try to get user ID from context (set by auth middleware)
		key := c.ClientIP()
		if userID, exists := c.Get("user_id"); exists {
			if id, ok := userID.(string); ok {
				key = id
			} else if id, ok := userID.(uuid.UUID); ok {
				key = id.String()
			}
		}

		if !rl.Allow(key) {
			remaining := rl.Remaining(key)
			c.Header("X-RateLimit-Remaining", string(rune(remaining)))
			c.Header("X-RateLimit-Limit", string(rune(rl.maxTokens)))
			c.JSON(http.StatusTooManyRequests, gin.H{
				"error": APIError{
					Code:       ErrCodeRateLimited,
					Message:    "Too many requests, please try again later",
					RetryAfter: int(rl.refillPeriod.Milliseconds()),
				},
			})
			c.Abort()
			return
		}

		// Set rate limit headers
		c.Header("X-RateLimit-Remaining", string(rune(rl.Remaining(key))))
		c.Header("X-RateLimit-Limit", string(rune(rl.maxTokens)))

		c.Next()
	}
}

// DefaultRateLimiter provides a default rate limiter for the API
// 100 requests per minute per user
var DefaultRateLimiter = NewRateLimiter(100, 10, time.Minute)

// StrictRateLimiter provides a stricter rate limiter for expensive operations
// 20 requests per minute per user (for generation/verification)
var StrictRateLimiter = NewRateLimiter(20, 2, time.Minute)
