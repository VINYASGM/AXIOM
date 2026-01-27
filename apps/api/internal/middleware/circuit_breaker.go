package middleware

import (
	"net/http"
	"sync"
	"time"

	"github.com/gin-gonic/gin"
)

// CircuitState represents the state of the circuit breaker
type CircuitState int

const (
	CircuitClosed   CircuitState = iota // Normal operation
	CircuitOpen                         // Failing, reject requests
	CircuitHalfOpen                     // Testing if recovered
)

// CircuitBreaker implements the circuit breaker pattern
type CircuitBreaker struct {
	mu              sync.RWMutex
	state           CircuitState
	failures        int
	successes       int
	lastFailureTime time.Time

	// Configuration
	FailureThreshold int           // Number of failures before opening
	SuccessThreshold int           // Number of successes before closing
	Timeout          time.Duration // How long to wait before half-open
	OnStateChange    func(from, to CircuitState)
}

// NewCircuitBreaker creates a new circuit breaker with defaults
func NewCircuitBreaker() *CircuitBreaker {
	return &CircuitBreaker{
		state:            CircuitClosed,
		FailureThreshold: 5,
		SuccessThreshold: 2,
		Timeout:          30 * time.Second,
	}
}

// NewCircuitBreakerWithConfig creates a circuit breaker with custom config
func NewCircuitBreakerWithConfig(failureThreshold, successThreshold int, timeout time.Duration) *CircuitBreaker {
	return &CircuitBreaker{
		state:            CircuitClosed,
		FailureThreshold: failureThreshold,
		SuccessThreshold: successThreshold,
		Timeout:          timeout,
	}
}

// State returns the current state
func (cb *CircuitBreaker) State() CircuitState {
	cb.mu.RLock()
	defer cb.mu.RUnlock()
	return cb.state
}

// Allow checks if a request should be allowed
func (cb *CircuitBreaker) Allow() bool {
	cb.mu.Lock()
	defer cb.mu.Unlock()

	switch cb.state {
	case CircuitClosed:
		return true
	case CircuitOpen:
		// Check if timeout has passed
		if time.Since(cb.lastFailureTime) > cb.Timeout {
			cb.setState(CircuitHalfOpen)
			return true
		}
		return false
	case CircuitHalfOpen:
		return true
	}
	return false
}

// RecordSuccess records a successful request
func (cb *CircuitBreaker) RecordSuccess() {
	cb.mu.Lock()
	defer cb.mu.Unlock()

	switch cb.state {
	case CircuitHalfOpen:
		cb.successes++
		if cb.successes >= cb.SuccessThreshold {
			cb.setState(CircuitClosed)
			cb.failures = 0
			cb.successes = 0
		}
	case CircuitClosed:
		cb.failures = 0 // Reset failures on success
	}
}

// RecordFailure records a failed request
func (cb *CircuitBreaker) RecordFailure() {
	cb.mu.Lock()
	defer cb.mu.Unlock()

	cb.failures++
	cb.lastFailureTime = time.Now()

	switch cb.state {
	case CircuitClosed:
		if cb.failures >= cb.FailureThreshold {
			cb.setState(CircuitOpen)
		}
	case CircuitHalfOpen:
		cb.setState(CircuitOpen)
		cb.successes = 0
	}
}

func (cb *CircuitBreaker) setState(newState CircuitState) {
	if cb.OnStateChange != nil && cb.state != newState {
		cb.OnStateChange(cb.state, newState)
	}
	cb.state = newState
}

// AIServiceCircuitBreaker is a global circuit breaker for AI service
var AIServiceCircuitBreaker = NewCircuitBreaker()

// CircuitBreakerMiddleware wraps the AI service calls with circuit breaker
func CircuitBreakerMiddleware(cb *CircuitBreaker) gin.HandlerFunc {
	return func(c *gin.Context) {
		if !cb.Allow() {
			c.JSON(http.StatusServiceUnavailable, gin.H{
				"error": APIError{
					Code:       "CIRCUIT_OPEN",
					Message:    "AI service is temporarily unavailable due to repeated failures",
					RetryAfter: int(cb.Timeout.Milliseconds()),
				},
			})
			c.Abort()
			return
		}
		c.Next()
	}
}
