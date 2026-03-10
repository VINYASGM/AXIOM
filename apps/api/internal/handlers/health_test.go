package handlers

import (
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"testing"

	"github.com/gin-gonic/gin"
)

func TestHealth_ReturnsOK(t *testing.T) {
	gin.SetMode(gin.TestMode)
	r := gin.New()

	handler := NewHealthHandler(nil, nil, "")
	r.GET("/health", handler.Health)

	w := httptest.NewRecorder()
	req, _ := http.NewRequest("GET", "/health", nil)
	r.ServeHTTP(w, req)

	if w.Code != http.StatusOK {
		t.Errorf("expected 200, got %d", w.Code)
	}

	var resp map[string]interface{}
	if err := json.Unmarshal(w.Body.Bytes(), &resp); err != nil {
		t.Fatalf("failed to unmarshal response: %v", err)
	}
	if resp["status"] != "healthy" {
		t.Errorf("expected status healthy, got %v", resp["status"])
	}
	if resp["service"] != "axiom-api" {
		t.Errorf("expected service axiom-api, got %v", resp["service"])
	}
}

func TestDeepHealth_NoDependencies(t *testing.T) {
	gin.SetMode(gin.TestMode)
	r := gin.New()

	// All nil deps → all "not configured"
	handler := NewHealthHandler(nil, nil, "")
	r.GET("/health/deep", handler.DeepHealth)

	w := httptest.NewRecorder()
	req, _ := http.NewRequest("GET", "/health/deep", nil)
	r.ServeHTTP(w, req)

	if w.Code != http.StatusOK {
		t.Errorf("expected 200, got %d", w.Code)
	}

	var resp HealthResponse
	if err := json.Unmarshal(w.Body.Bytes(), &resp); err != nil {
		t.Fatalf("failed to unmarshal response: %v", err)
	}

	if resp.Dependencies["database"] != "not configured" {
		t.Errorf("expected database not configured, got %s", resp.Dependencies["database"])
	}
	if resp.Dependencies["redis"] != "not configured" {
		t.Errorf("expected redis not configured, got %s", resp.Dependencies["redis"])
	}
	if resp.Dependencies["ai_service"] != "not configured" {
		t.Errorf("expected ai_service not configured, got %s", resp.Dependencies["ai_service"])
	}
}
