package speculation

import (
	"context"
	"strings"

	"go.uber.org/zap"
)

// Engine analyzes intents for speculative execution opportunities
type Engine struct {
	logger *zap.Logger
	// Could inject AI service here for deeper analysis
}

func NewEngine(logger *zap.Logger) *Engine {
	return &Engine{
		logger: logger,
	}
}

// SpeculativePath represents a potential future state or parallel execution path
type SpeculativePath struct {
	Name             string  `json:"name"`
	Description      string  `json:"description"`
	Likelihood       float64 `json:"likelihood"`        // 0.0 to 1.0
	EstimatedBenefit string  `json:"estimated_benefit"` // e.g., "Speedup 2x"
	Complexity       string  `json:"complexity"`        // "Low", "Medium", "High"
}

// AnalyzeIntent returns potential speculative paths for a given intent
func (e *Engine) AnalyzeIntent(ctx context.Context, intent string) ([]SpeculativePath, error) {
	paths := []SpeculativePath{}
	intentLower := strings.ToLower(intent)

	// Heuristic 1: If intent involves "and", "both", "multiple", it might be parallelizable
	if strings.Contains(intentLower, " and ") || strings.Contains(intentLower, "both") || strings.Contains(intentLower, ",") {
		paths = append(paths, SpeculativePath{
			Name:             "Parallel Execution",
			Description:      "Split intent into multiple independent tasks",
			Likelihood:       0.8,
			EstimatedBenefit: "ROI +40%",
			Complexity:       "Medium",
		})
	}

	// Heuristic 2: If intent involves "test", "verify", "check", suggest TDD path
	if strings.Contains(intentLower, "test") || strings.Contains(intentLower, "verify") {
		paths = append(paths, SpeculativePath{
			Name:             "Test-Driven Development",
			Description:      "Generate tests before implementation",
			Likelihood:       0.9,
			EstimatedBenefit: "Reliability +50%",
			Complexity:       "Low",
		})
	}

	// Heuristic 3: If intent is vague or short, suggest "Exploratory Prototyping"
	if len(intent) < 20 {
		paths = append(paths, SpeculativePath{
			Name:             "Exploratory Prototype",
			Description:      "Generate 3 distinct variations to explore solution space",
			Likelihood:       0.7,
			EstimatedBenefit: "Creativity +60%",
			Complexity:       "High",
		})
	}

	// Always add a standard path
	paths = append(paths, SpeculativePath{
		Name:             "Standard Execution",
		Description:      "Linear execution of the intent",
		Likelihood:       1.0,
		EstimatedBenefit: "Baseline",
		Complexity:       "Low",
	})

	e.logger.Info("analyzed intent for speculation",
		zap.String("intent_preview", intent[:min(len(intent), 20)]),
		zap.Int("paths_found", len(paths)),
	)

	return paths, nil
}

func min(a, b int) int {
	if a < b {
		return a
	}
	return b
}
