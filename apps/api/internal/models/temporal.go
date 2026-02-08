package models

// GenerationInput matches the Python GenerationInput dataclass
type GenerationInput struct {
	SDOID          string   `json:"sdo_id"`
	Intent         string   `json:"intent"`
	Constraints    []string `json:"constraints"`
	Language       string   `json:"language"`
	CandidateCount int      `json:"candidate_count"`
	ModelTier      string   `json:"model_tier"`
}

// GenerationOutput matches the Python GenerationOutput dataclass
type GenerationOutput struct {
	SDOID               string                   `json:"sdo_id"`
	Candidates          []map[string]interface{} `json:"candidates"`
	SelectedCode        string                   `json:"selected_code"`
	SelectedCandidateID string                   `json:"selected_candidate_id"`
	TotalCost           float64                  `json:"total_cost"`
}
