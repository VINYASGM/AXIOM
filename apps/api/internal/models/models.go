package models

import (
	"time"

	"github.com/google/uuid"
)

// IVCUStatus represents the lifecycle state of an IVCU
type IVCUStatus string

const (
	IVCUStatusDraft      IVCUStatus = "draft"
	IVCUStatusGenerating IVCUStatus = "generating"
	IVCUStatusVerifying  IVCUStatus = "verifying"
	IVCUStatusVerified   IVCUStatus = "verified"
	IVCUStatusDeployed   IVCUStatus = "deployed"
	IVCUStatusDeprecated IVCUStatus = "deprecated"
	IVCUStatusFailed     IVCUStatus = "failed"
)

// IVCU represents an Intent-Verified Code Unit - the atomic unit of AXIOM
type IVCU struct {
	ID        uuid.UUID `json:"id"`
	ProjectID uuid.UUID `json:"project_id"`
	Version   int       `json:"version"`

	// Intent
	RawIntent    string                 `json:"raw_intent"`
	ParsedIntent map[string]interface{} `json:"parsed_intent,omitempty"`

	// Contracts
	Contracts []Contract `json:"contracts"`

	// Verification
	VerificationResult *VerificationResult `json:"verification_result,omitempty"`
	ConfidenceScore    float64             `json:"confidence_score"`

	// Implementation
	Code     string `json:"code,omitempty"`
	Language string `json:"language,omitempty"`

	// Provenance
	ModelID          string                 `json:"model_id,omitempty"`
	ModelVersion     string                 `json:"model_version,omitempty"`
	GenerationParams map[string]interface{} `json:"generation_params,omitempty"`
	InputHash        string                 `json:"input_hash,omitempty"`
	OutputHash       string                 `json:"output_hash,omitempty"`

	// Metadata
	Status    IVCUStatus  `json:"status"`
	CreatedAt time.Time   `json:"created_at"`
	UpdatedAt time.Time   `json:"updated_at"`
	CreatedBy uuid.UUID   `json:"created_by"`
	ParentIDs []uuid.UUID `json:"parent_ids,omitempty"`
}

// Contract represents a formal constraint on the IVCU
type Contract struct {
	Type        string                 `json:"type"` // precondition, postcondition, invariant
	Description string                 `json:"description"`
	Expression  string                 `json:"expression,omitempty"`
	Metadata    map[string]interface{} `json:"metadata,omitempty"`
}

// VerificationResult holds the results of verification
type VerificationResult struct {
	Passed          bool             `json:"passed"`
	Confidence      float64          `json:"confidence"`
	VerifierResults []VerifierResult `json:"verifier_results"`
	Limitations     []string         `json:"limitations,omitempty"`
	Duration        time.Duration    `json:"duration_ms"`
}

// VerifierResult represents a single verifier's result
type VerifierResult struct {
	Name       string   `json:"name"`
	Tier       int      `json:"tier"` // 1, 2, or 3
	Passed     bool     `json:"passed"`
	Confidence float64  `json:"confidence"`
	Messages   []string `json:"messages,omitempty"`
	Duration   int64    `json:"duration_ms"`
}

// ProofCertificate represents a cryptographic proof of verification
type ProofCertificate struct {
	ID                 uuid.UUID           `json:"id"`
	IVCUID             uuid.UUID           `json:"ivcu_id"`
	ProofType          ProofType           `json:"proof_type"`
	VerifierVersion    string              `json:"verifier_version"`
	Timestamp          time.Time           `json:"timestamp"`
	IntentID           uuid.UUID           `json:"intent_id"`
	ASTHash            string              `json:"ast_hash"`
	CodeHash           string              `json:"code_hash"`
	VerifierSignatures []VerifierSignature `json:"verifier_signatures"`
	Assertions         []FormalAssertion   `json:"assertions"`
	ProofData          []byte              `json:"proof_data"`
	HashChain          string              `json:"hash_chain"`
	Signature          []byte              `json:"signature"`
	CreatedAt          time.Time           `json:"created_at"`
}

// VerifierSignature represents a signature from a specific verifier
type VerifierSignature struct {
	Verifier  string    `json:"verifier"`
	Signature string    `json:"signature"`
	Timestamp time.Time `json:"timestamp"`
}

// FormalAssertion represents a formal property verified
type FormalAssertion struct {
	Type        string `json:"type"`
	Description string `json:"description"`
	Verified    bool   `json:"verified"`
	Evidence    string `json:"evidence"`
}

// ProofType defines the type of proof
type ProofType string

const (
	ProofTypeTypeSafety         ProofType = "type_safety"
	ProofTypeMemorySafety       ProofType = "memory_safety"
	ProofTypeContractCompliance ProofType = "contract_compliance"
	ProofTypePropertyBased      ProofType = "property_based"
)

// User represents a user in the system
type User struct {
	ID               uuid.UUID  `json:"id"`
	Email            string     `json:"email"`
	Name             string     `json:"name"`
	PasswordHash     string     `json:"-"` // Never serialize
	OrgID            *uuid.UUID `json:"org_id,omitempty"`
	Role             string     `json:"role"`
	TrustDialDefault int        `json:"trust_dial_default"`
	CreatedAt        time.Time  `json:"created_at"`
	UpdatedAt        time.Time  `json:"updated_at"`
}

// Project represents a project container for IVCUs
type Project struct {
	ID              uuid.UUID              `json:"id"`
	Name            string                 `json:"name"`
	OwnerID         uuid.UUID              `json:"owner_id"`
	OrgID           *uuid.UUID             `json:"org_id,omitempty"`
	SecurityContext string                 `json:"security_context"`
	Settings        map[string]interface{} `json:"settings"`
	CreatedAt       time.Time              `json:"created_at"`
	UpdatedAt       time.Time              `json:"updated_at"`
}

// Organization represents a group of users
type Organization struct {
	ID              uuid.UUID              `json:"id"`
	Name            string                 `json:"name"`
	SecurityContext string                 `json:"security_context"`
	Settings        map[string]interface{} `json:"settings"`
	CreatedAt       time.Time              `json:"created_at"`
	UpdatedAt       time.Time              `json:"updated_at"`
}

// ProjectMember represents a user's role in a project
type ProjectMember struct {
	ProjectID uuid.UUID `json:"project_id"`
	UserID    uuid.UUID `json:"user_id"`
	Role      string    `json:"role"` // viewer, editor, admin
	AddedAt   time.Time `json:"added_at"`
}

// GenerationLog tracks generation costs
type GenerationLog struct {
	ID        uuid.UUID `json:"id"`
	IVCUID    uuid.UUID `json:"ivcu_id"`
	ModelID   string    `json:"model_id"`
	TokensIn  int       `json:"tokens_in"`
	TokensOut int       `json:"tokens_out"`
	LatencyMs int       `json:"latency_ms"`
	Cost      float64   `json:"cost"`
	CreatedAt time.Time `json:"created_at"`
}

// UserSkill represents a user's proficiency in a specific skill
type UserSkill struct {
	UserID      uuid.UUID `json:"user_id"`
	Skill       string    `json:"skill"`
	Proficiency int       `json:"proficiency"` // 1-10
	LastUpdated time.Time `json:"last_updated"`
}

// LearnerProfile aggregates user skills
type LearnerProfile struct {
	UserID      uuid.UUID      `json:"user_id"`
	GlobalLevel string         `json:"global_level"` // novice, intermediate, expert
	Skills      map[string]int `json:"skills"`
	LastUpdated time.Time      `json:"last_updated"`
}
