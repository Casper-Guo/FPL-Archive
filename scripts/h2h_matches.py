"""Download manager metadata and H2H matches."""

import argparse
from pathlib import Path

import pandas as pd
import requests

LEAGUE_ID = 11066


def main() -> None:  # noqa: D103
    parser = argparse.ArgumentParser(
        description="Download manager and H2H match data",
    )
    parser.add_argument("output", help="Output directory")
    args = parser.parse_args()

    dest = Path(args.output)
    if not dest.exists():
        dest.mkdir(parents=True)

    if not dest.is_dir():
        raise ValueError(f"Target is not a directory: {dest}\n")

    raw = requests.get(f"https://draft.premierleague.com/api/league/{LEAGUE_ID}/details").json()

    managers: list[dict] = raw["league_entries"]
    managers = [
        {
            key: manager[key]
            for key in (
                # entry id is used for URL path parameters
                "entry_id",
                # id is used in some API responses such as H2H match results
                "id",
                "entry_name",
                "player_first_name",
                "player_last_name",
                "short_name",
            )
        }
        for manager in managers
    ]
    pd.DataFrame.from_records(managers).to_csv(dest / "managers.csv", index=False)

    standing: list[dict] = raw["standings"]
    for manager in standing:
        manager.pop("last_rank")
        manager.pop("rank_sort")
    pd.DataFrame.from_records(standing).to_csv(dest / "standing.csv", index=False)

    matches: list[dict] = raw["matches"]
    for match in matches:
        match["gameweek"] = match.pop("event")
        for key in ("finished", "started", "winning_league_entry", "winning_method"):
            match.pop(key)
    pd.DataFrame.from_records(matches).to_csv(dest / "matches.csv", index=False)


if __name__ == "__main__":
    main()
