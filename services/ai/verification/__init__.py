"""
Verification Module for AXIOM
Multi-tier verification orchestra for generated code.

Tier 0: Tree-sitter syntax (<10ms)
Tier 1: Static analysis (<2s)
Tier 2: Dynamic testing (2-15s)
Tier 3: Formal verification (15s-5min)
"""
from .orchestra import VerificationOrchestra
from .result import VerificationResult, VerifierResult, VerificationTier, TierResult
from .tier0 import TreeSitterVerifier, verify_tier0, Tier0Result
from .tier1 import Tier1Verifier
from .tier2 import Tier2Verifier
from .tier3 import Tier3Verifier

__all__ = [
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
]
