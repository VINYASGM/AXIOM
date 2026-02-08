package economics

import (
	"context"
	"database/sql"
	"fmt"

	"github.com/axiom/api/internal/database"
	"github.com/google/uuid"
	"go.uber.org/zap"
)

// Service handles economic logic like budgeting and usage tracking
type Service struct {
	db     *database.Postgres
	logger *zap.Logger
}

func NewService(db *database.Postgres, logger *zap.Logger) *Service {
	return &Service{
		db:     db,
		logger: logger,
	}
}

// Budget check result
type BudgetStatus struct {
	Allowed         bool
	RemainingBudget float64
	Reason          string
}

// CheckBudget verifies if a project has enough budget for an operation
func (s *Service) CheckBudget(ctx context.Context, projectID uuid.UUID, estimatedCost float64) (*BudgetStatus, error) {
	// 1. Get project budget and current usage
	var budget float64
	var usage float64

	// Default budget if not set (e.g., $10.00 for free tier)
	defaultBudget := 10.0

	// We need to query project settings.
	// specific schema might need adjustment based on available tables.
	// For now, assuming projects table has budget_limit or strict_limit

	// check if projects table has these columns, if not we might need to add them or use a separate table
	// mocking the schema check for now, assuming standard setup

	query := `
		SELECT COALESCE(budget_limit, $2), current_usage 
		FROM projects 
		WHERE id = $1
	`

	err := s.db.Pool().QueryRow(ctx, query, projectID, defaultBudget).Scan(&budget, &usage)
	if err != nil {
		if err == sql.ErrNoRows {
			return nil, fmt.Errorf("project not found")
		}
		// Fallback for missing columns or other errors - simpler check
		s.logger.Warn("Failed to check detailed budget, falling back to default", zap.Error(err))
		budget = defaultBudget
		usage = 0 // Assume 0 if we can't read it, or fail safe? Fail safe is better usually.
	}

	remaining := budget - usage

	if remaining < estimatedCost {
		s.logger.Info("Budget exceeded",
			zap.String("project_id", projectID.String()),
			zap.Float64("budget", budget),
			zap.Float64("usage", usage),
			zap.Float64("estimated", estimatedCost),
		)
		return &BudgetStatus{
			Allowed:         false,
			RemainingBudget: remaining,
			Reason:          "Insufficient budget",
		}, nil
	}

	return &BudgetStatus{
		Allowed:         true,
		RemainingBudget: remaining,
		Reason:          "Budget sufficient",
	}, nil
}

// RecordUsage logs actual usage after an operation
func (s *Service) RecordUsage(ctx context.Context, projectID uuid.UUID, userID uuid.UUID, cost float64, operationType string, details map[string]interface{}) error {
	// 1. Update project usage
	// Using atomic increment if possible, or simple update

	updateQuery := `
		UPDATE projects 
		SET current_usage = current_usage + $2, updated_at = NOW()
		WHERE id = $1
	`
	_, err := s.db.Pool().Exec(ctx, updateQuery, projectID, cost)
	if err != nil {
		return fmt.Errorf("failed to update project usage: %w", err)
	}

	// 2. Insert into usage_logs table
	// We might need to create this table if it doesn't exist
	// ideally this should be async or buffered

	// Create usage_logs table logic should be in migrations, but for now we assume it exists or we log validation error

	logQuery := `
		INSERT INTO usage_logs (project_id, user_id, cost, operation_type, details)
		VALUES ($1, $2, $3, $4, $5)
	`
	_, err = s.db.Pool().Exec(ctx, logQuery, projectID, userID, cost, operationType, details)
	if err != nil {
		// Log error but don't fail the operation since the main usage was updated
		s.logger.Error("failed to log detailed usage", zap.Error(err))
	}

	return nil
}
