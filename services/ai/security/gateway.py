"""
AI Security Gateway for AXIOM

Input/output filtering to ensure secure AI operations:
- PII detection and masking
- Secret/credential detection
- Injection prevention
- License compliance checking
- Rate limiting
"""
import re
import time
from typing import Optional, List, Dict, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict


class ThreatLevel(str, Enum):
    """Threat severity levels."""
    NONE = "none"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class FilterType(str, Enum):
    """Types of security filters."""
    PII = "pii"
    SECRETS = "secrets"
    INJECTION = "injection"
    LICENSE = "license"
    RATE_LIMIT = "rate_limit"


@dataclass
class SecurityFinding:
    """A security finding from filtering."""
    filter_type: FilterType
    threat_level: ThreatLevel
    description: str
    location: Optional[str] = None
    suggestion: Optional[str] = None
    masked_content: Optional[str] = None


@dataclass
class SecurityResult:
    """Result from security gateway check."""
    allowed: bool
    findings: List[SecurityFinding] = field(default_factory=list)
    sanitized_content: Optional[str] = None
    processing_time_ms: float = 0.0
    
    @property
    def highest_threat(self) -> ThreatLevel:
        if not self.findings:
            return ThreatLevel.NONE
        levels = [ThreatLevel.NONE, ThreatLevel.LOW, ThreatLevel.MEDIUM, ThreatLevel.HIGH, ThreatLevel.CRITICAL]
        max_level = ThreatLevel.NONE
        for f in self.findings:
            if levels.index(f.threat_level) > levels.index(max_level):
                max_level = f.threat_level
        return max_level
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "allowed": self.allowed,
            "highest_threat": self.highest_threat.value,
            "findings": [
                {
                    "type": f.filter_type.value,
                    "threat": f.threat_level.value,
                    "description": f.description,
                    "location": f.location,
                    "suggestion": f.suggestion
                }
                for f in self.findings
            ],
            "processing_time_ms": self.processing_time_ms
        }


