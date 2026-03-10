package config

import (
	"fmt"
	"os"
	"strings"
)

// Config holds all configuration for the API service
type Config struct {
	// Server
	Port        string
	Environment string

	// Database
	DatabaseURL string
	RedisURL    string

	// External services
	AIServiceURL string
	VerifierURL  string
	TemporalURL  string

	// Security
	JWTSecret string
}

// Load reads configuration from environment variables
func Load() *Config {
	cfg := &Config{
		Port:         getEnv("PORT", "8080"),
		Environment:  getEnv("GO_ENV", "development"),
		DatabaseURL:  getEnv("DATABASE_URL", "postgres://axiom:axiom_dev_password@localhost:5433/axiom?sslmode=disable"),
		RedisURL:     getEnv("REDIS_URL", "redis://localhost:6380"),
		AIServiceURL: getEnv("AI_SERVICE_URL", "http://localhost:8000"),
		VerifierURL:  getEnv("VERIFIER_URL", "localhost:50051"),
		TemporalURL:  getEnv("TEMPORAL_URL", "localhost:7233"),
		JWTSecret:    getEnv("JWT_SECRET", "dev-secret-change-in-production"),
	}

	cfg.Validate()
	return cfg
}

// Validate checks for insecure defaults in non-development environments.
// Panics if dev-default credentials are used in production/staging.
func (c *Config) Validate() {
	if c.Environment != "development" && c.Environment != "dev" && c.Environment != "test" {
		devDefaults := []string{"axiom_dev_password", "dev-secret-change-in-production"}
		for _, secret := range devDefaults {
			if strings.Contains(c.DatabaseURL, secret) {
				panic(fmt.Sprintf("FATAL: DATABASE_URL contains dev-default password '%s' in %s environment. Set a secure password via env.", secret, c.Environment))
			}
			if c.JWTSecret == secret {
				panic(fmt.Sprintf("FATAL: JWT_SECRET is set to dev-default '%s' in %s environment. Set a secure secret via env.", secret, c.Environment))
			}
		}
	}
}

func getEnv(key, defaultValue string) string {
	if value := os.Getenv(key); value != "" {
		return value
	}
	return defaultValue
}

