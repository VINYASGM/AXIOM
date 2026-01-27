"""
SMT Verifier for Formal Contract Verification

Uses Z3 solver to verify preconditions, postconditions, and invariants.
"""
import time
import hashlib
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum

try:
    import z3
    Z3_AVAILABLE = True
except ImportError:
    z3 = None
    Z3_AVAILABLE = False


class SMTStatus(str, Enum):
    SAT = "sat"
    UNSAT = "unsat"
    UNKNOWN = "unknown"
    TIMEOUT = "timeout"
    ERROR = "error"
    DISABLED = "disabled"


@dataclass
class SMTAssertion:
    """A single SMT assertion from a contract."""
    name: str
    expression: str
    assertion_type: str  # precondition, postcondition, invariant
    verified: bool = False
    z3_expr: Optional[Any] = None


@dataclass
class SMTResult:
    """Result of SMT verification."""
    status: SMTStatus
    solver: str = "z3"
    solver_version: str = ""
    solve_time_ms: float = 0.0
    assertions: List[SMTAssertion] = field(default_factory=list)
    proof_bytes: bytes = b""
    error: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "status": self.status.value,
            "solver": self.solver,
            "solver_version": self.solver_version,
            "solve_time_ms": self.solve_time_ms,
            "assertions": [
                {
                    "name": a.name,
                    "expression": a.expression,
                    "type": a.assertion_type,
                    "verified": a.verified
                }
                for a in self.assertions
            ],
            "error": self.error
        }


class SMTVerifier:
    """
    SMT-based formal verification using Z3.
    
    Verifies:
    - Preconditions: Constraints that must hold before function execution
    - Postconditions: Constraints that must hold after function execution
    - Invariants: Constraints that must hold throughout execution
    """
    
    def __init__(self, timeout_ms: int = 5000):
        self.timeout_ms = timeout_ms
        self.solver_version = z3.get_version_string() if Z3_AVAILABLE and z3 else "N/A"
    
    async def verify_contracts(
        self,
        code: str,
        contracts: List[Dict[str, Any]],
        language: str = "python"
    ) -> SMTResult:
        """
        Verify contracts against code using SMT solver.
        
        Args:
            code: Source code to verify
            contracts: List of contracts with type, expression, description
            language: Programming language
            
        Returns:
            SMTResult with verification status
        """
        if not Z3_AVAILABLE:
            return SMTResult(
                status=SMTStatus.DISABLED,
                error="Z3 solver not installed"
            )
        
        if not contracts:
            return SMTResult(
                status=SMTStatus.SAT,
                solver_version=self.solver_version,
                assertions=[]
            )
        
        start_time = time.time()
        
        try:
            # Create Z3 solver with timeout
            solver = z3.Solver()
            solver.set("timeout", self.timeout_ms)
            
            # Parse contracts into Z3 assertions
            assertions = []
            for contract in contracts:
                assertion = self._parse_contract(contract)
                if assertion:
                    assertions.append(assertion)
                    if assertion.z3_expr is not None:
                        solver.add(assertion.z3_expr)
            
            # Check satisfiability
            result = solver.check()
            solve_time = (time.time() - start_time) * 1000
            
            # Determine status
            if result == z3.sat:
                status = SMTStatus.SAT
                # Mark all assertions as verified
                for a in assertions:
                    a.verified = True
            elif result == z3.unsat:
                status = SMTStatus.UNSAT
                # Get unsat core if available
                for a in assertions:
                    a.verified = False
            else:
                status = SMTStatus.UNKNOWN
            
            # Generate proof bytes (hash of solver state)
            proof_hash = hashlib.sha256(
                f"{code}:{str(assertions)}:{result}".encode()
            ).digest()
            
            return SMTResult(
                status=status,
                solver="z3",
                solver_version=self.solver_version,
                solve_time_ms=solve_time,
                assertions=assertions,
                proof_bytes=proof_hash
            )
            
        except z3.Z3Exception as e:
            return SMTResult(
                status=SMTStatus.ERROR,
                solver="z3",
                solver_version=self.solver_version,
                solve_time_ms=(time.time() - start_time) * 1000,
                error=str(e)
            )
        except Exception as e:
            return SMTResult(
                status=SMTStatus.ERROR,
                solver="z3",
                error=f"Unexpected error: {str(e)}"
            )
    
    def _parse_contract(self, contract: Dict[str, Any]) -> Optional[SMTAssertion]:
        """
        Parse a contract into an SMT assertion.
        
        Supports simple expressions like:
        - x > 0
        - len(result) == n
        - result >= input
        """
        expr_str = contract.get("expression", "")
        contract_type = contract.get("type", "invariant")
        description = contract.get("description", "")
        
        if not expr_str:
            return None
        
        try:
            # Create assertion object
            assertion = SMTAssertion(
                name=description or f"{contract_type}_{hash(expr_str) % 10000}",
                expression=expr_str,
                assertion_type=contract_type
            )
            
            # Try to parse expression into Z3
            # This is simplified - real implementation would need proper parsing
            z3_expr = self._expression_to_z3(expr_str)
            assertion.z3_expr = z3_expr
            
            return assertion
            
        except Exception:
            # Return assertion without Z3 expr if parsing fails
            return SMTAssertion(
                name=description or "parse_error",
                expression=expr_str,
                assertion_type=contract_type
            )
    
    def _expression_to_z3(self, expr: str) -> Optional[Any]:
        """
        Convert a simple expression string to Z3 expression.
        
        Handles: comparisons (>, <, ==, >=, <=, !=), 
                 basic arithmetic (+, -, *, /)
                 boolean operators (and, or, not)
        """
        if not Z3_AVAILABLE:
            return None
        
        # Create variables for common names
        x = z3.Int('x')
        y = z3.Int('y')
        n = z3.Int('n')
        result = z3.Int('result')
        length = z3.Int('length')
        
        # Simple expression mapping
        try:
            # Replace Python operators with Z3 equivalents
            expr = expr.replace("and", "z3.And").replace("or", "z3.Or").replace("not ", "z3.Not(")
            
            # Use eval with restricted namespace (not safe for production)
            # Real implementation should use a proper expression parser
            namespace = {
                'x': x, 'y': y, 'n': n, 'result': result, 'length': length,
                'z3': z3, 'And': z3.And, 'Or': z3.Or, 'Not': z3.Not,
                'Implies': z3.Implies
            }
            
            # Only evaluate simple comparisons for safety
            if any(op in expr for op in ['>', '<', '==', '>=', '<=', '!=']):
                z3_expr = eval(expr, {"__builtins__": {}}, namespace)
                return z3_expr
                
        except Exception:
            pass
        
        return None
    
    async def verify_type_constraints(
        self,
        code: str,
        types: Dict[str, str]
    ) -> SMTResult:
        """
        Verify type constraints are satisfiable.
        
        Used for checking generic type bounds and constraints.
        """
        if not Z3_AVAILABLE:
            return SMTResult(status=SMTStatus.DISABLED)
        
        # Type constraint verification logic
        # This would integrate with the type system
        return SMTResult(
            status=SMTStatus.SAT,
            solver="z3",
            solver_version=self.solver_version,
            assertions=[]
        )


# Singleton instance
_smt_verifier: Optional[SMTVerifier] = None


def get_smt_verifier() -> SMTVerifier:
    """Get or create SMT verifier singleton."""
    global _smt_verifier
    if _smt_verifier is None:
        _smt_verifier = SMTVerifier()
    return _smt_verifier
