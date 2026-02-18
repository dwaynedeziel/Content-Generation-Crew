"""Tool for writing topic map data to a CSV file."""

from __future__ import annotations

import csv
import os
from typing import Type

from crewai.tools import BaseTool
from pydantic import BaseModel, Field

from content_crew.constants import CSV_HEADERS


class CSVWriterInput(BaseModel):
    """Input schema for CSVWriterTool."""

    csv_content: str = Field(
        description=(
            "The full CSV content as a string. The first line MUST be the header row "
            "matching the topic map schema. Each subsequent line is a topic row. "
            "Fields are comma-separated. Use double quotes around fields that contain "
            "commas or pipe characters."
        )
    )
    output_path: str = Field(
        description="Absolute file path where the CSV should be saved, e.g. output/topic_maps/Topic Map - 2026-02-13.csv"
    )


class CSVWriterTool(BaseTool):
    """Writes structured topic map data to a CSV file."""

    name: str = "csv_writer"
    description: str = (
        "Writes topic map data to a CSV file. Pass the full CSV content as a string "
        "(header row + data rows) and the output file path. The tool will create "
        "any necessary directories and write the file."
    )
    args_schema: Type[BaseModel] = CSVWriterInput

    def _run(self, csv_content: str, output_path: str) -> str:
        """Write CSV content to the specified path."""
        try:
            # Ensure the output directory exists
            os.makedirs(os.path.dirname(output_path), exist_ok=True)

            # Write the CSV content directly
            with open(output_path, "w", newline="", encoding="utf-8") as f:
                f.write(csv_content)

            # Validate header row
            with open(output_path, "r", encoding="utf-8") as f:
                reader = csv.reader(f)
                header = next(reader)
                header_clean = [h.strip() for h in header]

                # Check if headers match expected schema
                missing = [h for h in CSV_HEADERS if h not in header_clean]
                if missing:
                    return (
                        f"WARNING: CSV written to {output_path} but missing expected columns: "
                        f"{', '.join(missing)}. Expected columns: {', '.join(CSV_HEADERS)}"
                    )

                # Count data rows
                row_count = sum(1 for _ in reader)

            return f"SUCCESS: CSV written to {output_path} with {row_count} topic rows."

        except Exception as e:
            return f"ERROR writing CSV: {str(e)}"
