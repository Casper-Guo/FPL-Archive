"""Download FPL fixture and player performance data."""

import argparse
from pathlib import Path
from time import sleep

import pandas as pd
import requests

PLAYER_OVERVIEW_COLUMNS = [
    # metadata
    "id",
    "team",
    "position",
    "first_name",
    "second_name",
    "web_name",
    "known_name",
    "team_join_date",
    "birth_date",
    # fpl stats
    "total_points",
    "bonus",
    "bps",
    "minutes",
    "starts",
    "goals_scored",
    "assists",
    "clean_sheets",
    "goals_conceded",
    "own_goals",
    "penalties_saved",
    "penalties_missed",
    "yellow_cards",
    "red_cards",
    "saves",
    "clearances_blocks_interceptions",
    "recoveries",
    "tackles",
    "defensive_contribution",
    # expected stats
    "expected_goals",
    "expected_assists",
    "expected_goal_involvements",
    "expected_goals_conceded",
    # per 90 stats
    "points_per_game",
    "points_per_game_rank",
    "points_per_game_rank_type",
    "saves_per_90",
    "goals_conceded_per_90",
    "starts_per_90",
    "clean_sheets_per_90",
    "defensive_contribution_per_90",
    # per 90 expected stats
    "expected_goals_per_90",
    "expected_assists_per_90",
    "expected_goal_involvements_per_90",
    "expected_goals_conceded_per_90",
    # ict stats
    "influence",
    "creativity",
    "threat",
    "ict_index",
    "influence_rank",
    "influence_rank_type",
    "creativity_rank",
    "creativity_rank_type",
    "threat_rank",
    "threat_rank_type",
    "ict_index_rank",
    "ict_index_rank_type",
]


def flatten_player_gameweek_performance_data(data: dict, gameweek: int) -> dict:
    """Reorganize the player gameweek performance data from the API."""
    flattened_data = {
        "id": data["id"],
        "gameweek": gameweek,
        # this field is missing for blank gameweeks
        "fixture_id": data["explain"][0]["fixture"] if data["explain"] else None,
        **data["stats"],
    }
    flattened_data.pop("in_dreamteam")
    return flattened_data


def main() -> None:  # noqa: D103
    parser = argparse.ArgumentParser(description="Download FPL API data")
    parser.add_argument("output", help="Path to the output directory")
    args = parser.parse_args()
    output_dir = Path(args.output)

    if not output_dir.exists():
        output_dir.mkdir(parents=True)
    if not output_dir.is_dir():
        raise ValueError(f"Output path is not a directory: {output_dir}\n")

    metadata = requests.get("https://fantasy.premierleague.com/api/bootstrap-static/").json()
    fpl_positions = pd.json_normalize(metadata["element_types"])[
        ["id", "singular_name_short"]
    ].rename(columns={"singular_name_short": "position"})

    fpl_teams = pd.json_normalize(metadata["teams"])[["id", "name", "short_name"]]
    fpl_teams.to_csv(output_dir / "teams.csv", index=False)

    player_overview = pd.json_normalize(metadata["elements"])
    player_overview = (
        player_overview.merge(
            fpl_teams,
            left_on="team",
            right_on="id",
            how="left",
            suffixes=("", "_team"),
        )
        .drop(columns=["team", "id_team", "short_name"])
        # there is no player "name" column so this column get no suffix
        .rename(columns={"name": "team"})
    )
    player_overview = player_overview.merge(
        fpl_positions,
        left_on="element_type",
        right_on="id",
        how="left",
        suffixes=("", "_position"),
    ).drop(columns=["element_type", "id_position"])

    # filter and reorder columns
    player_overview = player_overview[PLAYER_OVERVIEW_COLUMNS]
    player_overview.to_csv(output_dir / "player_overview.csv", index=False)

    fixtures = requests.get("https://fantasy.premierleague.com/api/fixtures/").json()
    fpl_fixtures = pd.json_normalize(fixtures)[
        [
            "event",
            "id",
            "kickoff_time",
            "team_a",
            "team_h",
            "team_a_score",
            "team_h_score",
            "team_a_difficulty",
            "team_h_difficulty",
        ]
    ].rename(
        columns={
            "event": "Gameweek",
            "team_a": "away_id",
            "team_h": "home_id",
            "team_a_score": "away_score",
            "team_h_score": "home_score",
            "team_a_difficulty": "away_difficulty",
            "team_h_difficulty": "home_difficulty",
        },
    )
    fpl_fixtures.to_csv(output_dir / "fixtures.csv", index=False)

    per_gameweek_performance: list[dict] = []

    for gameweek in range(1, 39):
        raw_data = requests.get(
            f"https://fantasy.premierleague.com/api/event/{gameweek}/live/",
        ).json()["elements"]
        per_gameweek_performance.extend(
            flatten_player_gameweek_performance_data(d, gameweek) for d in raw_data
        )
        sleep(0.5)

    df_performance = pd.DataFrame.from_records(per_gameweek_performance)
    df_performance.to_csv(output_dir / "player_gameweek_performance.csv", index=False)


if __name__ == "__main__":
    main()
