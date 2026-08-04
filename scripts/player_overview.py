"""Prompt for player names and print their player card statistics."""

import argparse
import sys
import unicodedata
from pathlib import Path

import pandas as pd
from rapidfuzz import fuzz, process
from tabulate import tabulate

# letters that unicode decomposition leaves alone
TRANSLITERATIONS = str.maketrans({"ø": "o", "đ": "d", "ı": "i", "ł": "l"})  # noqa: RUF001

# defensive contributions needed in one game to score DEFCON points
DEFCON_THRESHOLD = {"DEF": 10, "MID": 12, "FWD": 12}

# a name containing every word of the query scores this much
PERFECT_PARTIAL_MATCH = 100

# lowest score accepted as a match
SCORE_FLOOR = 75
# spread within which matches are considered ambiguous
SCORE_MARGIN = 10

# card columns per position, mirroring the issue templates, as (header, column, precision)
CARDS: dict[str, tuple[tuple[str, str, int], ...]] = {
    "FWD": (
        ("Pts", "total_points", 0),
        ("B23", "bonus_23", 0),
        ("MP", "minutes", 0),
        ("G", "goals_scored", 0),
        ("A", "assists", 0),
        ("xA", "expected_assists", 2),
        ("Pts/90", "total_points_per_90", 2),
        ("G/90", "goals_scored_per_90", 2),
        ("A/90", "assists_per_90", 2),
        ("xA/90", "expected_assists_per_90", 2),
    ),
    "MID": (
        ("Pts", "total_points", 0),
        ("B23", "bonus_23", 0),
        ("MP", "minutes", 0),
        ("G", "goals_scored", 0),
        ("A", "assists", 0),
        ("xA", "expected_assists", 2),
        ("DC", "defensive_contribution", 0),
        ("DC12+", "defcon_hits", 0),
        ("Pts/90", "total_points_per_90", 2),
        ("G/90", "goals_scored_per_90", 2),
        ("A/90", "assists_per_90", 2),
        ("xA/90", "expected_assists_per_90", 2),
        ("DC/90", "defensive_contribution_per_90", 2),
    ),
    "DEF": (
        ("Pts", "total_points", 0),
        ("B23", "bonus_23", 0),
        ("MP", "minutes", 0),
        ("GA", "goals_conceded", 0),
        ("xGA", "expected_goals_conceded", 2),
        ("G", "goals_scored", 0),
        ("A", "assists", 0),
        ("CS", "clean_sheets", 0),
        ("DC", "defensive_contribution", 0),
        ("DC10+", "defcon_hits", 0),
        ("Pts/90", "total_points_per_90", 2),
        ("GA/90", "goals_conceded_per_90", 2),
        ("xGA/90", "expected_goals_conceded_per_90", 2),
        ("G/90", "goals_scored_per_90", 2),
        ("A/90", "assists_per_90", 2),
        ("DC/90", "defensive_contribution_per_90", 2),
    ),
    "GKP": (
        ("Pts", "total_points", 0),
        ("B23", "bonus_23", 0),
        ("MP", "minutes", 0),
        ("GA", "goals_conceded", 0),
        ("xGA", "expected_goals_conceded", 2),
        ("S", "saves", 0),
        ("CS", "clean_sheets", 0),
        ("Pts/90", "total_points_per_90", 2),
        ("GA/90", "goals_conceded_per_90", 2),
        ("xGA/90", "expected_goals_conceded_per_90", 2),
        ("S/90", "saves_per_90", 2),
    ),
}

# per game columns summed into season totals
SUM_COLUMNS = (
    "total_points",
    "minutes",
    "goals_scored",
    "assists",
    "clean_sheets",
    "goals_conceded",
    "saves",
    "defensive_contribution",
    "expected_assists",
    "expected_goals_conceded",
)

PER_90_COLUMNS = (
    "total_points",
    "goals_scored",
    "assists",
    "expected_assists",
    "goals_conceded",
    "expected_goals_conceded",
    "saves",
    "defensive_contribution",
)


def to_ascii(name: str) -> str:
    """Strip unicode accent marks and case."""
    stripped = "".join(
        c for c in unicodedata.normalize("NFD", name) if unicodedata.category(c) != "Mn"
    )
    return stripped.casefold().translate(TRANSLITERATIONS)


