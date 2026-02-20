"""Tool for writing markdown content to files."""

from __future__ import annotations

import os


def file_writer(content: str, output_path: str) -> str:
    """Write content to the specified path.

    Args:
        content: The full markdown content to write.
        output_path: Absolute file path where the file should be saved.

    Returns:
        Success or error message.
    """
    try:
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        with open(output_path, "w", encoding="utf-8") as f:
            f.write(content)

        word_count = len(content.split())
        return f"SUCCESS: File written to {output_path} ({word_count} words)."

    except Exception as e:
        return f"ERROR writing file: {str(e)}"
