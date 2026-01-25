package config

import "os"

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

	// Security
	JWTSecret string
}

// Load reads configuration from environment variables
func Load() *Config {
	return &Config{
		Port:         getEnv("PORT", "8080"),
		Environment:  getEnv("GO_ENV", "development"),
		DatabaseURL:  getEnv("DATABASE_URL", "postgres://axiom:axiom_dev_password@localhost:5433/axiom?sslmode=disable"),
		RedisURL:     getEnv("REDIS_URL", "redis://localhost:6380"),
		AIServiceURL: getEnv("AI_SERVICE_URL", "http://localhost:8000"),
		JWTSecret:    getEnv("JWT_SECRET", "dev-secret-change-in-production"),
	}
}

func getEnv(key, defaultValue string) string {
	if value := os.Getenv(key); value != "" {
		return value
	}
	return defaultValue
}
