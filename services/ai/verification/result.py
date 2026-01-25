"""
Verification Result Models
Data structures for verification outcomes.
"""
from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime
import uuid


class VerificationTier(str, Enum):
    """Verification tier levels"""
    TIER_1 = "tier_1"  # Syntax, types, lint (fast)
    TIER_2 = "tier_2"  # Unit tests, property tests (medium)
    TIER_3 = "tier_3"  # Formal verification, fuzzing (slow)


class VerifierResult(BaseModel):
    """Result from a single verifier"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    tier: VerificationTier
    passed: bool
    confidence: float = Field(ge=0.0, le=1.0)
    messages: List[str] = []
    errors: List[str] = []
    warnings: List[str] = []
    duration_ms: float = 0.0
    metadata: Dict[str, Any] = {}
    details: Dict[str, Any] = {}


class VerificationResult(BaseModel):
    """Aggregate result from verification orchestra"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    sdo_id: str
    candidate_id: Optional[str] = None
    
    # Overall status
    passed: bool = False
    confidence: float = 0.0
    
    # Tier results
    tier_1_passed: bool = False
    tier_2_passed: Optional[bool] = None
    tier_3_passed: Optional[bool] = None
    
    # Individual verifier results
    verifier_results: List[VerifierResult] = []
    
    # Summary
    total_errors: int = 0
    total_warnings: int = 0
    limitations: List[str] = []
    
    # Timing
    total_duration_ms: float = 0.0
    started_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    completed_at: Optional[str] = None
    
    def add_result(self, result: VerifierResult):
        """Add a verifier result and update aggregates"""
        self.verifier_results.append(result)
        self.total_errors += len(result.errors)
        self.total_warnings += len(result.warnings)
        self.total_duration_ms += result.duration_ms
        
        # Update tier status
        if result.tier == VerificationTier.TIER_1:
            if self.tier_1_passed is True or self.tier_1_passed is False:
                self.tier_1_passed = self.tier_1_passed and result.passed
            else:
                self.tier_1_passed = result.passed
        elif result.tier == VerificationTier.TIER_2:
            if self.tier_2_passed is None:
                self.tier_2_passed = result.passed
            else:
                self.tier_2_passed = self.tier_2_passed and result.passed
        elif result.tier == VerificationTier.TIER_3:
            if self.tier_3_passed is None:
                self.tier_3_passed = result.passed
            else:
                self.tier_3_passed = self.tier_3_passed and result.passed
    
    def finalize(self):
        """Calculate final confidence and status"""
        self.completed_at = datetime.utcnow().isoformat()
        
        # Calculate overall passed status
        self.passed = self.tier_1_passed
        if self.tier_2_passed is not None:
            self.passed = self.passed and self.tier_2_passed
        
        # Calculate weighted confidence
        if self.verifier_results:
            total_weight = 0.0
            weighted_sum = 0.0
            for r in self.verifier_results:
                weight = 1.0 if r.tier == VerificationTier.TIER_1 else 1.5 if r.tier == VerificationTier.TIER_2 else 2.0
                weighted_sum += r.confidence * weight
                total_weight += weight
            self.confidence = weighted_sum / total_weight if total_weight > 0 else 0.0
        
        return self
