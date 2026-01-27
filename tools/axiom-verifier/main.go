/*
AXIOM Verifier CLI

Standalone tool for verifying AXIOM proof bundles.
Third-party verification without re-running generation.

Usage:

	axiom-verifier verify <bundle.json> [--public-key <key.pem>]
	axiom-verifier inspect <bundle.json>
	axiom-verifier extract <bundle.json> --output <dir>
*/
package main

import (
	"crypto/ed25519"
	"crypto/sha256"
	"crypto/x509"
	"encoding/hex"
	"encoding/json"
	"encoding/pem"
	"fmt"
	"io"
	"os"
)

// ProofBundle represents the exported proof bundle
type ProofBundle struct {
	Version     string          `json:"version"`
	IVCUID      string          `json:"ivcu_id"`
	CandidateID string          `json:"candidate_id"`
	Code        string          `json:"code"`
	CodeHash    string          `json:"code_hash"`
	Proof       json.RawMessage `json:"proof"`
	PublicKey   string          `json:"public_key"`
	CreatedAt   string          `json:"created_at"`
	Tests       string          `json:"tests,omitempty"`
}

// VerificationProof represents the proof structure
type VerificationProof struct {
	ProofID           string                 `json:"proof_id"`
	IVCUID            string                 `json:"ivcu_id"`
	CandidateID       string                 `json:"candidate_id"`
	CodeHash          string                 `json:"code_hash"`
	Timestamp         int64                  `json:"timestamp"`
	Version           string                 `json:"version"`
	Signature         string                 `json:"signature"`
	SignerID          string                 `json:"signer_id"`
	PublicKey         string                 `json:"public_key"`
	OverallConfidence float64                `json:"overall_confidence"`
	TierProofs        []TierProof            `json:"tier_proofs"`
	SMTProof          map[string]interface{} `json:"smt_proof,omitempty"`
	Metadata          map[string]string      `json:"metadata"`
}

// TierProof represents a verification tier proof
type TierProof struct {
	Tier            string          `json:"tier"`
	Passed          bool            `json:"passed"`
	Confidence      float64         `json:"confidence"`
	ExecutionTimeMs float64         `json:"execution_time_ms"`
	Verifiers       []VerifierProof `json:"verifiers"`
}

// VerifierProof represents an individual verifier's proof
type VerifierProof struct {
	VerifierName    string            `json:"verifier_name"`
	VerifierVersion string            `json:"verifier_version"`
	Passed          bool              `json:"passed"`
	Confidence      float64           `json:"confidence"`
	Errors          []string          `json:"errors"`
	Warnings        []string          `json:"warnings"`
	Details         map[string]string `json:"details"`
}

// VerificationResult holds the result of verification
type VerificationResult struct {
	Valid          bool     `json:"valid"`
	HashValid      bool     `json:"hash_valid"`
	SignatureValid bool     `json:"signature_valid"`
	Errors         []string `json:"errors"`
}

func main() {
	if len(os.Args) < 3 {
		printUsage()
		os.Exit(1)
	}

	command := os.Args[1]
	bundlePath := os.Args[2]

	switch command {
	case "verify":
		publicKeyPath := ""
		for i, arg := range os.Args {
			if arg == "--public-key" && i+1 < len(os.Args) {
				publicKeyPath = os.Args[i+1]
			}
		}
		verifyBundle(bundlePath, publicKeyPath)
	case "inspect":
		inspectBundle(bundlePath)
	case "extract":
		outputDir := "."
		for i, arg := range os.Args {
			if arg == "--output" && i+1 < len(os.Args) {
				outputDir = os.Args[i+1]
			}
		}
		extractBundle(bundlePath, outputDir)
	default:
		printUsage()
		os.Exit(1)
	}
}

func printUsage() {
	fmt.Println(`AXIOM Verifier CLI

Usage:
  axiom-verifier verify <bundle.json> [--public-key <key.pem>]
  axiom-verifier inspect <bundle.json>
  axiom-verifier extract <bundle.json> --output <dir>

Commands:
  verify   Verify a proof bundle's integrity and signature
  inspect  Display bundle contents and proof details
  extract  Extract code and tests from a bundle`)
}

