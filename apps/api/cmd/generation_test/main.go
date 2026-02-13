package main

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"log"
	"net/http"
	"time"

	"github.com/axiom/api/internal/config"
	"github.com/axiom/api/internal/database"
	"github.com/golang-jwt/jwt/v5"
	"github.com/google/uuid"
)

func main() {
	// Load config
	cfg := config.Load()

	// Connect to DB
	db, err := database.NewPostgres(cfg.DatabaseURL)
	if err != nil {
		log.Fatalf("Failed to connect to DB: %v", err)
	}
	defer db.Close()

	ctx := context.Background()

	// 1. Setup Data
	userID := uuid.New()
	projectID := uuid.New()
	ivcuID := uuid.New()
	email := fmt.Sprintf("gen-test-%s@example.com", userID.String())

	log.Printf("Seeding for Generation Test. UserID: %s, IVCUID: %s", userID, ivcuID)

	// Create User
	_, err = db.Pool().Exec(ctx, `
		INSERT INTO users (id, email, name, password_hash, role, trust_dial_default, created_at, updated_at)
		VALUES ($1, $2, $3, $4, $5, $6, NOW(), NOW())
	`, userID, email, "Gen Test User", "hash", "user", 1)
	if err != nil {
		log.Fatalf("Failed to insert user: %v", err)
	}

	// Create Project
	_, err = db.Pool().Exec(ctx, `
		INSERT INTO projects (id, name, owner_id, security_context, settings, created_at, updated_at)
		VALUES ($1, $2, $3, $4, $5, NOW(), NOW())
	`, projectID, "Gen Project", userID, "confidential", "{}")
	if err != nil {
		log.Fatalf("Failed to insert project: %v", err)
	}

	// Create IVCU
	_, err = db.Pool().Exec(ctx, `
		INSERT INTO ivcus (id, project_id, version, raw_intent, status, created_by, created_at, updated_at)
		VALUES ($1, $2, $3, $4, 'draft', $5, NOW(), NOW())
	`, ivcuID, projectID, 1, "Create a python function to calculate fibonacci sequence", userID)
	if err != nil {
		log.Fatalf("Failed to insert IVCU: %v", err)
	}

	// 2. Start Generation
	log.Println("Calling StartGeneration endpoint...")
	url := "http://localhost:8080/api/v1/generation/start"
	payload := map[string]interface{}{
		"ivcu_id":         ivcuID.String(),
		"language":        "python",
		"candidate_count": 1,
		"strategy":        "simple",
	}
	jsonBody, _ := json.Marshal(payload)

	req, _ := http.NewRequest("POST", url, bytes.NewBuffer(jsonBody))
	req.Header.Set("Content-Type", "application/json")

	// Generate valid JWT token
	claims := jwt.MapClaims{
		"user_id": userID.String(),
		"exp":     time.Now().Add(time.Hour * 1).Unix(),
	}
	token := jwt.NewWithClaims(jwt.SigningMethodHS256, claims)
	tokenString, err := token.SignedString([]byte(cfg.JWTSecret))
	if err != nil {
		log.Fatalf("Failed to sign token: %v", err)
	}

	req.Header.Set("Authorization", "Bearer "+tokenString)

	client := &http.Client{Timeout: 10 * time.Second}
	resp, err := client.Do(req)
	if err != nil {
		log.Fatalf("Request failed: %v", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode == 401 {
		log.Fatal("Unauthorized. Need valid token.")
	}

	if resp.StatusCode != 202 {
		buf := new(bytes.Buffer)
		buf.ReadFrom(resp.Body)
		log.Fatalf("Expected 202 Accepted, got %d. Body: %s", resp.StatusCode, buf.String())
	}

	var respData map[string]interface{}
	json.NewDecoder(resp.Body).Decode(&respData)
	generationID := respData["generation_id"].(string)
	log.Printf("Generation started. ID: %s", generationID)

	// 3. Poll for Completion
	// This depends on the Temporal Worker running!
	// If Worker is not running, status will remain 'generating' or 'queued'.

	log.Println("Polling for status...")
	statusURL := fmt.Sprintf("http://localhost:8080/api/v1/generation/%s/status", ivcuID.String())

	for i := 0; i < 30; i++ { // Wait up to 30 seconds
		req, _ := http.NewRequest("GET", statusURL, nil)
		req.Header.Set("Authorization", "Bearer "+tokenString)

		resp, err := client.Do(req)
		if err == nil && resp.StatusCode == 200 {
			var statusData map[string]interface{}
			json.NewDecoder(resp.Body).Decode(&statusData)
			resp.Body.Close()

			status := statusData["status"].(string)
			stage := statusData["stage"].(string)
			log.Printf("Status: %s, Stage: %s", status, stage)

			if status == "verified" || status == "generated" || status == "completed" {
				log.Println("SUCCESS: Generation completed!")
				return
			}
			if status == "failed" {
				log.Fatalf("Generation failed: %v", statusData)
			}
		}

		time.Sleep(1 * time.Second)
	}

	log.Println("Timeout waiting for generation completion (Did you start the Temporal Worker?)")
}