class SecurityGateway:
    """
    AI Security Gateway.
    
    Provides layered security for AI inputs and outputs:
    1. PII Detection - emails, phones, SSNs, etc.
    2. Secret Detection - API keys, passwords, tokens
    3. Injection Prevention - prompt injection patterns
    4. License Compliance - check for license violations
    5. Rate Limiting - per-user/org quotas
    """
    
    # PII Patterns
    PII_PATTERNS = {
        "email": r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
        "phone_us": r'\b(\+?1[-.\s]?)?(\(?\d{3}\)?[-.\s]?)?\d{3}[-.\s]?\d{4}\b',
        "ssn": r'\b\d{3}[-\s]?\d{2}[-\s]?\d{4}\b',
        "credit_card": r'\b(?:\d{4}[-\s]?){3}\d{4}\b',
        "ip_address": r'\b(?:\d{1,3}\.){3}\d{1,3}\b',
    }
    
    # Secret Patterns
    SECRET_PATTERNS = {
        "aws_key": r'AKIA[0-9A-Z]{16}',
        "aws_secret": r'(?i)aws(.{0,20})?[\'"][0-9a-zA-Z/+]{40}[\'"]',
        "github_token": r'gh[pousr]_[A-Za-z0-9_]{36}',
        "google_api": r'AIza[0-9A-Za-z\-_]{35}',
        "jwt": r'eyJ[A-Za-z0-9-_=]+\.eyJ[A-Za-z0-9-_=]+\.?[A-Za-z0-9-_.+/=]*',
        "private_key": r'-----BEGIN (?:RSA |EC |DSA )?PRIVATE KEY-----',
        "slack_token": r'xox[baprs]-[0-9]{10,12}-[0-9A-Za-z]{24,36}',
        "generic_api_key": r'(?i)(api[_-]?key|apikey|secret[_-]?key)[\'"]?\s*[:=]\s*[\'"][a-zA-Z0-9]{16,}[\'"]',
        "password_assignment": r'(?i)(password|passwd|pwd)\s*[:=]\s*[\'"][^\'"]+[\'"]',
    }
    
    # Prompt Injection Patterns
    INJECTION_PATTERNS = [
        r'(?i)ignore\s+(previous|all|above)\s+instructions?',
        r'(?i)disregard\s+(previous|all|above)',
        r'(?i)forget\s+(everything|previous|what)',
        r'(?i)new\s+instructions?:\s+',
        r'(?i)system\s*:\s*you\s+are',
        r'(?i)\]\]\s*\[\[',  # Delimiter escape
        r'(?i)```\s*system',  # Code block injection
    ]
    
    # License Keywords (simplified)
    LICENSE_PATTERNS = {
        "gpl": r'(?i)\bGPL(?:v[23])?\b',
        "agpl": r'(?i)\bAGPL\b',
        "copyleft": r'(?i)\bcopyleft\b',
    }
    
    def __init__(
        self,
        block_pii: bool = True,
        block_secrets: bool = True,
        block_injection: bool = True,
        check_license: bool = False,
        enable_rate_limit: bool = True
    ):
        self.block_pii = block_pii
        self.block_secrets = block_secrets
        self.block_injection = block_injection
        self.check_license = check_license
        self.enable_rate_limit = enable_rate_limit
        
        # Rate limiting state
        self._rate_limits: Dict[str, List[float]] = defaultdict(list)
        self._rate_limit_window = 60  # seconds
        self._rate_limit_max = {
            "free": 10,
            "pro": 100,
            "enterprise": 1000
        }
    
    def check_input(
        self,
        content: str,
        user_id: Optional[str] = None,
        org_id: Optional[str] = None,
        plan: str = "free"
    ) -> SecurityResult:
        """
        Check input content before sending to AI.
        
        Args:
            content: The input content to check
            user_id: User ID for rate limiting
            org_id: Organization ID for quotas
            plan: User's plan tier
            
        Returns:
            SecurityResult with findings and sanitized content
        """
        start_time = time.time()
        findings = []
        sanitized = content
        
        # 1. Rate limiting
        if self.enable_rate_limit and user_id:
            rate_result = self._check_rate_limit(user_id, plan)
            if rate_result:
                findings.append(rate_result)
        
        # 2. Prompt injection detection
        if self.block_injection:
            injection_findings = self._detect_injection(content)
            findings.extend(injection_findings)
        
        # 3. PII detection (warn, don't block inputs)
        pii_findings = self._detect_pii(content)
        for f in pii_findings:
            f.threat_level = ThreatLevel.LOW  # Downgrade for inputs
        findings.extend(pii_findings)
        
        # Determine if allowed
        critical_findings = [f for f in findings if f.threat_level in [ThreatLevel.HIGH, ThreatLevel.CRITICAL]]
        allowed = len(critical_findings) == 0
        
        return SecurityResult(
            allowed=allowed,
            findings=findings,
            sanitized_content=sanitized,
            processing_time_ms=(time.time() - start_time) * 1000
        )
    
    def check_output(
        self,
        content: str,
        mask_pii: bool = True,
        mask_secrets: bool = True
    ) -> SecurityResult:
        """
        Check and sanitize output content from AI.
        
        Args:
            content: The output content to check
            mask_pii: Whether to mask PII
            mask_secrets: Whether to mask secrets
            
        Returns:
            SecurityResult with findings and sanitized content
        """
        start_time = time.time()
        findings = []
        sanitized = content
        
        # 1. Secret detection (critical)
        if self.block_secrets:
            secret_findings, sanitized = self._detect_and_mask_secrets(sanitized, mask_secrets)
            findings.extend(secret_findings)
        
        # 2. PII detection
        if self.block_pii:
            pii_findings, sanitized = self._detect_and_mask_pii(sanitized, mask_pii)
            findings.extend(pii_findings)
        
        # 3. License compliance
        if self.check_license:
            license_findings = self._check_license_compliance(content)
            findings.extend(license_findings)
        
        # Always allow outputs but include warnings
        return SecurityResult(
            allowed=True,
            findings=findings,
            sanitized_content=sanitized,
            processing_time_ms=(time.time() - start_time) * 1000
        )
    
    def _detect_injection(self, content: str) -> List[SecurityFinding]:
        """Detect prompt injection patterns."""
        findings = []
        for pattern in self.INJECTION_PATTERNS:
            matches = re.finditer(pattern, content)
            for match in matches:
                findings.append(SecurityFinding(
                    filter_type=FilterType.INJECTION,
                    threat_level=ThreatLevel.HIGH,
                    description=f"Potential prompt injection detected",
                    location=f"Position {match.start()}-{match.end()}",
                    suggestion="Remove or rephrase the instruction-like content"
                ))
        return findings
    
    def _detect_pii(self, content: str) -> List[SecurityFinding]:
        """Detect PII patterns."""
        findings = []
        for pii_type, pattern in self.PII_PATTERNS.items():
            matches = re.finditer(pattern, content)
            for match in matches:
                findings.append(SecurityFinding(
                    filter_type=FilterType.PII,
                    threat_level=ThreatLevel.MEDIUM,
                    description=f"Potential {pii_type.replace('_', ' ')} detected",
                    location=f"Position {match.start()}-{match.end()}",
                    suggestion=f"Consider removing or masking {pii_type}"
                ))
        return findings
    
    def _detect_and_mask_pii(self, content: str, mask: bool) -> Tuple[List[SecurityFinding], str]:
        """Detect and optionally mask PII."""
        findings = []
        sanitized = content
        
        for pii_type, pattern in self.PII_PATTERNS.items():
            matches = list(re.finditer(pattern, content))
            for match in matches:
                findings.append(SecurityFinding(
                    filter_type=FilterType.PII,
                    threat_level=ThreatLevel.MEDIUM,
                    description=f"Found {pii_type.replace('_', ' ')}",
                    location=f"Position {match.start()}-{match.end()}",
                    masked_content=f"[{pii_type.upper()}_MASKED]"
                ))
                if mask:
                    sanitized = sanitized.replace(match.group(), f"[{pii_type.upper()}_MASKED]")
        
        return findings, sanitized
    
    def _detect_and_mask_secrets(self, content: str, mask: bool) -> Tuple[List[SecurityFinding], str]:
        """Detect and optionally mask secrets."""
        findings = []
        sanitized = content
        
        for secret_type, pattern in self.SECRET_PATTERNS.items():
            matches = list(re.finditer(pattern, content))
            for match in matches:
                findings.append(SecurityFinding(
                    filter_type=FilterType.SECRETS,
                    threat_level=ThreatLevel.CRITICAL,
                    description=f"Potential {secret_type.replace('_', ' ')} detected",
                    location=f"Position {match.start()}-{match.end()}",
                    suggestion="This secret should be removed from the output",
                    masked_content="[SECRET_REDACTED]"
                ))
                if mask:
                    sanitized = sanitized.replace(match.group(), "[SECRET_REDACTED]")
        
        return findings, sanitized
    
    def _check_license_compliance(self, content: str) -> List[SecurityFinding]:
        """Check for potential license compliance issues."""
        findings = []
        for license_type, pattern in self.LICENSE_PATTERNS.items():
            if re.search(pattern, content):
                findings.append(SecurityFinding(
                    filter_type=FilterType.LICENSE,
                    threat_level=ThreatLevel.LOW,
                    description=f"Code may contain {license_type.upper()} licensed content",
                    suggestion="Review license compatibility with your project"
                ))
        return findings
    
    def _check_rate_limit(self, user_id: str, plan: str) -> Optional[SecurityFinding]:
        """Check rate limits for a user."""
        now = time.time()
        window_start = now - self._rate_limit_window
        
        # Clean old entries
        self._rate_limits[user_id] = [
            t for t in self._rate_limits[user_id]
            if t > window_start
        ]
        
        # Check limit
        limit = self._rate_limit_max.get(plan, 10)
        if len(self._rate_limits[user_id]) >= limit:
            return SecurityFinding(
                filter_type=FilterType.RATE_LIMIT,
                threat_level=ThreatLevel.HIGH,
                description=f"Rate limit exceeded ({limit}/minute)",
                suggestion=f"Wait or upgrade to a higher plan"
            )
        
        # Record request
        self._rate_limits[user_id].append(now)
        return None


# Singleton instance
_security_gateway: Optional[SecurityGateway] = None


def get_security_gateway() -> SecurityGateway:
    """Get or create security gateway singleton."""
    global _security_gateway
    if _security_gateway is None:
        _security_gateway = SecurityGateway()
    return _security_gateway
