"""Convert the trades HTML table into JSON."""

import argparse
import json
from pathlib import Path

import pandas as pd


def main() -> None:
    """Convert the trades HTML table at the input path into JSON."""
    parser = argparse.ArgumentParser(
        description="Convert the trades HTML table into JSON",
    )
    parser.add_argument(
        "input",
        help="Path to the input HTML file",
    )
    parser.add_argument(
        "--output",
        "-o",
        default="trades.json",
        help="Path to the output JSON file",
    )
    args = parser.parse_args()

    input_path = Path(args.input)
    if not input_path.exists() or not input_path.is_file():
        raise ValueError(f"Input file not found: {input_path}\n")

    output_path = Path(args.output)

    table = pd.read_html(str(input_path), encoding="utf-8", displayed_only=False)[0]
    table = table.drop(columns=["Result"])
    table = table.rename(columns={"GW": "Gameweek"})
    table_json = json.loads(table.to_json(orient="records"))

    for trade in table_json:
        trade["Offered"] = trade["Offered"].split(r", ", regex=True)
        trade["Requested"] = trade["Requested"].split(r", ", regex=True)

    with output_path.open("w", encoding="utf-8") as f:
        json.dump(table_json, f, indent=4, ensure_ascii=False)


if __name__ == "__main__":
    main()
