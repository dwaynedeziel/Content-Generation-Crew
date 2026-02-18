"""Tool for writing markdown content to files."""

from __future__ import annotations

import os
from typing import Type

from crewai.tools import BaseTool
from pydantic import BaseModel, Field


class FileWriterInput(BaseModel):
    """Input schema for FileWriterTool."""

    content: str = Field(description="The full markdown content to write to the file.")
    output_path: str = Field(
        description="Absolute file path where the file should be saved, e.g. output/briefs/Topic Name - 2026-02-13.md"
    )


class FileWriterTool(BaseTool):
    """Writes markdown content to a file."""

    name: str = "file_writer"
    description: str = (
        "Writes markdown or text content to a file. Pass the content and the output "
        "file path. The tool will create any necessary directories and write the file."
    )
    args_schema: Type[BaseModel] = FileWriterInput

    def _run(self, content: str, output_path: str) -> str:
        """Write content to the specified path."""
        try:
            os.makedirs(os.path.dirname(output_path), exist_ok=True)

            with open(output_path, "w", encoding="utf-8") as f:
                f.write(content)

            word_count = len(content.split())
            return f"SUCCESS: File written to {output_path} ({word_count} words)."

        except Exception as e:
            return f"ERROR writing file: {str(e)}"
