"""Merge point progression CSVs under a directory into combined.csv."""

import argparse
import csv
import sys
from pathlib import Path


def main() -> None:
    """Merge point progression CSVs, adding a team name column."""
    parser = argparse.ArgumentParser(
        description="Merge point progression CSVs into combined.csv",
    )
    parser.add_argument("dir", help="Directory to search for CSV files")
    parser.add_argument(
        "--output",
        "-o",
        default="combined.csv",
        help="Output CSV filename (default: combined.csv)",
    )
    args = parser.parse_args()

    root = Path(args.dir)
    if not root.exists() or not root.is_dir():
        raise ValueError(f"Invalid input directory: {root}\n")

    out_path = Path(args.output)

    csv_files = [p for p in root.rglob("*.csv") if p.name.lower() != "combined.csv"]
    if not csv_files:
        raise ValueError(f"No CSV files found under {root}\n")

    input_fields = ["Gameweek", "Points", "Total"]
    rows = []

    # arrange by team name alphabetical
    for f in sorted(csv_files):
        with f.open(newline="", encoding="utf-8") as fh:
            reader = csv.DictReader(fh)
            if reader.fieldnames != input_fields:
                sys.stderr.write(f"Warning: header mismatch in {f}; continuing.\n")
                continue
            for r in reader:
                r["Team"] = f.stem.replace("_", " ")
                rows.append(r)

    # Ensure Team is added as the first column
    out_fields = ["Team", *input_fields]

    with out_path.open("w", newline="", encoding="utf-8") as outfh:
        writer = csv.DictWriter(outfh, fieldnames=out_fields)
        writer.writeheader()
        for r in rows:
            writer.writerow(r)


if __name__ == "__main__":
    main()
