"""
ProofCertificate Activity for Temporal Workflows

Activity that issues cryptographic proof certificates after verification.
"""
from datetime import datetime
from typing import Dict, Any, List
from temporalio import activity

from proof_certificate import (
    create_proof_certificate,
    VerificationLevel,
    ProofCertificate
)


@activity.defn
async def issue_proof_certificate_activity(
    ivcu_id: str,
    sdo_id: str,
    code: str,
    verification_results: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Issue a cryptographic proof certificate for verified code.
    
    Args:
        ivcu_id: IVCU identifier
        sdo_id: SDO identifier
        code: The verified code
        verification_results: List of tier verification results
        
    Returns:
        Certificate data including ID, signature, and status
    """
    try:
        # Format results for certificate
        formatted_results = []
        for vr in verification_results:
            formatted_results.append({
                "tier": vr.get("tier", "syntax"),
                "passed": vr.get("passed", False),
                "confidence": vr.get("confidence", 0.0),
                "timestamp": vr.get("timestamp", datetime.utcnow().isoformat()),
                "details": vr.get("details", {})
            })
        
        # Issue certificate
        cert = create_proof_certificate(
            ivcu_id=ivcu_id,
            sdo_id=sdo_id,
            code=code,
            verification_results=formatted_results
        )
        
        return {
            "certificate_id": cert.id,
            "code_hash": cert.code_hash,
            "overall_passed": cert.overall_passed,
            "overall_confidence": cert.overall_confidence,
            "signature": cert.signature,
            "issued_at": cert.issued_at.isoformat(),
            "expires_at": cert.expires_at.isoformat(),
            "status": cert.status.value,
            "tiers_verified": [vr["tier"] for vr in formatted_results if vr["passed"]]
        }
        
    except Exception as e:
        return {
            "certificate_id": None,
            "error": str(e),
            "overall_passed": False
        }
