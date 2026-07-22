"""
Security Agent
--------------
A lightweight guard that runs before the Research Agent. It screens the
user-supplied topic for common prompt-injection / jailbreak patterns and
blocks the pipeline before any LLM call is made if something suspicious
is detected.

NOTE ON LIMITATIONS: this is pattern/regex matching, which is a reasonable
first line of defense for a lab project, but it is not a complete security
solution -- it can be bypassed by typos, translation, encoding tricks, or
novel phrasings. A production system should pair this with a hardened
system prompt and checks on the *output* side too, not just the input.
"""

import re
from typing import Tuple


# ---------------------------------------------------------------------------
# Known prompt-injection / jailbreak patterns.
# Written as regexes (not plain substrings) so small variations in wording
# ("ignore all previous instructions" vs "ignore previous instructions")
# are still caught, while staying case-insensitive.
# ---------------------------------------------------------------------------
SUSPICIOUS_PATTERNS = [
    r"ignore\s+(all\s+)?previous\s+instructions",
    r"forget\s+(all\s+)?previous\s+instructions",
    r"disregard\s+(all\s+)?previous\s+instructions",
    r"override\s+(the\s+)?instructions",
    r"system\s+prompt",
    r"reveal\s+(the\s+)?system\s+prompt",
    r"developer\s+message",
    r"jailbreak",
    r"bypass\s+security",
    r"act\s+as\s+(a|an)?\s*\w+",
    r"pretend\s+to\s+be",
]

_COMPILED_PATTERNS = [re.compile(p, re.IGNORECASE) for p in SUSPICIOUS_PATTERNS]


def check_input_safety(text: str) -> Tuple[bool, str]:
    """
    Screen a piece of text for prompt-injection / jailbreak patterns.

    Returns:
        (is_safe, reason)
        is_safe -- True if no suspicious pattern was found.
        reason  -- human-readable explanation. Empty string if safe.
    """
    for pattern in _COMPILED_PATTERNS:
        match = pattern.search(text)
        if match:
            return False, f"Matched suspicious pattern: {match.group(0)!r}"
    return True, ""