func verifyBundle(bundlePath, publicKeyPath string) {
	bundle, err := loadBundle(bundlePath)
	if err != nil {
		fmt.Printf("❌ Error loading bundle: %v\n", err)
		os.Exit(1)
	}

	result := VerificationResult{
		Valid:          true,
		HashValid:      false,
		SignatureValid: false,
		Errors:         []string{},
	}

	// Verify code hash
	expectedHash := computeCodeHash(bundle.Code)
	result.HashValid = bundle.CodeHash == expectedHash

	if !result.HashValid {
		result.Valid = false
		result.Errors = append(result.Errors, "Code hash mismatch - code may have been tampered")
	}

	// Parse proof
	var proof VerificationProof
	if err := json.Unmarshal(bundle.Proof, &proof); err != nil {
		result.Valid = false
		result.Errors = append(result.Errors, fmt.Sprintf("Failed to parse proof: %v", err))
	} else if proof.Signature != "" {
		// Verify signature
		var publicKey ed25519.PublicKey

		if publicKeyPath != "" {
			publicKey, err = loadPublicKey(publicKeyPath)
			if err != nil {
				result.Errors = append(result.Errors, fmt.Sprintf("Failed to load public key: %v", err))
			}
		} else if bundle.PublicKey != "" {
			publicKey, err = parsePublicKeyPEM(bundle.PublicKey)
			if err != nil {
				result.Errors = append(result.Errors, fmt.Sprintf("Failed to parse embedded public key: %v", err))
			}
		}

		if publicKey != nil {
			// Create canonical representation for verification
			canonical := createCanonical(proof)
			signatureBytes, err := hex.DecodeString(proof.Signature)
			if err != nil {
				result.Errors = append(result.Errors, "Invalid signature format")
				result.Valid = false
			} else {
				result.SignatureValid = ed25519.Verify(publicKey, canonical, signatureBytes)
				if !result.SignatureValid {
					result.Valid = false
					result.Errors = append(result.Errors, "Signature verification failed")
				}
			}
		}
	} else {
		result.SignatureValid = true // No signature to verify
		result.Errors = append(result.Errors, "Warning: Bundle is unsigned")
	}

	// Output result
	fmt.Println("\n═══════════════════════════════════════════════════════════════")
	fmt.Println("                    AXIOM Proof Verification")
	fmt.Println("═══════════════════════════════════════════════════════════════")
	fmt.Printf("Bundle: %s\n", bundlePath)
	fmt.Printf("IVCU:   %s\n", bundle.IVCUID)
	fmt.Println("───────────────────────────────────────────────────────────────")

	if result.Valid {
		fmt.Println("✅ VERIFICATION PASSED")
	} else {
		fmt.Println("❌ VERIFICATION FAILED")
	}

	fmt.Printf("   Hash Valid:      %v\n", boolIcon(result.HashValid))
	fmt.Printf("   Signature Valid: %v\n", boolIcon(result.SignatureValid))

	if len(result.Errors) > 0 {
		fmt.Println("\nErrors/Warnings:")
		for _, err := range result.Errors {
			fmt.Printf("   • %s\n", err)
		}
	}

	fmt.Println("═══════════════════════════════════════════════════════════════")

	if !result.Valid {
		os.Exit(1)
	}
}

func inspectBundle(bundlePath string) {
	bundle, err := loadBundle(bundlePath)
	if err != nil {
		fmt.Printf("Error loading bundle: %v\n", err)
		os.Exit(1)
	}

	var proof VerificationProof
	json.Unmarshal(bundle.Proof, &proof)

	fmt.Println("\n═══════════════════════════════════════════════════════════════")
	fmt.Println("                    AXIOM Proof Bundle")
	fmt.Println("═══════════════════════════════════════════════════════════════")
	fmt.Printf("Version:     %s\n", bundle.Version)
	fmt.Printf("IVCU ID:     %s\n", bundle.IVCUID)
	fmt.Printf("Candidate:   %s\n", bundle.CandidateID)
	fmt.Printf("Code Hash:   %s\n", bundle.CodeHash)
	fmt.Printf("Created:     %s\n", bundle.CreatedAt)
	fmt.Printf("Code Size:   %d bytes\n", len(bundle.Code))
	fmt.Println("───────────────────────────────────────────────────────────────")
	fmt.Println("Proof Details:")
	fmt.Printf("   Proof ID:   %s\n", proof.ProofID)
	fmt.Printf("   Confidence: %.2f%%\n", proof.OverallConfidence*100)
	fmt.Printf("   Signed By:  %s\n", proof.SignerID)
	fmt.Printf("   Tiers:      %d\n", len(proof.TierProofs))

	if len(proof.TierProofs) > 0 {
		fmt.Println("\nTier Results:")
		for _, tier := range proof.TierProofs {
			status := "✅"
			if !tier.Passed {
				status = "❌"
			}
			fmt.Printf("   %s %s: %.2f%% confidence (%.1fms)\n",
				status, tier.Tier, tier.Confidence*100, tier.ExecutionTimeMs)
		}
	}

	if proof.SMTProof != nil {
		fmt.Println("\nSMT Verification:")
		fmt.Printf("   Solver: %v\n", proof.SMTProof["solver"])
		fmt.Printf("   Status: %v\n", proof.SMTProof["status"])
	}

	fmt.Println("═══════════════════════════════════════════════════════════════")
}

