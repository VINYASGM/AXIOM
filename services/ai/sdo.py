"""
Semantic Development Object (SDO)
The core unit of AXIOM's AI logic. Encapsulates intent, state, and generation history.
"""
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any, Union
import time
import hashlib
from enum import Enum

class SDOStatus(str, Enum):
    DRAFT = "draft"
    PARSING = "parsing"
    PLANNING = "planning"
    GENERATING = "generating"
    VERIFYING = "verifying"
    VERIFIED = "verified"
    FAILED = "failed"

class Contract(BaseModel):
    type: str = Field(..., description="precondition, postcondition, invariant")
    description: str
    expression: Optional[str] = None

class GenerationStep(BaseModel):
    timestamp: float = Field(default_factory=time.time)
    step_type: str  # parse, plan, code, verify
    content: Dict[str, Any]
    confidence: float
    model_id: str


class Candidate(BaseModel):
    """A single code generation candidate"""
    id: str
    code: str
    confidence: float = 0.0
    model_id: str = "unknown"
    verification_score: float = 0.0
    verification_passed: bool = False
    pruned: bool = False
    reasoning: Optional[str] = None
    verification_result: Optional[Dict[str, Any]] = None
    created_at: float = Field(default_factory=time.time)


class SDO(BaseModel):
    """
    Semantic Development Object
    Maintains the state of a code generation task from intent to verified code.
    """
    id: str
    raw_intent: str
    status: SDOStatus = SDOStatus.DRAFT
    
    # Analysis
    parsed_intent: Optional[Dict[str, Any]] = None
    constraints: List[str] = []
    contracts: List[Contract] = []
    
    # Strategy
    generation_strategy: Optional[Dict[str, Any]] = None
    
    # Context
    retrieved_context: Optional[Dict[str, Any]] = None
    context_used: Optional[Dict[str, int]] = None
    
    # Generation
    language: str
    code: Optional[str] = None
    test_code: Optional[str] = None
    verification_result: Optional[Dict[str, Any]] = None
    
    # Parallel candidates
    candidates: List[Candidate] = []
    selected_candidate_id: Optional[str] = None
    
    # Metadata
    confidence: float = 0.0
    history: List[GenerationStep] = []
    created_at: float = Field(default_factory=time.time)
    updated_at: float = Field(default_factory=time.time)

    def add_step(self, step_type: str, content: Dict[str, Any], confidence: float, model: str):
        self.history.append(GenerationStep(
            step_type=step_type,
            content=content,
            confidence=confidence,
            model_id=model
        ))
        self.updated_at = time.time()
        
    def update_status(self, status: SDOStatus):
        self.status = status
        self.updated_at = time.time()

    def calculate_confidence(self) -> float:
        """
        Calculate overall confidence based on history and verification results.
        Simple weighted average for now.
        """
        if not self.history:
            return 0.0
            
        # Weights for different steps
        weights = {
            "parse": 0.2,
            "plan": 0.2,
            "code": 0.3,
            "verify": 0.3
        }
        
        total_score = 0.0
        total_weight = 0.0
        
        for step in self.history:
            w = weights.get(step.step_type, 0.1)
            total_score += step.confidence * w
            total_weight += w
            
        if total_weight == 0:
            return 0.0
            
        return min(total_score / total_weight, 1.0)
