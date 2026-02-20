"""Tool for checking content against banned AI cliché phrases."""

from __future__ import annotations

from content_crew.constants import BANNED_PHRASES


def banned_phrase_checker(content: str) -> str:
    """Check content for banned AI cliché phrases.

    Args:
        content: The article content to check.

    Returns:
        PASSED or FAILED with violation details.
    """
    content_lower = content.lower()
    violations = []

    for phrase in BANNED_PHRASES:
        phrase_lower = phrase.lower()
        if phrase_lower in content_lower:
            start = 0
            while True:
                idx = content_lower.find(phrase_lower, start)
                if idx == -1:
                    break
                context_start = max(0, idx - 30)
                context_end = min(len(content), idx + len(phrase) + 30)
                context = content[context_start:context_end].replace("\n", " ")
                violations.append(f'  - "{phrase}" found: "...{context}..."')
                start = idx + 1

    if not violations:
        return "PASSED: No banned phrases found in the content."

    return (
        f"FAILED: Found {len(violations)} banned phrase violation(s):\n"
        + "\n".join(violations)
    )
