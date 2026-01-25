"""
Policy Engine

Pre/post generation code governance and security policies.
Inspired by UACP's gateway/internal/policy/

Enforces rules on intents and generated code to prevent dangerous patterns.
"""
import re
from typing import List, Dict, Any, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum
from abc import ABC, abstractmethod


class PolicySeverity(Enum):
    """Severity level for policy violations."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class PolicyPhase(Enum):
    """When the policy is evaluated."""
    PRE_GENERATION = "pre_generation"
    POST_GENERATION = "post_generation"


@dataclass
class PolicyViolation:
    """A policy violation found during evaluation."""
    rule_id: str
    rule_name: str
    severity: PolicySeverity
    message: str
    location: Optional[str] = None  # Line number or context
    suggestion: Optional[str] = None
    
    def to_dict(self) -> dict:
        return {
            "rule_id": self.rule_id,
            "rule_name": self.rule_name,
            "severity": self.severity.value,
            "message": self.message,
            "location": self.location,
            "suggestion": self.suggestion
        }


@dataclass
class PolicyResult:
    """Result of policy evaluation."""
    passed: bool
    violations: List[PolicyViolation] = field(default_factory=list)
    phase: PolicyPhase = PolicyPhase.POST_GENERATION
    
    @property
    def has_critical(self) -> bool:
        return any(v.severity == PolicySeverity.CRITICAL for v in self.violations)
    
    @property
    def has_errors(self) -> bool:
        return any(v.severity == PolicySeverity.ERROR for v in self.violations)
    
    @property
    def error_count(self) -> int:
        return sum(1 for v in self.violations 
                   if v.severity in (PolicySeverity.ERROR, PolicySeverity.CRITICAL))
    
    @property
    def warning_count(self) -> int:
        return sum(1 for v in self.violations if v.severity == PolicySeverity.WARNING)
    
    def to_dict(self) -> dict:
        return {
            "passed": self.passed,
            "phase": self.phase.value,
            "violations": [v.to_dict() for v in self.violations],
            "error_count": self.error_count,
            "warning_count": self.warning_count
        }


class PolicyRule(ABC):
    """Abstract base class for policy rules."""
    
    @property
    @abstractmethod
    def id(self) -> str:
        pass
    
    @property
    @abstractmethod
    def name(self) -> str:
        pass
    
    @property
    @abstractmethod
    def phase(self) -> PolicyPhase:
        pass
    
    @property
    def severity(self) -> PolicySeverity:
        return PolicySeverity.ERROR
    
    @property
    def enabled(self) -> bool:
        return True
    
    @abstractmethod
    def check(self, content: str, context: Dict[str, Any]) -> List[PolicyViolation]:
        """Check content against this rule."""
        pass


# ============================================================================
# Built-in Pre-Generation Rules (Intent Filtering)
# ============================================================================

class BlockDangerousIntentsRule(PolicyRule):
    """Block intents that request dangerous operations."""
    
    DANGEROUS_PATTERNS = [
        r"\b(delete|remove|drop)\s+(all|every|database|table|file)",
        r"\b(rm\s+-rf|format\s+\w:)",
        r"\b(hack|exploit|bypass|crack)\b",
        r"\bcrypto\s*(mine|mining)\b",
    ]
    
    @property
    def id(self) -> str:
        return "pre-001"
    
    @property
    def name(self) -> str:
        return "Block Dangerous Intents"
    
    @property
    def phase(self) -> PolicyPhase:
        return PolicyPhase.PRE_GENERATION
    
    @property
    def severity(self) -> PolicySeverity:
        return PolicySeverity.CRITICAL
    
    def check(self, content: str, context: Dict[str, Any]) -> List[PolicyViolation]:
        violations = []
        content_lower = content.lower()
        
        for pattern in self.DANGEROUS_PATTERNS:
            if re.search(pattern, content_lower):
                violations.append(PolicyViolation(
                    rule_id=self.id,
                    rule_name=self.name,
                    severity=self.severity,
                    message=f"Intent contains potentially dangerous pattern: {pattern}",
                    suggestion="Rephrase your intent to be more specific and safe"
                ))
                break  # One violation is enough
        
        return violations


# ============================================================================
# Built-in Post-Generation Rules (Code Safety)
# ============================================================================

class NoEvalExecRule(PolicyRule):
    """Block eval() and exec() usage."""
    
    @property
    def id(self) -> str:
        return "post-001"
    
    @property
    def name(self) -> str:
        return "No eval/exec"
    
    @property
    def phase(self) -> PolicyPhase:
        return PolicyPhase.POST_GENERATION
    
    @property
    def severity(self) -> PolicySeverity:
        return PolicySeverity.CRITICAL
    
    def check(self, content: str, context: Dict[str, Any]) -> List[PolicyViolation]:
        violations = []
        
        # Match eval/exec not in strings or comments
        for i, line in enumerate(content.split('\n'), 1):
            line_stripped = line.strip()
            if line_stripped.startswith('#'):
                continue
            
            if re.search(r'\beval\s*\(', line):
                violations.append(PolicyViolation(
                    rule_id=self.id,
                    rule_name=self.name,
                    severity=self.severity,
                    message="Use of eval() is not allowed",
                    location=f"line {i}",
                    suggestion="Use ast.literal_eval() for safe literal parsing"
                ))
            
            if re.search(r'\bexec\s*\(', line):
                violations.append(PolicyViolation(
                    rule_id=self.id,
                    rule_name=self.name,
                    severity=self.severity,
                    message="Use of exec() is not allowed",
                    location=f"line {i}",
                    suggestion="Refactor to avoid dynamic code execution"
                ))
        
        return violations


class NoOsSystemRule(PolicyRule):
    """Block os.system() and subprocess.call() with shell=True."""
    
    @property
    def id(self) -> str:
        return "post-002"
    
    @property
    def name(self) -> str:
        return "No shell execution"
    
    @property
    def phase(self) -> PolicyPhase:
        return PolicyPhase.POST_GENERATION
    
    @property
    def severity(self) -> PolicySeverity:
        return PolicySeverity.ERROR
    
    def check(self, content: str, context: Dict[str, Any]) -> List[PolicyViolation]:
        violations = []
        
        for i, line in enumerate(content.split('\n'), 1):
            if 'os.system(' in line:
                violations.append(PolicyViolation(
                    rule_id=self.id,
                    rule_name=self.name,
                    severity=self.severity,
                    message="os.system() is not allowed",
                    location=f"line {i}",
                    suggestion="Use subprocess.run() with shell=False"
                ))
            
            if 'shell=True' in line and ('subprocess' in content):
                violations.append(PolicyViolation(
                    rule_id=self.id,
                    rule_name=self.name,
                    severity=self.severity,
                    message="subprocess with shell=True is not allowed",
                    location=f"line {i}",
                    suggestion="Use shell=False and pass args as list"
                ))
        
        return violations


class RequireTypeHintsRule(PolicyRule):
    """Require type hints on function definitions."""
    
    @property
    def id(self) -> str:
        return "post-003"
    
    @property
    def name(self) -> str:
        return "Require type hints"
    
    @property
    def phase(self) -> PolicyPhase:
        return PolicyPhase.POST_GENERATION
    
    @property
    def severity(self) -> PolicySeverity:
        return PolicySeverity.WARNING
    
    def check(self, content: str, context: Dict[str, Any]) -> List[PolicyViolation]:
        violations = []
        
        # Simple heuristic: functions without -> return type
        for i, line in enumerate(content.split('\n'), 1):
            if re.match(r'\s*def\s+\w+\s*\([^)]*\)\s*:', line):
                if '->' not in line:
                    func_match = re.search(r'def\s+(\w+)', line)
                    func_name = func_match.group(1) if func_match else "function"
                    violations.append(PolicyViolation(
                        rule_id=self.id,
                        rule_name=self.name,
                        severity=self.severity,
                        message=f"Function '{func_name}' is missing return type hint",
                        location=f"line {i}",
                        suggestion="Add return type, e.g., '-> str:' or '-> None:'"
                    ))
        
        return violations


class MaxFunctionLengthRule(PolicyRule):
    """Limit function length for maintainability."""
    
    MAX_LINES = 50
    
    @property
    def id(self) -> str:
        return "post-004"
    
    @property
    def name(self) -> str:
        return "Max function length"
    
    @property
    def phase(self) -> PolicyPhase:
        return PolicyPhase.POST_GENERATION
    
    @property
    def severity(self) -> PolicySeverity:
        return PolicySeverity.WARNING
    
    def check(self, content: str, context: Dict[str, Any]) -> List[PolicyViolation]:
        violations = []
        lines = content.split('\n')
        
        in_function = False
        func_start = 0
        func_name = ""
        indent_level = 0
        
        for i, line in enumerate(lines):
            # Detect function start
            func_match = re.match(r'^(\s*)def\s+(\w+)', line)
            if func_match:
                if in_function:
                    # Check previous function
                    length = i - func_start
                    if length > self.MAX_LINES:
                        violations.append(PolicyViolation(
                            rule_id=self.id,
                            rule_name=self.name,
                            severity=self.severity,
                            message=f"Function '{func_name}' is {length} lines (max: {self.MAX_LINES})",
                            location=f"line {func_start + 1}",
                            suggestion="Consider breaking into smaller functions"
                        ))
                
                in_function = True
                func_start = i
                func_name = func_match.group(2)
                indent_level = len(func_match.group(1))
        
        # Check last function
        if in_function:
            length = len(lines) - func_start
            if length > self.MAX_LINES:
                violations.append(PolicyViolation(
                    rule_id=self.id,
                    rule_name=self.name,
                    severity=self.severity,
                    message=f"Function '{func_name}' is {length} lines (max: {self.MAX_LINES})",
                    location=f"line {func_start + 1}",
                    suggestion="Consider breaking into smaller functions"
                ))
        
        return violations


# ============================================================================
# Policy Engine
# ============================================================================

class PolicyEngine:
    """
    Enforces code governance policies.
    
    Usage:
        engine = PolicyEngine()
        
        # Pre-generation check
        result = engine.check_pre_generation("Create a function to delete all files")
        if not result.passed:
            raise PolicyError(result.violations)
        
        # Post-generation check
        result = engine.check_post_generation(generated_code)
        if result.has_critical:
            raise PolicyError(result.violations)
    """
    
    def __init__(self, strict_mode: bool = False):
        self.rules: List[PolicyRule] = []
        self.strict_mode = strict_mode  # Treat warnings as errors
        
        # Register default rules
        self._register_defaults()
    
    def _register_defaults(self):
        """Register built-in rules."""
        # Pre-generation
        self.add_rule(BlockDangerousIntentsRule())
        
        # Post-generation
        self.add_rule(NoEvalExecRule())
        self.add_rule(NoOsSystemRule())
        self.add_rule(RequireTypeHintsRule())
        self.add_rule(MaxFunctionLengthRule())
    
    def add_rule(self, rule: PolicyRule):
        """Add a policy rule."""
        self.rules.append(rule)
    
    def remove_rule(self, rule_id: str):
        """Remove a rule by ID."""
        self.rules = [r for r in self.rules if r.id != rule_id]
    
    def check_pre_generation(
        self, 
        intent: str, 
        context: Optional[Dict[str, Any]] = None
    ) -> PolicyResult:
        """Check intent before generation."""
        return self._evaluate(
            content=intent,
            phase=PolicyPhase.PRE_GENERATION,
            context=context or {}
        )
    
    def check_post_generation(
        self, 
        code: str, 
        context: Optional[Dict[str, Any]] = None
    ) -> PolicyResult:
        """Check generated code."""
        return self._evaluate(
            content=code,
            phase=PolicyPhase.POST_GENERATION,
            context=context or {}
        )
    
    def _evaluate(
        self, 
        content: str, 
        phase: PolicyPhase, 
        context: Dict[str, Any]
    ) -> PolicyResult:
        """Run all applicable rules."""
        violations = []
        
        for rule in self.rules:
            if not rule.enabled:
                continue
            if rule.phase != phase:
                continue
            
            try:
                rule_violations = rule.check(content, context)
                violations.extend(rule_violations)
            except Exception as e:
                # Don't let a broken rule crash the engine
                violations.append(PolicyViolation(
                    rule_id=rule.id,
                    rule_name=rule.name,
                    severity=PolicySeverity.WARNING,
                    message=f"Rule evaluation error: {str(e)}"
                ))
        
        # Determine if passed
        if self.strict_mode:
            passed = len(violations) == 0
        else:
            passed = not any(
                v.severity in (PolicySeverity.ERROR, PolicySeverity.CRITICAL)
                for v in violations
            )
        
        return PolicyResult(
            passed=passed,
            violations=violations,
            phase=phase
        )
    
    def list_rules(self) -> List[dict]:
        """List all registered rules."""
        return [
            {
                "id": r.id,
                "name": r.name,
                "phase": r.phase.value,
                "severity": r.severity.value,
                "enabled": r.enabled
            }
            for r in self.rules
        ]


# Global instance
_global_engine: Optional[PolicyEngine] = None


def get_policy_engine() -> PolicyEngine:
    """Get the global policy engine."""
    global _global_engine
    if _global_engine is None:
        _global_engine = PolicyEngine()
    return _global_engine


def check_code(code: str) -> PolicyResult:
    """Convenience function to check code."""
    return get_policy_engine().check_post_generation(code)


def check_intent(intent: str) -> PolicyResult:
    """Convenience function to check intent."""
    return get_policy_engine().check_pre_generation(intent)
