"""
Proof Generator for Proof-Carrying Code

Generates cryptographically signed verification proofs.
"""
import hashlib
import time
import uuid
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field, asdict

from .smt_verifier import get_smt_verifier, SMTResult, SMTStatus
from .proof_signer import get_proof_signer


@dataclass
class VerifierProof:
    """Proof from an individual verifier."""
    verifier_name: str
    verifier_version: str
    passed: bool
    confidence: float
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    proof_data: bytes = b""
    details: Dict[str, str] = field(default_factory=dict)


@dataclass
class TierProof:
    """Proof for a single verification tier."""
    tier: str
    passed: bool
    confidence: float
    execution_time_ms: float
    verifiers: List[VerifierProof] = field(default_factory=list)


@dataclass
class SMTProofData:
    """SMT Solver proof data."""
    solver: str
    solver_version: str
    status: str
    solve_time_ms: float
    proof_bytes: bytes
    assertions: List[Dict[str, Any]]


@dataclass
class VerificationProof:
    """Complete verification proof that travels with code."""
    proof_id: str
    ivcu_id: str
    candidate_id: str
    code_hash: str
    timestamp: int
    version: str = "1.0"
    
    tier_proofs: List[TierProof] = field(default_factory=list)
    
    signature: bytes = b""
    signer_id: str = ""
    public_key: str = ""
    
    smt_proof: Optional[SMTProofData] = None
    
    overall_confidence: float = 0.0
    metadata: Dict[str, str] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "proof_id": self.proof_id,
            "ivcu_id": self.ivcu_id,
            "candidate_id": self.candidate_id,
            "code_hash": self.code_hash,
            "timestamp": self.timestamp,
            "version": self.version,
            "tier_proofs": [
                {
                    "tier": tp.tier,
                    "passed": tp.passed,
                    "confidence": tp.confidence,
                    "execution_time_ms": tp.execution_time_ms,
                    "verifiers": [asdict(v) for v in tp.verifiers]
                }
                for tp in self.tier_proofs
            ],
            "signature": self.signature.hex() if self.signature else "",
            "signer_id": self.signer_id,
            "public_key": self.public_key,
            "smt_proof": asdict(self.smt_proof) if self.smt_proof else None,
            "overall_confidence": self.overall_confidence,
            "metadata": self.metadata
        }


