"""
ProofCertificate - Cryptographic Verification Certificates (Phase 4)

Provides cryptographically verifiable proof of code verification.
Each certificate contains:
- Verification results hash
- Timestamp
- Signing authority
- Verification tiers passed
- Reproducibility metadata

Use cases:
- Audit trail for compliance
- Third-party verification trust
- Deployment gates requiring proof
"""
import hashlib
import json
import secrets
from datetime import datetime, timedelta
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any, Optional
from enum import Enum
import hmac


class VerificationLevel(str, Enum):
    """Verification levels for certificates."""
    SYNTAX = "syntax"
    SEMANTIC = "semantic"
    COVERAGE = "coverage"
    SECURITY = "security"
    INTEGRATION = "integration"


class CertificateStatus(str, Enum):
    """Status of a proof certificate."""
    VALID = "valid"
    EXPIRED = "expired"
    REVOKED = "revoked"
    PENDING = "pending"


@dataclass
class VerificationResult:
    """Individual verification result."""
    tier: VerificationLevel
    passed: bool
    confidence: float
    timestamp: datetime
    details: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "tier": self.tier.value,
            "passed": self.passed,
            "confidence": self.confidence,
            "timestamp": self.timestamp.isoformat(),
            "details": self.details
        }


@dataclass
class ProofCertificate:
    """
    Cryptographic proof of code verification.
    
    This certificate provides:
    - Tamper-evident record of verification
    - Chain of custody for audit
    - Trust anchor for deployment
    """
    id: str
    ivcu_id: str
    sdo_id: str
    code_hash: str  # SHA-256 of verified code
    
    # Verification details
    verifications: List[VerificationResult]
    overall_passed: bool
    overall_confidence: float
    
    # Certificate metadata
    issued_at: datetime
    expires_at: datetime
    issuer: str = "axiom-verification-authority"
    version: str = "1.0"
    
    # Signature
    signature: str = ""
    signature_algorithm: str = "HMAC-SHA256"
    
    # Status
    status: CertificateStatus = CertificateStatus.VALID
    revocation_reason: Optional[str] = None
    
    def __post_init__(self):
        if not self.signature:
            self.signature = self._generate_signature()
    
    def _generate_signature(self, secret_key: str = "axiom-cert-secret") -> str:
        """Generate HMAC signature for the certificate."""
        payload = self._get_payload_for_signing()
        signature = hmac.new(
            secret_key.encode(),
            payload.encode(),
            hashlib.sha256
        ).hexdigest()
        return signature
    
    def _get_payload_for_signing(self) -> str:
        """Get the payload used for signature generation."""
        data = {
            "id": self.id,
            "ivcu_id": self.ivcu_id,
            "sdo_id": self.sdo_id,
            "code_hash": self.code_hash,
            "overall_passed": self.overall_passed,
            "overall_confidence": self.overall_confidence,
            "issued_at": self.issued_at.isoformat(),
            "expires_at": self.expires_at.isoformat(),
            "issuer": self.issuer,
            "version": self.version,
            "verifications": [v.to_dict() for v in self.verifications]
        }
        return json.dumps(data, sort_keys=True)
    
    def verify_signature(self, secret_key: str = "axiom-cert-secret") -> bool:
        """Verify the certificate signature is valid."""
        expected = self._generate_signature(secret_key)
        return hmac.compare_digest(self.signature, expected)
    
    def is_valid(self) -> bool:
        """Check if certificate is currently valid."""
        if self.status != CertificateStatus.VALID:
            return False
        if datetime.utcnow() > self.expires_at:
            return False
        return self.verify_signature()
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize certificate to dictionary."""
        return {
            "id": self.id,
            "ivcu_id": self.ivcu_id,
            "sdo_id": self.sdo_id,
            "code_hash": self.code_hash,
            "verifications": [v.to_dict() for v in self.verifications],
            "overall_passed": self.overall_passed,
            "overall_confidence": self.overall_confidence,
            "issued_at": self.issued_at.isoformat(),
            "expires_at": self.expires_at.isoformat(),
            "issuer": self.issuer,
            "version": self.version,
            "signature": self.signature,
            "signature_algorithm": self.signature_algorithm,
            "status": self.status.value,
            "revocation_reason": self.revocation_reason
        }
    
    def to_pem(self) -> str:
        """Export certificate in PEM-like format."""
        cert_data = json.dumps(self.to_dict(), indent=2)
        import base64
        encoded = base64.b64encode(cert_data.encode()).decode()
        
        lines = []
        lines.append("-----BEGIN AXIOM PROOF CERTIFICATE-----")
        for i in range(0, len(encoded), 64):
            lines.append(encoded[i:i+64])
        lines.append("-----END AXIOM PROOF CERTIFICATE-----")
        
        return "\n".join(lines)


class CertificateAuthority:
    """
    Certificate Authority for issuing and managing ProofCertificates.
    """
    
    def __init__(
        self,
        issuer: str = "axiom-verification-authority",
        signing_key: str = None,
        validity_days: int = 365
    ):
        self.issuer = issuer
        self.signing_key = signing_key or secrets.token_hex(32)
        self.validity_days = validity_days
        self._issued_certs: Dict[str, ProofCertificate] = {}
        self._revoked_certs: set = set()
    
    def issue_certificate(
        self,
        ivcu_id: str,
        sdo_id: str,
        code: str,
        verifications: List[VerificationResult]
    ) -> ProofCertificate:
        """
        Issue a new proof certificate.
        
        Args:
            ivcu_id: IVCU identifier
            sdo_id: SDO identifier
            code: Verified code
            verifications: List of verification results
            
        Returns:
            Signed ProofCertificate
        """
        cert_id = f"cert-{secrets.token_hex(8)}"
        code_hash = hashlib.sha256(code.encode()).hexdigest()
        
        overall_passed = all(v.passed for v in verifications)
        overall_confidence = (
            sum(v.confidence for v in verifications) / len(verifications)
            if verifications else 0.0
        )
        
        now = datetime.utcnow()
        expires = now + timedelta(days=self.validity_days)
        
        cert = ProofCertificate(
            id=cert_id,
            ivcu_id=ivcu_id,
            sdo_id=sdo_id,
            code_hash=code_hash,
            verifications=verifications,
            overall_passed=overall_passed,
            overall_confidence=overall_confidence,
            issued_at=now,
            expires_at=expires,
            issuer=self.issuer,
            signature=""
        )
        
        # Sign with our key
        cert.signature = cert._generate_signature(self.signing_key)
        
        self._issued_certs[cert_id] = cert
        return cert
    
    def verify_certificate(self, cert: ProofCertificate) -> bool:
        """Verify a certificate is valid and not revoked."""
        if cert.id in self._revoked_certs:
            return False
        
        expected_sig = cert._generate_signature(self.signing_key)
        if not hmac.compare_digest(cert.signature, expected_sig):
            return False
        
        if datetime.utcnow() > cert.expires_at:
            return False
        
        return True
    
    def revoke_certificate(self, cert_id: str, reason: str = "unspecified") -> bool:
        """Revoke a certificate."""
        if cert_id not in self._issued_certs:
            return False
        
        self._revoked_certs.add(cert_id)
        cert = self._issued_certs[cert_id]
        cert.status = CertificateStatus.REVOKED
        cert.revocation_reason = reason
        return True
    
    def get_certificate(self, cert_id: str) -> Optional[ProofCertificate]:
        """Retrieve a certificate by ID."""
        return self._issued_certs.get(cert_id)


# Global CA instance
_certificate_authority: Optional[CertificateAuthority] = None


def get_certificate_authority() -> CertificateAuthority:
    """Get or create the global certificate authority."""
    global _certificate_authority
    if _certificate_authority is None:
        _certificate_authority = CertificateAuthority()
    return _certificate_authority


def create_proof_certificate(
    ivcu_id: str,
    sdo_id: str,
    code: str,
    verification_results: List[Dict[str, Any]]
) -> ProofCertificate:
    """
    Convenience function to create a proof certificate.
    
    Args:
        ivcu_id: IVCU identifier
        sdo_id: SDO identifier
        code: The verified code
        verification_results: List of verification result dicts
        
    Returns:
        Signed ProofCertificate
    """
    ca = get_certificate_authority()
    
    verifications = []
    for vr in verification_results:
        verifications.append(VerificationResult(
            tier=VerificationLevel(vr.get("tier", "syntax")),
            passed=vr.get("passed", False),
            confidence=vr.get("confidence", 0.0),
            timestamp=datetime.fromisoformat(vr.get("timestamp", datetime.utcnow().isoformat())),
            details=vr.get("details", {})
        ))
    
    return ca.issue_certificate(ivcu_id, sdo_id, code, verifications)
