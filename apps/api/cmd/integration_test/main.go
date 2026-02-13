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
	"github.com/google/uuid"
)

func main() {
	// Load config to get DB URL
	cfg := config.Load()

	// Connect to DB
	db, err := database.NewPostgres(cfg.DatabaseURL)
	if err != nil {
		log.Fatalf("Failed to connect to DB: %v", err)
	}
	defer db.Close()

	ctx := context.Background()

	// 1. Setup Test Data
	userID := uuid.New()
	projectID := uuid.New()
	ivcuID := uuid.New()
	email := fmt.Sprintf("test-%s@example.com", userID.String())

	log.Printf("Seeding database with UserID: %s, IVCUID: %s", userID, ivcuID)

	// Create User
	// Using ON CONFLICT logic or just random new one
	_, err = db.Pool().Exec(ctx, `
		INSERT INTO users (id, email, name, password_hash, role, trust_dial_default, created_at, updated_at)
		VALUES ($1, $2, $3, $4, $5, $6, NOW(), NOW())
	`, userID, email, "Test User", "hash", "user", 1)
	if err != nil {
		log.Fatalf("Failed to insert user: %v", err)
	}

	// Create Project
	_, err = db.Pool().Exec(ctx, `
		INSERT INTO projects (id, name, owner_id, security_context, settings, created_at, updated_at)
		VALUES ($1, $2, $3, $4, $5, NOW(), NOW())
	`, projectID, "Test Project", userID, "confidential", "{}")
	if err != nil {
		log.Fatalf("Failed to insert project: %v", err)
	}

	// Create IVCU
	_, err = db.Pool().Exec(ctx, `
		INSERT INTO ivcus (id, project_id, version, raw_intent, status, created_by, created_at, updated_at)
		VALUES ($1, $2, $3, $4, 'draft', $5, NOW(), NOW())
	`, ivcuID, projectID, 1, "Verify me", userID)
	if err != nil {
		log.Fatalf("Failed to insert IVCU: %v", err)
	}

	// 2. Call Verification Endpoint
	log.Println("Calling verification endpoint...")
	url := "http://localhost:8080/api/v1/verification/verify"
	payload := map[string]interface{}{
		"ivcu_id": ivcuID.String(),
		"code":    "def main(): print('hello')",
	}
	jsonBody, _ := json.Marshal(payload)

	// Retry loop for server startup
	var resp *http.Response
	for i := 0; i < 10; i++ {
		req, _ := http.NewRequest("POST", url, bytes.NewBuffer(jsonBody))
		req.Header.Set("Content-Type", "application/json")

		client := &http.Client{Timeout: 5 * time.Second}
		resp, err = client.Do(req)
		if err == nil {
			break
		}
		log.Printf("Waiting for server... %v", err)
		time.Sleep(1 * time.Second)
	}

	if err != nil {
		log.Fatalf("Request failed after retries: %v", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != 200 {
		buf := new(bytes.Buffer)
		buf.ReadFrom(resp.Body)
		log.Fatalf("Expected 200 OK, got %d. Body: %s", resp.StatusCode, buf.String())
	}

	// 3. Verify Proof Certificate Created
	log.Println("Verifying certificate in DB...")
	var count int
	err = db.Pool().QueryRow(ctx, "SELECT COUNT(*) FROM proof_certificates WHERE ivcu_id = $1", ivcuID).Scan(&count)
	if err != nil {
		log.Fatalf("Failed to query certificates: %v", err)
	}

	if count == 0 {
		log.Fatal("No proof certificate found!")
	}

	log.Println("SUCCESS: Verified Endpoint and Certificate Generation")
}