def build_players(data_dir: Path) -> pd.DataFrame:
    """Derive every statistic shown on a player card from the per game data."""
    games = pd.read_csv(data_dir / "merged_gw.csv")
    idlist = pd.read_csv(data_dir / "player_idlist.csv")

    # fix GK position inconsistency
    games["position"] = games["position"].replace({"GK": "GKP"})

    df = idlist.set_index("id")
    df["name"] = df["first_name"] + " " + df["second_name"]
    df["position"] = games.groupby("element")["position"].last()
    df["team"] = games.sort_values("kickoff_time").groupby("element")["team"].last()
    df[list(SUM_COLUMNS)] = games.groupby("element")[list(SUM_COLUMNS)].sum()

    hit_bonus = games["bonus"].isin((2, 3))
    hit_defcon = games["defensive_contribution"] >= games["position"].map(DEFCON_THRESHOLD)
    for column, hits in (("bonus_23", hit_bonus), ("defcon_hits", hit_defcon)):
        counts = games[hits].groupby("element").size()
        df[column] = counts.reindex(df.index, fill_value=0)

    for column in PER_90_COLUMNS:
        df[f"{column}_per_90"] = (df[column] / df["minutes"] * 90).where(df["minutes"] > 0)

    df["search_name"] = df["name"].map(to_ascii)

    return df


def select_player(matches: pd.DataFrame) -> pd.Series | None:
    """Ask the user to disambiguate between similarly named players."""
    options = "\n".join(
        f"  {index}) {row['name']} ({row['position']}, {row['team']})"
        for index, (_, row) in enumerate(matches.iterrows())
    )
    while True:
        try:
            choice = input(f"Multiple matches:\n{options}\nSelect: ").strip()
        except (EOFError, KeyboardInterrupt):
            sys.stderr.write("\nSkipped.\n")
            return None
        if choice.isdigit() and int(choice) < len(matches):
            return matches.iloc[int(choice)]
        sys.stderr.write("Invalid selection.\n")


def resolve_player(df: pd.DataFrame, query: str) -> pd.Series | None:
    """Look for perfect partial match before fuzzy matching names."""
    names = df["search_name"].tolist()
    folded = to_ascii(query)

    partial = process.extract(folded, names, scorer=fuzz.token_set_ratio, limit=None)
    matched = [index for _, score, index in partial if score == PERFECT_PARTIAL_MATCH]

    if not matched:
        ranked = process.extract(folded, names, scorer=fuzz.WRatio, limit=5)
        best = ranked[0][1]
        matched = [
            index
            for _, score, index in ranked
            if score >= max(best - SCORE_MARGIN, SCORE_FLOOR)
        ]

    if not matched:
        sys.stderr.write(f"No matches for {query}.\n")
        return None
    if len(matched) == 1:
        return df.iloc[matched[0]]
    return select_player(df.iloc[matched])


def format_value(value: float, precision: int) -> str:
    """Render one statistic, leaving values undefined by a lack of minutes blank."""
    if pd.isna(value):
        return "-"
    return f"{value:.{precision}f}"


def format_table(player: pd.Series) -> str:
    """Tabulate the player card statistics for one player, one row per statistic."""
    card = CARDS[player["position"]]
    rows = [
        (header, format_value(player[column], precision)) for header, column, precision in card
    ]
    # the values are preformatted, so numparse stays off to keep their trailing zeros
    table = tabulate(
        rows,
        headers=["Stat", "Value"],
        tablefmt="rounded_grid",
        disable_numparse=True,
    )
    return f"{player['name']} ({player['position']}, {player['team']})\n{table}"


def main() -> None:  # noqa: D103
    parser = argparse.ArgumentParser(
        description="Print player card statistics, one player at a time.",
    )
    parser.add_argument(
        "-d",
        "--data",
        default=Path(__file__).parent.parent / "25-26" / "vaastav",
        type=Path,
        help="Path to the season data directory",
    )
    args = parser.parse_args()

    df = build_players(args.data)

    while True:
        try:
            query = input("\nPlayer name: ").strip()
        except (EOFError, KeyboardInterrupt):
            sys.stderr.write("\n")
            return

        if not query:
            continue
        if (player := resolve_player(df, query)) is not None:
            sys.stdout.write(f"\n{format_table(player)}\n")


if __name__ == "__main__":
    main()
