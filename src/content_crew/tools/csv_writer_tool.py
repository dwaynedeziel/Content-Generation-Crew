"""Tool for writing topic map data to a CSV file."""

from __future__ import annotations

import csv
import os

from content_crew.constants import CSV_HEADERS


def csv_writer(csv_content: str, output_path: str) -> str:
    """Write CSV content to the specified path.

    Args:
        csv_content: The full CSV content as a string. First line is the header row.
        output_path: Absolute file path where the CSV should be saved.

    Returns:
        Success or error message.
    """
    try:
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        with open(output_path, "w", newline="", encoding="utf-8") as f:
            f.write(csv_content)

        # Validate header row
        with open(output_path, "r", encoding="utf-8") as f:
            reader = csv.reader(f)
            header = next(reader)
            header_clean = [h.strip() for h in header]

            missing = [h for h in CSV_HEADERS if h not in header_clean]
            if missing:
                return (
                    f"WARNING: CSV written to {output_path} but missing expected columns: "
                    f"{', '.join(missing)}. Expected columns: {', '.join(CSV_HEADERS)}"
                )

            row_count = sum(1 for _ in reader)

        return f"SUCCESS: CSV written to {output_path} with {row_count} topic rows."

    except Exception as e:
        return f"ERROR writing CSV: {str(e)}"
