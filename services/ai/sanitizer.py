"""
Intent Sanitizer

Provides input sanitization for raw user intents to prevent prompt injection,
adversarial inputs, and ensure safe processing through the AI pipeline.
"""
import re
from typing import Tuple


# Maximum allowed intent length (characters)
MAX_INTENT_LENGTH = 5000

# Patterns that indicate potential prompt injection attempts
INJECTION_PATTERNS = [
    r"ignore\s+(all\s+)?previous\s+instructions",
    r"ignore\s+(all\s+)?constraints",
    r"forget\s+(all\s+)?instructions",
    r"disregard\s+(all\s+)?(previous\s+)?instructions",
    r"override\s+system\s+prompt",
    r"output\s+(your\s+)?(system\s+)?prompt",
    r"reveal\s+(your\s+)?(api|secret)\s+key",
    r"print\s+(your\s+)?environment\s+variables",
    r"execute\s+(shell|bash|cmd)\s+command",
    r"os\.system\s*\(",
    r"subprocess\.\w+\s*\(",
    r"__import__\s*\(",
    r"eval\s*\(",
    r"exec\s*\(",
]

# Compiled regex patterns for efficiency
_compiled_patterns = [
    re.compile(pattern, re.IGNORECASE) for pattern in INJECTION_PATTERNS
]


def sanitize_intent(raw_intent: str) -> Tuple[str, bool, str]:
    """
    Sanitize a raw user intent string.

    Returns:
        Tuple of (sanitized_intent, is_safe, warning_message)
    """
    if not raw_intent or not raw_intent.strip():
        return "", False, "Intent cannot be empty"

    # 1. Length check
    if len(raw_intent) > MAX_INTENT_LENGTH:
        return "", False, f"Intent exceeds maximum length of {MAX_INTENT_LENGTH} characters"

    # 2. Strip control characters (keep newlines and tabs)
    sanitized = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', raw_intent)

    # 3. Check for injection patterns
    for pattern in _compiled_patterns:
        if pattern.search(sanitized):
            return "", False, "Intent contains potentially unsafe instructions"

    # 4. Strip excessive whitespace
    sanitized = re.sub(r'\n{3,}', '\n\n', sanitized)
    sanitized = sanitized.strip()

    return sanitized, True, ""
