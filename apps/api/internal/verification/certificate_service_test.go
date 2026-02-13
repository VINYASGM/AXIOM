package verification

import (
	"context"
	"encoding/hex"
	"testing"

	"github.com/axiom/api/internal/models"
	"github.com/google/uuid"
)

func TestGenerateCertificate(t *testing.T) {
	// Setup
	secretKey := "test-secret-key-123"
	service := NewCertificateService(secretKey)
	ctx := context.Background()

	// Test Data
	ivcuID := uuid.New()
	intentID := uuid.New()
	code := "def hello(): print('world')"
	proofType := models.ProofTypeContractCompliance
	verifierResults := []models.VerifierResult{
		{
			Name:       "test-verifier",
			Passed:     true,
			Confidence: 0.95,
		},
	}

	// Execution
	cert, err := service.GenerateCertificate(ctx, ivcuID, intentID, code, proofType, verifierResults)

	// Assertions
	if err != nil {
		t.Fatalf("GenerateCertificate failed: %v", err)
	}

	if cert == nil {
		t.Fatal("Certificate is nil")
	}

	if cert.IVCUID != ivcuID {
		t.Errorf("Expected IVCUID %v, got %v", ivcuID, cert.IVCUID)
	}

	if cert.IntentID != intentID {
		t.Errorf("Expected IntentID %v, got %v", intentID, cert.IntentID)
	}

	if cert.ProofType != proofType {
		t.Errorf("Expected ProofType %v, got %v", proofType, cert.ProofType)
	}

	// Verify Code Hash (SHA256 of code)
	// "def hello(): print('world')"
	// sha256sum: 5920...
	if cert.CodeHash == "" {
		t.Error("CodeHash is empty")
	}

	// Verify Signatures
	if len(cert.VerifierSignatures) != 1 {
		t.Errorf("Expected 1 verifier signature, got %d", len(cert.VerifierSignatures))
	} else {
		sig := cert.VerifierSignatures[0]
		if sig.Verifier != "test-verifier" {
			t.Errorf("Expected verifier name 'test-verifier', got %s", sig.Verifier)
		}
		if sig.Signature == "" {
			t.Error("Verifier signature is empty")
		}
	}

	// Verify Hash Chain
	if cert.HashChain == "" {
		t.Error("HashChain is empty")
	}

	// Verify Certificate Signature
	if len(cert.Signature) == 0 {
		t.Error("Certificate signature is empty")
	}

	// Verify Integrity (Re-compute signature)
	// We need to re-compute the hash chain and sign it to check if it matches
	computedHashChain := service.computeHashChain(cert)
	if computedHashChain != cert.HashChain {
		t.Errorf("HashChain mismatch. Algo produced %s but cert has %s", computedHashChain, cert.HashChain)
	}

	expectedSig := service.sign(cert.HashChain)
	if hex.EncodeToString(cert.Signature) != expectedSig { // Note: Certificate.Signature is []byte in struct but sign returns string hex?
		// Wait, looking at certificate_service.go:
		// cert.Signature = []byte(s.sign(cert.HashChain))
		// s.sign returns string (hex encoded).
		// So cert.Signature is []byte("hex_string").
		// Let's verify this conversion.

		actualSigStr := string(cert.Signature)
		if actualSigStr != expectedSig {
			t.Errorf("Signature mismatch. Expected %s, got %s", expectedSig, actualSigStr)
		}
	}
}

func TestCertificateIntegrity(t *testing.T) {
	service := NewCertificateService("secret")
	ctx := context.Background()

	cert, _ := service.GenerateCertificate(
		ctx, uuid.New(), uuid.New(), "code", models.ProofTypeTypeSafety, []models.VerifierResult{},
	)

	// Tamper with the certificate
	cert.CodeHash = "tampered_hash"

	// Re-verify (Logic normally works by re-computing hash chain and comparing with signature)
	// Since we don't have a specific "VerifyCertificate" method exposed publically in the service
	// (we only saw GenerateCertificate helpers), we can just manually check if our manual verify fails.

	validChain := service.computeHashChain(cert)

	// The certificate's existing HashChain should NOT match the new validChain derived from tampered data
	if validChain == cert.HashChain {
		t.Error("Tampered certificate should have different hash chain")
	}
}
