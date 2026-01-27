"""
Proof Bundle for Export/Import

JSON-based proof bundle format for portable verification proofs.
"""
import json
import base64
import hashlib
import time
from typing import Dict, Any, Optional
from dataclasses import dataclass

from .proof_generator import VerificationProof, get_proof_generator


@dataclass
class ProofBundle:
    """
    Portable proof bundle for export/import.
    
    Contains everything needed to independently verify an IVCU:
    - Code
    - Verification proof
    - Signature
    - Metadata
    """
    version: str
    ivcu_id: str
    candidate_id: str
    code: str
    code_hash: str
    proof: Dict[str, Any]
    public_key: str
    created_at: str
    tests: Optional[str] = None
    
    def to_json(self, indent: int = 2) -> str:
        """Export as JSON string."""
        return json.dumps({
            "version": self.version,
            "ivcu_id": self.ivcu_id,
            "candidate_id": self.candidate_id,
            "code": self.code,
            "code_hash": self.code_hash,
            "proof": self.proof,
            "public_key": self.public_key,
            "created_at": self.created_at,
            "tests": self.tests
        }, indent=indent)
    
    def to_bytes(self) -> bytes:
        """Export as bytes (minified JSON)."""
        return json.dumps({
            "version": self.version,
            "ivcu_id": self.ivcu_id,
            "candidate_id": self.candidate_id,
            "code": self.code,
            "code_hash": self.code_hash,
            "proof": self.proof,
            "public_key": self.public_key,
            "created_at": self.created_at,
            "tests": self.tests
        }, separators=(',', ':')).encode('utf-8')
    
    @classmethod
    def from_json(cls, json_str: str) -> "ProofBundle":
        """Import from JSON string."""
        data = json.loads(json_str)
        return cls(
            version=data["version"],
            ivcu_id=data["ivcu_id"],
            candidate_id=data["candidate_id"],
            code=data["code"],
            code_hash=data["code_hash"],
            proof=data["proof"],
            public_key=data["public_key"],
            created_at=data["created_at"],
            tests=data.get("tests")
        )
    
    @classmethod
    def from_bytes(cls, data: bytes) -> "ProofBundle":
        """Import from bytes."""
        return cls.from_json(data.decode('utf-8'))


class ProofBundler:
    """
    Creates and validates proof bundles.
    """
    
    CURRENT_VERSION = "1.0"
    
    def __init__(self):
        self.proof_generator = get_proof_generator()
    
    async def create_bundle(
        self,
        ivcu_id: str,
        candidate_id: str,
        code: str,
        verification_result: Dict[str, Any],
        contracts: Optional[list] = None,
        tests: Optional[str] = None
    ) -> ProofBundle:
        """
        Create a proof bundle from verification results.
        
        Args:
            ivcu_id: IVCU identifier
            candidate_id: Candidate identifier
            code: Source code
            verification_result: Verification orchestra result
            contracts: Optional contracts for SMT verification
            tests: Optional test code
            
        Returns:
            ProofBundle ready for export
        """
        # Generate proof
        proof = await self.proof_generator.generate_proof(
            ivcu_id=ivcu_id,
            candidate_id=candidate_id,
            code=code,
            verification_result=verification_result,
            contracts=contracts,
            sign=True
        )
        
        return ProofBundle(
            version=self.CURRENT_VERSION,
            ivcu_id=ivcu_id,
            candidate_id=candidate_id,
            code=code,
            code_hash=proof.code_hash,
            proof=proof.to_dict(),
            public_key=proof.public_key,
            created_at=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            tests=tests
        )
    
    def verify_bundle(
        self,
        bundle: ProofBundle,
        public_key_bytes: Optional[bytes] = None
    ) -> Dict[str, Any]:
        """
        Verify a proof bundle.
        
        Args:
            bundle: The proof bundle to verify
            public_key_bytes: Optional external public key
            
        Returns:
            Verification results
        """
        results = {
            "valid": True,
            "version_valid": False,
            "hash_valid": False,
            "signature_valid": False,
            "errors": []
        }
        
        # Check version
        if bundle.version in ["1.0"]:
            results["version_valid"] = True
        else:
            results["valid"] = False
            results["errors"].append(f"Unknown bundle version: {bundle.version}")
            return results
        
        # Verify code hash
        expected_hash = f"sha256:{hashlib.sha256(bundle.code.encode()).hexdigest()}"
        results["hash_valid"] = (bundle.code_hash == expected_hash)
        
        if not results["hash_valid"]:
            results["valid"] = False
            results["errors"].append("Code hash mismatch - code may have been tampered")
            return results
        
        # Verify signature in proof
        proof_data = bundle.proof
        signature_hex = proof_data.get("signature", "")
        
        if signature_hex:
            try:
                signature = bytes.fromhex(signature_hex)
                
                # Use provided key or key from bundle
                if public_key_bytes is None and bundle.public_key:
                    # The public key in bundle is PEM format
                    # For now, trust it (in production, validate against trusted keystore)
                    pass
                
                results["signature_valid"] = self.proof_generator.proof_signer.verify_signature(
                    proof_data,
                    signature,
                    public_key_bytes
                )
                
                if not results["signature_valid"]:
                    results["valid"] = False
                    results["errors"].append("Invalid signature")
                    
            except Exception as e:
                results["valid"] = False
                results["signature_valid"] = False
                results["errors"].append(f"Signature verification error: {str(e)}")
        else:
            # No signature - unsigned bundle
            results["signature_valid"] = True
            results["errors"].append("Warning: Bundle is unsigned")
        
        return results
    
    def export_to_file(self, bundle: ProofBundle, filepath: str) -> None:
        """Export bundle to a JSON file."""
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(bundle.to_json())
    
    def import_from_file(self, filepath: str) -> ProofBundle:
        """Import bundle from a JSON file."""
        with open(filepath, 'r', encoding='utf-8') as f:
            return ProofBundle.from_json(f.read())


# Singleton instance
_proof_bundler: Optional[ProofBundler] = None


def get_proof_bundler() -> ProofBundler:
    """Get or create proof bundler singleton."""
    global _proof_bundler
    if _proof_bundler is None:
        _proof_bundler = ProofBundler()
    return _proof_bundler