class ProofGenerator:
    """
    Generates verification proofs for IVCUs.
    
    Combines verification results, SMT proofs, and cryptographic signatures
    into a single proof bundle.
    """
    
    def __init__(self):
        self.smt_verifier = get_smt_verifier()
        self.proof_signer = get_proof_signer()
    
    async def generate_proof(
        self,
        ivcu_id: str,
        candidate_id: str,
        code: str,
        verification_result: Dict[str, Any],
        contracts: Optional[List[Dict[str, Any]]] = None,
        sign: bool = True
    ) -> VerificationProof:
        """
        Generate a complete verification proof.
        
        Args:
            ivcu_id: IVCU identifier
            candidate_id: Candidate identifier
            code: Verified source code
            verification_result: Result from verification orchestra
            contracts: Optional contracts for SMT verification
            sign: Whether to cryptographically sign the proof
            
        Returns:
            VerificationProof
        """
        # Generate code hash
        code_hash = f"sha256:{hashlib.sha256(code.encode()).hexdigest()}"
        
        # Extract tier proofs from verification result
        tier_proofs = self._extract_tier_proofs(verification_result)
        
        # Run SMT verification if contracts provided
        smt_proof = None
        if contracts:
            smt_result = await self.smt_verifier.verify_contracts(code, contracts)
            if smt_result.status != SMTStatus.DISABLED:
                smt_proof = SMTProofData(
                    solver=smt_result.solver,
                    solver_version=smt_result.solver_version,
                    status=smt_result.status.value,
                    solve_time_ms=smt_result.solve_time_ms,
                    proof_bytes=smt_result.proof_bytes,
                    assertions=[
                        {
                            "name": a.name,
                            "expression": a.expression,
                            "type": a.assertion_type,
                            "verified": a.verified
                        }
                        for a in smt_result.assertions
                    ]
                )
        
        # Calculate overall confidence
        overall_confidence = self._calculate_confidence(tier_proofs, smt_proof)
        
        # Create proof
        proof = VerificationProof(
            proof_id=str(uuid.uuid4()),
            ivcu_id=ivcu_id,
            candidate_id=candidate_id,
            code_hash=code_hash,
            timestamp=int(time.time() * 1000),
            tier_proofs=tier_proofs,
            smt_proof=smt_proof,
            overall_confidence=overall_confidence,
            metadata={
                "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "generator_version": "1.0.0"
            }
        )
        
        # Sign if requested
        if sign:
            proof_dict = proof.to_dict()
            signature, signer_id = self.proof_signer.sign_proof(proof_dict)
            proof.signature = signature
            proof.signer_id = signer_id
            proof.public_key = self.proof_signer.get_public_key_pem()
        
        return proof
    
    def verify_proof(
        self,
        proof: VerificationProof,
        code: str,
        public_key_bytes: Optional[bytes] = None
    ) -> Dict[str, bool]:
        """
        Verify a proof independently.
        
        Args:
            proof: The verification proof to verify
            code: Original code to check hash
            public_key_bytes: Optional public key for signature verification
            
        Returns:
            Dictionary with validation results
        """
        results = {
            "valid": True,
            "hash_valid": False,
            "signature_valid": False
        }
        
        # Verify code hash
        expected_hash = f"sha256:{hashlib.sha256(code.encode()).hexdigest()}"
        results["hash_valid"] = (proof.code_hash == expected_hash)
        
        if not results["hash_valid"]:
            results["valid"] = False
            return results
        
        # Verify signature
        if proof.signature:
            proof_dict = proof.to_dict()
            results["signature_valid"] = self.proof_signer.verify_signature(
                proof_dict,
                proof.signature,
                public_key_bytes
            )
            if not results["signature_valid"]:
                results["valid"] = False
        else:
            results["signature_valid"] = True  # No signature to verify
        
        return results
    
    def _extract_tier_proofs(
        self,
        verification_result: Dict[str, Any]
    ) -> List[TierProof]:
        """Extract tier proofs from verification result."""
        tier_proofs = []
        
        # Map from verification result structure
        verifier_results = verification_result.get("verifier_results", [])
        
        # Group by tier
        tier_map: Dict[str, List[Dict]] = {}
        for vr in verifier_results:
            tier = vr.get("tier", "tier1")
            if tier not in tier_map:
                tier_map[tier] = []
            tier_map[tier].append(vr)
        
        # Create TierProof for each tier
        for tier_name in ["tier0", "tier1", "tier2", "tier3"]:
            tier_results = tier_map.get(tier_name, [])
            if not tier_results:
                continue
            
            verifiers = []
            tier_passed = True
            tier_confidence = 1.0
            total_time = 0.0
            
            for vr in tier_results:
                verifier = VerifierProof(
                    verifier_name=vr.get("verifier", "unknown"),
                    verifier_version=vr.get("version", "1.0"),
                    passed=vr.get("passed", False),
                    confidence=vr.get("confidence", 0.0),
                    errors=vr.get("errors", []),
                    warnings=vr.get("warnings", []),
                    details=vr.get("details", {})
                )
                verifiers.append(verifier)
                
                if not verifier.passed:
                    tier_passed = False
                tier_confidence = min(tier_confidence, verifier.confidence)
                total_time += vr.get("duration_ms", 0)
            
            tier_proofs.append(TierProof(
                tier=tier_name,
                passed=tier_passed,
                confidence=tier_confidence,
                execution_time_ms=total_time,
                verifiers=verifiers
            ))
        
        return tier_proofs
    
    def _calculate_confidence(
        self,
        tier_proofs: List[TierProof],
        smt_proof: Optional[SMTProofData]
    ) -> float:
        """Calculate overall confidence from tier and SMT proofs."""
        if not tier_proofs:
            return 0.0
        
        # Weighted average of tier confidences
        weights = {"tier0": 0.1, "tier1": 0.3, "tier2": 0.4, "tier3": 0.2}
        
        total_weight = 0.0
        weighted_confidence = 0.0
        
        for tp in tier_proofs:
            weight = weights.get(tp.tier, 0.1)
            weighted_confidence += tp.confidence * weight
            total_weight += weight
        
        base_confidence = weighted_confidence / total_weight if total_weight > 0 else 0.0
        
        # Boost if SMT proof is SAT
        if smt_proof and smt_proof.status == "sat":
            base_confidence = min(1.0, base_confidence * 1.1)
        elif smt_proof and smt_proof.status == "unsat":
            base_confidence = min(base_confidence, 0.3)
        
        return round(base_confidence, 4)


# Singleton instance
_proof_generator: Optional[ProofGenerator] = None


def get_proof_generator() -> ProofGenerator:
    """Get or create proof generator singleton."""
    global _proof_generator
    if _proof_generator is None:
        _proof_generator = ProofGenerator()
    return _proof_generator
