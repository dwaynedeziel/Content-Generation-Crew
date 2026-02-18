"""Tool for checking content against banned AI cliché phrases."""

from __future__ import annotations

from typing import Type

from crewai.tools import BaseTool
from pydantic import BaseModel, Field

from content_crew.constants import BANNED_PHRASES


class BannedPhraseCheckerInput(BaseModel):
    """Input schema for BannedPhraseCheckerTool."""

    content: str = Field(description="The article content to check for banned phrases.")


class BannedPhraseCheckerTool(BaseTool):
    """Checks content for banned AI cliché phrases and returns any violations."""

    name: str = "banned_phrase_checker"
    description: str = (
        "Scans article content for banned AI cliché phrases. Returns a list of any "
        "violations found with their locations. Use this during QA to ensure content "
        "does not contain any of the banned phrases."
    )
    args_schema: Type[BaseModel] = BannedPhraseCheckerInput

    def _run(self, content: str) -> str:
        """Check content for banned phrases."""
        content_lower = content.lower()
        violations = []

        for phrase in BANNED_PHRASES:
            phrase_lower = phrase.lower()
            if phrase_lower in content_lower:
                # Find all occurrences
                start = 0
                while True:
                    idx = content_lower.find(phrase_lower, start)
                    if idx == -1:
                        break
                    # Get surrounding context (30 chars before and after)
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
