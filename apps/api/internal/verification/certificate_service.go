package verification

import (
	"context"
	"crypto/hmac"
	"crypto/sha256"
	"encoding/hex"
	"fmt"
	"time"

	"github.com/axiom/api/internal/models"
	"github.com/google/uuid"
)

// CertificateService handles the creation and validation of proof certificates
type CertificateService struct {
	signingKey []byte
}

// NewCertificateService creating a new certificate service
func NewCertificateService(signingKey string) *CertificateService {
	return &CertificateService{
		signingKey: []byte(signingKey),
	}
}

// GenerateCertificate creates a new ProofCertificate for a verified IVCU
func (s *CertificateService) GenerateCertificate(
	ctx context.Context,
	ivcuID uuid.UUID,
	intentID uuid.UUID,
	code string,
	proofType models.ProofType,
	verifierResults []models.VerifierResult,
) (*models.ProofCertificate, error) {

	// 1. Compute Code Hash
	codeHash := s.computeHash([]byte(code))

	// 2. Compute AST Hash (Mock implementation for now, assuming code is AST source)
	// In a real implementation, this would parse the code and hash the AST structure
	astHash := s.computeHash([]byte(fmt.Sprintf("AST:%s", code)))

	// 3. Generate Verifier Signatures
	// In a real system, verifiers would sign their own results.
	// We simulate this by signing the verifier name + result
	verifierSignatures := make([]models.VerifierSignature, len(verifierResults))
	for i, result := range verifierResults {
		sigData := fmt.Sprintf("%s:%v:%f", result.Name, result.Passed, result.Confidence)
		verifierSignatures[i] = models.VerifierSignature{
			Verifier:  result.Name,
			Signature: s.sign(sigData),
			Timestamp: time.Now(),
		}
	}

	// 4. Create Certificate Structure
	cert := &models.ProofCertificate{
		ID:                 uuid.New(),
		IVCUID:             ivcuID,
		ProofType:          proofType,
		VerifierVersion:    "1.0.0",
		Timestamp:          time.Now(),
		IntentID:           intentID,
		ASTHash:            astHash,
		CodeHash:           codeHash,
		VerifierSignatures: verifierSignatures,
		Assertions:         []models.FormalAssertion{}, // Example: populated by formal verifier
		ProofData:          []byte("simulated_proof_data"),
		CreatedAt:          time.Now(),
	}

	// 5. Compute Hash Chain
	cert.HashChain = s.computeHashChain(cert)

	// 6. Sign the Certificate
	cert.Signature = []byte(s.sign(cert.HashChain))

	return cert, nil
}

// computeHash computes SHA-256 hash
func (s *CertificateService) computeHash(data []byte) string {
	hash := sha256.Sum256(data)
	return hex.EncodeToString(hash[:])
}

// sign creates an HMAC-SHA256 signature
func (s *CertificateService) sign(data string) string {
	h := hmac.New(sha256.New, s.signingKey)
	h.Write([]byte(data))
	return hex.EncodeToString(h.Sum(nil))
}

// computeHashChain computes the integrity hash of the certificate
func (s *CertificateService) computeHashChain(cert *models.ProofCertificate) string {
	// Concatenate critical fields to ensure integrity
	data := fmt.Sprintf("%s:%s:%s:%s",
		cert.CodeHash,
		cert.ASTHash,
		cert.IntentID.String(),
		cert.Timestamp.Format(time.RFC3339),
	)
	return s.computeHash([]byte(data))
}