func extractBundle(bundlePath, outputDir string) {
	bundle, err := loadBundle(bundlePath)
	if err != nil {
		fmt.Printf("Error loading bundle: %v\n", err)
		os.Exit(1)
	}

	if err := os.MkdirAll(outputDir, 0755); err != nil {
		fmt.Printf("Error creating output directory: %v\n", err)
		os.Exit(1)
	}

	// Write code
	codePath := fmt.Sprintf("%s/code.py", outputDir)
	if err := os.WriteFile(codePath, []byte(bundle.Code), 0644); err != nil {
		fmt.Printf("Error writing code: %v\n", err)
		os.Exit(1)
	}
	fmt.Printf("✅ Extracted code to %s\n", codePath)

	// Write tests if present
	if bundle.Tests != "" {
		testsPath := fmt.Sprintf("%s/tests.py", outputDir)
		if err := os.WriteFile(testsPath, []byte(bundle.Tests), 0644); err != nil {
			fmt.Printf("Error writing tests: %v\n", err)
			os.Exit(1)
		}
		fmt.Printf("✅ Extracted tests to %s\n", testsPath)
	}

	// Write proof
	proofPath := fmt.Sprintf("%s/proof.json", outputDir)
	if err := os.WriteFile(proofPath, bundle.Proof, 0644); err != nil {
		fmt.Printf("Error writing proof: %v\n", err)
		os.Exit(1)
	}
	fmt.Printf("✅ Extracted proof to %s\n", proofPath)
}

func loadBundle(path string) (*ProofBundle, error) {
	file, err := os.Open(path)
	if err != nil {
		return nil, err
	}
	defer file.Close()

	data, err := io.ReadAll(file)
	if err != nil {
		return nil, err
	}

	var bundle ProofBundle
	if err := json.Unmarshal(data, &bundle); err != nil {
		return nil, err
	}

	return &bundle, nil
}

func computeCodeHash(code string) string {
	hash := sha256.Sum256([]byte(code))
	return "sha256:" + hex.EncodeToString(hash[:])
}

func loadPublicKey(path string) (ed25519.PublicKey, error) {
	data, err := os.ReadFile(path)
	if err != nil {
		return nil, err
	}
	return parsePublicKeyPEM(string(data))
}

func parsePublicKeyPEM(pemData string) (ed25519.PublicKey, error) {
	block, _ := pem.Decode([]byte(pemData))
	if block == nil {
		return nil, fmt.Errorf("failed to decode PEM block")
	}

	pub, err := x509.ParsePKIXPublicKey(block.Bytes)
	if err != nil {
		return nil, err
	}

	ed25519Key, ok := pub.(ed25519.PublicKey)
	if !ok {
		return nil, fmt.Errorf("not an Ed25519 public key")
	}

	return ed25519Key, nil
}

func createCanonical(proof VerificationProof) []byte {
	// Create canonical JSON representation (without signature)
	canonical := map[string]interface{}{
		"proof_id":           proof.ProofID,
		"ivcu_id":            proof.IVCUID,
		"candidate_id":       proof.CandidateID,
		"code_hash":          proof.CodeHash,
		"timestamp":          proof.Timestamp,
		"version":            proof.Version,
		"overall_confidence": proof.OverallConfidence,
		"tier_proofs":        proof.TierProofs,
		"smt_proof":          proof.SMTProof,
		"metadata":           proof.Metadata,
	}

	data, _ := json.Marshal(canonical)
	return data
}

func boolIcon(b bool) string {
	if b {
		return "✅"
	}
	return "❌"
}
