package verifier

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"log"
	"net/http"
	"time"
)

// Client defines the interface for the Verification Service
type Client interface {
	Verify(ctx context.Context, code string, language string) (bool, float64, error)
}

// GrpcClient is the implementation that calls the AI verification endpoint.
// When the Rust gRPC verifier is available, replace the HTTP call with a real gRPC call.
type GrpcClient struct {
	aiServiceURL string
	httpClient   *http.Client
}

func NewClient(addr string) (*GrpcClient, error) {
	log.Printf("Verifier Client initialized (AI service: %s)", addr)
	return &GrpcClient{
		aiServiceURL: addr,
		httpClient: &http.Client{
			Timeout: 30 * time.Second,
		},
	}, nil
}

// verifyRequest is the payload sent to the AI service /verify endpoint
type verifyRequest struct {
	Code     string `json:"code"`
	Language string `json:"language"`
	RunTier2 bool   `json:"run_tier2"`
}

// verifyResponse is the response from the AI service /verify endpoint
type verifyResponse struct {
	Passed          bool    `json:"passed"`
	Confidence      float64 `json:"confidence"`
	TotalErrors     int     `json:"total_errors"`
	TotalWarnings   int     `json:"total_warnings"`
	Tier1Passed     bool    `json:"tier_1_passed"`
	Tier2Passed     *bool   `json:"tier_2_passed,omitempty"`
}

func (c *GrpcClient) Verify(ctx context.Context, code string, language string) (bool, float64, error) {
	log.Printf("Verifier Client: Verifying code (len=%d, lang=%s)", len(code), language)

	// Call the AI service verification endpoint
	reqBody := verifyRequest{
		Code:     code,
		Language: language,
		RunTier2: true,
	}

	jsonData, err := json.Marshal(reqBody)
	if err != nil {
		return false, 0.0, fmt.Errorf("failed to marshal verify request: %w", err)
	}

	req, err := http.NewRequestWithContext(ctx, "POST", c.aiServiceURL+"/verify", bytes.NewBuffer(jsonData))
	if err != nil {
		return false, 0.0, fmt.Errorf("failed to create verify request: %w", err)
	}
	req.Header.Set("Content-Type", "application/json")

	resp, err := c.httpClient.Do(req)
	if err != nil {
		log.Printf("Verifier Client: AI service unavailable: %v", err)
		// Fail closed — do NOT pass unverified code
		return false, 0.0, fmt.Errorf("verification service unavailable: %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		return false, 0.0, fmt.Errorf("verification service returned status %d", resp.StatusCode)
	}

	var result verifyResponse
	if err := json.NewDecoder(resp.Body).Decode(&result); err != nil {
		return false, 0.0, fmt.Errorf("failed to decode verify response: %w", err)
	}

	return result.Passed, result.Confidence, nil
}
