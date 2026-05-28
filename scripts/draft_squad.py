"""Extract squad history for each manager (after auto-subs)."""

import argparse
import json
from pathlib import Path
from time import sleep

from bs4 import BeautifulSoup
from playwright import sync_api

MANAGER_IDS = (46472, 46532, 57636, 58827)


def extract_names(html: str) -> tuple[list[str], list[str]]:
    """Parse starters and bench (after auto-sub) from HTML."""
    soup = BeautifulSoup(html, "html.parser")
    pitch = soup.select_one('[class*="StyledPitch"]')

    starters: list[str] = []
    benched: list[str] = []

    if pitch is not None:
        for row in pitch.select('[class*="PitchRow"]'):
            starters.extend(
                name.get_text(strip=True)
                for name in row.select('[class*="ElementName"]')
                if name.get_text(strip=True)
            )

        bench = pitch.select_one('[class*="StyledBench"]')
        if bench is not None:
            benched.extend(
                name.get_text(strip=True)
                for name in bench.select('[class*="ElementName"]')
                if name.get_text(strip=True)
            )

    return starters, benched


def main() -> None:  # noqa: D103
    parser = argparse.ArgumentParser(
        description="Download and write each manager's squad history into JSON.",
    )
    parser.add_argument("output", help="Path to the output directory")
    args = parser.parse_args()
    output_path = Path(args.output)

    if not output_path.exists():
        output_path.mkdir(parents=True)
    if not output_path.is_dir():
        raise ValueError(f"{output_path} is not a directory")

    squad_list: dict[int, list[dict]] = {manager: [] for manager in MANAGER_IDS}

    with sync_api.sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page()

        for manager_id in MANAGER_IDS:
            for gameweek in range(1, 39):
                page.goto(
                    f"https://draft.premierleague.com/entry/{manager_id}/event/{gameweek}",
                    wait_until="networkidle",
                )
                html = page.content()
                starters, bench = extract_names(html)
                squad_list[manager_id].append(
                    {
                        "gameweek": gameweek,
                        "starters": starters,
                        "bench": bench,
                    },
                )
                sleep(0.1)
            sleep(1)

        browser.close()

    with (output_path / "squad_history.json").open("w", encoding="utf-8") as f:
        json.dump(squad_list, f, indent=4, ensure_ascii=False)


if __name__ == "__main__":
    main()
