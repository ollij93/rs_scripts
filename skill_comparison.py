#!/usr/bin/env python3
"""Compare the level and experience of each skill for multiple players."""

import argparse
import subprocess
import sys
import unicodedata
from urllib.parse import quote


HISCORES_URL = (
    "https://secure.runescape.com/m=hiscore_oldschool/index_lite.ws?player={}"
)
SKILLS = [
    "Overall",
    "Attack",
    "Defence",
    "Strength",
    "Hitpoints",
    "Ranged",
    "Prayer",
    "Magic",
    "Cooking",
    "Woodcutting",
    "Fletching",
    "Fishing",
    "Firemaking",
    "Crafting",
    "Smithing",
    "Mining",
    "Herblore",
    "Agility",
    "Thieving",
    "Slayer",
    "Farming",
    "Runecraft",
    "Hunter",
    "Construction",
    "Sailing",
]
GREEN = "\033[32m"
RED = "\033[31m"
RESET = "\033[0m"


def query_hiscores(player):
    """Return level and XP data from the official Old School hiscores."""
    url = HISCORES_URL.format(quote(player, safe=""))
    result = subprocess.run(
        [
            "curl",
            "--silent",
            "--show-error",
            "--location",
            "--write-out",
            "\n%{http_code}",
            url,
        ],
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    if result.returncode != 0:
        detail = result.stderr.strip() or f"curl exited with status {result.returncode}"
        raise RuntimeError(f"Could not query hiscores for {player}: {detail}")

    try:
        body, status_text = result.stdout.rsplit("\n", 1)
        status = int(status_text)
    except (ValueError, IndexError) as error:
        raise RuntimeError(f"Could not query hiscores for {player}: invalid HTTP response") from error
    if not 200 <= status < 300:
        raise RuntimeError(f"Could not query hiscores for {player}: HTTP {status}")

    lines = body.splitlines()
    if len(lines) < len(SKILLS):
        raise RuntimeError(
            f"Could not read hiscores for {player}: expected at least {len(SKILLS)} skill rows, "
            f"received {len(lines)}"
        )

    skill_data = {}
    for skill, line in zip(SKILLS, lines):
        try:
            _, level, xp = (int(value) for value in line.split(","))
        except ValueError as error:
            raise RuntimeError(
                f"Could not read hiscores for {player}: invalid {skill} row"
            ) from error
        skill_data[skill] = {
            "level": level if level >= 0 else None,
            "xp": xp if xp >= 0 else None,
        }
    return skill_data


def render_skill_table(players, player_data, use_color=True):
    """Render one row per skill and highlight the highest and lowest values."""
    show_color = use_color and sys.stdout.isatty()

    def display_width(value):
        """Count terminal columns for account names and skill labels."""
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
        return value + " " * (width - display_width(value))

    def colour(value, all_values):
        """Colour unique extremes for one metric across all players."""
        available = [number for number in all_values if number is not None]
        if not show_color or value is None or not available:
            return "N/A" if value is None else f"{value:,}"
        highest = max(available)
        lowest = min(available)
        rendered = f"{value:,}"
        if highest == lowest:
            return rendered
        if value == highest:
            return f"{GREEN}{rendered}{RESET}"
        if value == lowest:
            return f"{RED}{rendered}{RESET}"
        return rendered

    rows = []
    for skill in SKILLS:
        level_values = [data[skill]["level"] for data in player_data]
        xp_values = [data[skill]["xp"] for data in player_data]
        row = [skill]
        for index, data in enumerate(player_data):
            level = data[skill]["level"]
            xp = data[skill]["xp"]
            row.append(
                f"{colour(level, level_values)} / {colour(xp, xp_values)}"
            )
        rows.append(row)

    headings = ["Skill", *players]
    subheadings = ["", *(["Level / XP"] * len(players))]
    widths = [
        max(
            [display_width(headings[index]), display_width(subheadings[index])]
            + [display_width(row[index]) for row in rows]
        )
        for index in range(len(headings))
    ]
    lines = [
        "| "
        + " | ".join(
            pad(value, widths[index]) for index, value in enumerate(headings)
        )
        + " |",
        "| "
        + " | ".join(
            pad(value, widths[index]) for index, value in enumerate(subheadings)
        )
        + " |",
        "|-" + "-|-".join("-" * width for width in widths) + "-|",
    ]
    for row in rows:
        lines.append(
            "| "
            + " | ".join(
                pad(value, widths[index]) for index, value in enumerate(row)
            )
            + " |"
        )
    return "\n".join(lines)


def main():
    """Read account names, query their hiscores, and print the comparison."""
    parser = argparse.ArgumentParser(description="Compare RuneScape skill levels and XP.")
    parser.add_argument(
        "players",
        nargs="+",
        metavar="PLAYER",
        help="one or more RuneScape player names",
    )
    args = parser.parse_args()

    try:
        player_data = [query_hiscores(player) for player in args.players]
        print(render_skill_table(args.players, player_data))
    except (RuntimeError, subprocess.TimeoutExpired) as error:
        print(error, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
