"""Convert the free agents HTML table into CSV."""

import argparse
from pathlib import Path

import pandas as pd


def main() -> None:
    """Convert the free agents HTML table at the input path into CSV."""
    parser = argparse.ArgumentParser(
        description="Convert the free agents HTML table into CSV",
    )
    parser.add_argument(
        "input",
        help="Path to the input HTML file",
    )
    parser.add_argument(
        "--output",
        "-o",
        default="free_agents.csv",
        help="Path to the output CSV file",
    )
    args = parser.parse_args()

    input_path = Path(args.input)
    if not input_path.exists() or not input_path.is_file():
        raise ValueError(f"Input file not found: {input_path}\n")

    output_path = Path(args.output)

    table = pd.read_html(str(input_path), encoding="utf-8", displayed_only=False)[0]
    table = table.rename(columns={"GW": "Gameweek"})
    table.to_csv(output_path, index=False)


if __name__ == "__main__":
    main()
