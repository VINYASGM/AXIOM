"""
Verification Module for AXIOM
Multi-tier verification orchestra for generated code.

Tier 0: Tree-sitter syntax (<10ms)
Tier 1: Static analysis (<2s)
Tier 2: Dynamic testing (2-15s)
Tier 3: Formal verification (15s-5min)

Phase 6: Proof-Carrying Code (PCC) Architecture
"""
from .orchestra import VerificationOrchestra
from .result import VerificationResult, VerifierResult, VerificationTier, TierResult
from .tier0 import TreeSitterVerifier, verify_tier0, Tier0Result
from .tier1 import Tier1Verifier
from .tier2 import Tier2Verifier
from .tier3 import Tier3Verifier

# PCC Modules
from .smt_verifier import SMTVerifier, SMTResult, SMTStatus, get_smt_verifier
from .proof_signer import ProofSigner, SigningKey, get_proof_signer
from .proof_generator import ProofGenerator, VerificationProof, get_proof_generator
from .proof_bundle import ProofBundle, ProofBundler, get_proof_bundler

__all__ = [
    # Core verification
    "VerificationOrchestra",
    "VerificationResult",
    "VerifierResult",
    "VerificationTier",
    "TierResult",
    "TreeSitterVerifier",
    "verify_tier0",
    "Tier0Result",
    "Tier1Verifier",
    "Tier2Verifier",
    "Tier3Verifier",
    # PCC
    "SMTVerifier",
    "SMTResult",
    "SMTStatus",
    "get_smt_verifier",
    "ProofSigner",
    "SigningKey",
    "get_proof_signer",
    "ProofGenerator",
    "VerificationProof",
    "get_proof_generator",
    "ProofBundle",
    "ProofBundler",
    "get_proof_bundler",
]

