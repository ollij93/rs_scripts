#!/usr/bin/env python3
"""Compare Old School RuneScape boss and raid counts for multiple players."""

import argparse
import json
import subprocess
import sys
import unicodedata
from urllib.parse import quote


HISCORES_ROOT = "https://secure.runescape.com/m=hiscore_oldschool"
HISCORES_WS_URL = f"{HISCORES_ROOT}/index_lite.ws?player={{}}"
HISCORES_JSON_URL = f"{HISCORES_ROOT}/index_lite.json?player={{}}"
NON_BOSS_ACTIVITIES = {
    "Grid Points",
    "League Points",
    "Deadman Points",
    "Bounty Hunter - Hunter",
    "Bounty Hunter - Rogue",
    "Bounty Hunter (Legacy) - Hunter",
    "Bounty Hunter (Legacy) - Rogue",
    "Clue Scrolls (all)",
    "Clue Scrolls (beginner)",
    "Clue Scrolls (easy)",
    "Clue Scrolls (medium)",
    "Clue Scrolls (hard)",
    "Clue Scrolls (elite)",
    "Clue Scrolls (master)",
    "LMS - Rank",
    "PvP Arena - Rank",
    "Soul Wars Zeal",
    "Rifts closed",
    "Colosseum Glory",
    "Collections Logged",
}
GREEN = "\033[32m"
RED = "\033[31m"
RESET = "\033[0m"


def fetch_text(url, player, source):
    """Fetch one hiscores response and return its body text."""
    result = subprocess.run(
        ["curl", "--silent", "--show-error", "--location", "--write-out", "\n%{http_code}", url],
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    if result.returncode != 0:
        detail = result.stderr.strip() or f"curl exited with status {result.returncode}"
        raise RuntimeError(f"Could not query hiscores for {player} ({source}): {detail}")
    try:
        body, status_text = result.stdout.rsplit("\n", 1)
        status = int(status_text)
    except (ValueError, IndexError) as error:
        raise RuntimeError(
            f"Could not query hiscores for {player} ({source}): invalid HTTP response"
        ) from error
    if status == 404:
        raise RuntimeError(f"Could not query hiscores for {player}: account not found")
    if not 200 <= status < 300:
        raise RuntimeError(f"Could not query hiscores for {player} ({source}): HTTP {status}")
    return body


def query_activity_scores(player):
    """Read activity names from the official JSON API and scores from index_lite.ws."""
    encoded_player = quote(player, safe="")
    metadata_text = fetch_text(
        HISCORES_JSON_URL.format(encoded_player), player, "activity names"
    )
    try:
        metadata = json.loads(metadata_text)
        activities = metadata["activities"]
        skills = metadata["skills"]
    except (json.JSONDecodeError, KeyError, TypeError) as error:
        raise RuntimeError(f"Could not read activity names for {player}: invalid response") from error

    if not isinstance(activities, list) or not isinstance(skills, list):
        raise RuntimeError(f"Could not read activity names for {player}: invalid response")
    if not all(isinstance(activity, dict) and isinstance(activity.get("name"), str)
               for activity in activities):
        raise RuntimeError(f"Could not read activity names for {player}: invalid activity list")

    ws_text = fetch_text(HISCORES_WS_URL.format(encoded_player), player, "activity scores")
    lines = ws_text.splitlines()
    if len(lines) != len(skills) + len(activities):
        raise RuntimeError(
            f"Could not align hiscores rows for {player}: received {len(lines)} rows, "
            f"but the named response has {len(skills)} skills and {len(activities)} activities"
        )

    score_by_name = {}
    first_activity_row = len(skills)
    for activity, line in zip(activities, lines[first_activity_row:]):
        fields = line.split(",")
        if len(fields) != 2:
            raise RuntimeError(
                f"Could not read hiscores for {player}: invalid {activity['name']} row"
            )
        try:
            score = int(fields[1])
        except ValueError as error:
            raise RuntimeError(
                f"Could not read hiscores for {player}: invalid {activity['name']} score"
            ) from error
        score_by_name[activity["name"]] = score if score >= 0 else None
    return score_by_name


def display_width(value):
    """Count visible terminal columns for table text."""
    value = value.replace(GREEN, "").replace(RED, "").replace(RESET, "")
    return sum(
        0
        if unicodedata.combining(character)
        else 2
        if unicodedata.east_asian_width(character) in {"W", "F"}
        else 1
        for character in value
    )


def pad(value, width):
    """Pad a table cell to its visible terminal width."""
    return value + " " * (width - display_width(value))


def render_table(players, player_data):
    """Render boss and raid counts, with unavailable scores shown as N/A."""
    show_color = sys.stdout.isatty()
    activity_names = []
    for scores in player_data:
        for name in scores:
            if name not in NON_BOSS_ACTIVITIES and name not in activity_names:
                activity_names.append(name)
    activity_names.sort(key=str.casefold)
    headings = ["Boss / Raid", *players]
    rows = []
    for name in activity_names:
        scores = [player_scores.get(name) for player_scores in player_data]
        available_scores = [score for score in scores if score is not None]
        highest = max(available_scores) if available_scores else None
        lowest = min(available_scores) if available_scores else None
        values = [name]
        for score in scores:
            if score is None:
                values.append("N/A")
                continue

            rendered = f"{score:,}"
            if show_color and highest != lowest:
                if score == highest:
                    rendered = f"{GREEN}{rendered}{RESET}"
                elif score == lowest:
                    rendered = f"{RED}{rendered}{RESET}"
            values.append(rendered)
        rows.append(values)
    widths = [
        max([display_width(headings[index])] + [display_width(row[index]) for row in rows])
        for index in range(len(headings))
    ]
    lines = [
        "| " + " | ".join(pad(value, widths[index]) for index, value in enumerate(headings)) + " |",
        "|-" + "-|-".join("-" * width for width in widths) + "-|",
    ]
    for row in rows:
        lines.append(
            "| " + " | ".join(pad(value, widths[index]) for index, value in enumerate(row)) + " |"
        )
    return "\n".join(lines)


def main():
    """Query all named accounts and print their boss and raid counts."""
    parser = argparse.ArgumentParser(
        description="Compare Old School RuneScape boss and raid counts."
    )
    parser.add_argument(
        "players", nargs="+", metavar="PLAYER", help="one or more RuneScape player names"
    )
    args = parser.parse_args()
    try:
        player_data = [query_activity_scores(player) for player in args.players]
        print(render_table(args.players, player_data))
    except (RuntimeError, subprocess.TimeoutExpired) as error:
        print(error, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
