#!/usr/bin/env python3
"""Compare achievement diary task progress for RuneScape accounts."""

import argparse
import subprocess
import sys
import unicodedata

from query import query_player


TIERS = ("Easy", "Medium", "Hard", "Elite")
GREEN = "\033[32m"
RED = "\033[31m"
RESET = "\033[0m"


def diary_rows(player_data):
    """Return the sorted set of region and tier pairs in the account data."""
    pairs = set()
    for data in player_data:
        diaries = data.get("achievement_diaries")
        if not isinstance(diaries, dict):
            continue
        for region, tiers in diaries.items():
            if isinstance(tiers, dict):
                pairs.update((region, tier) for tier in tiers)

    tier_order = {tier: index for index, tier in enumerate(TIERS)}
    return sorted(
        pairs,
        key=lambda pair: (
            pair[0].casefold(),
            tier_order.get(pair[1], len(TIERS)),
            pair[1].casefold(),
        ),
    )


def progress_cell(player_data, region, tier):
    """Show a tier's completion state and completed task count."""
    diaries = player_data.get("achievement_diaries")
    if not isinstance(diaries, dict):
        return "N/A", None
    tiers = diaries.get(region)
    if not isinstance(tiers, dict):
        return "N/A", None
    tier_data = tiers.get(tier)
    if not isinstance(tier_data, dict):
        return "N/A", None

    tasks = tier_data.get("tasks")
    if not isinstance(tasks, list) or not all(isinstance(task, bool) for task in tasks):
        return "N/A", None

    completed = sum(tasks)
    complete = tier_data.get("complete")
    # The API provides both the tier flag and task states; use the flag for the
    # indicator while keeping the task count visible for partial completion.
    indicator = "✅" if complete is True else "❌" if complete is False else "❓"
    return f"{indicator} {completed}/{len(tasks)}", completed


def render_table(players, player_data):
    """Render one row per region and tier with one progress column per player."""
    show_color = sys.stdout.isatty()
    rows = []
    for region, tier in diary_rows(player_data):
        progress = [progress_cell(data, region, tier) for data in player_data]
        counts = [count for _, count in progress if count is not None]
        highest = max(counts) if counts else None
        lowest = min(counts) if counts else None
        values = []
        for value, count in progress:
            if show_color and count is not None and highest != lowest:
                if count == highest:
                    value = f"{GREEN}{value}{RESET}"
                elif count == lowest:
                    value = f"{RED}{value}{RESET}"
            values.append(value)
        rows.append([region, tier, *values])

    headings = ["Region", "Tier", *players]

    def display_width(value):
        """Count terminal columns for text and wide completion symbols."""
        value = value.replace(GREEN, "").replace(RED, "").replace(RESET, "")
        width = 0
        for character in value:
            if unicodedata.combining(character):
                continue
            if character in {"✅", "❌", "❓"}:
                width += 2
            elif unicodedata.east_asian_width(character) in {"W", "F"}:
                width += 2
            else:
                width += 1
        return width

    def pad(value, width):
        """Pad a table cell by its visible terminal width."""
        return value + " " * (width - display_width(value))

    widths = [
        max(
            [display_width(headings[index])]
            + [display_width(row[index]) for row in rows]
        )
        for index in range(len(headings))
    ]
    lines = [
        "| "
        + " | ".join(pad(value, widths[index]) for index, value in enumerate(headings))
        + " |",
        "|-" + "-|-".join("-" * width for width in widths) + "-|",
    ]
    for row in rows:
        lines.append(
            "| "
            + " | ".join(pad(value, widths[index]) for index, value in enumerate(row))
            + " |"
        )
    return "\n".join(lines)


def main():
    """Query each account and print its achievement diary comparison."""
    parser = argparse.ArgumentParser(
        description="Compare achievement diary task progress for RuneScape accounts."
    )
    parser.add_argument(
        "players",
        nargs="+",
        metavar="PLAYER",
        help="one or more RuneScape player names",
    )
    args = parser.parse_args()

    try:
        player_data = [query_player(player, "STANDARD") for player in args.players]
        if not any(isinstance(data.get("achievement_diaries"), dict) for data in player_data):
            raise RuntimeError("No achievement diary data was returned for these accounts.")
        print(render_table(args.players, player_data))
    except (RuntimeError, subprocess.TimeoutExpired) as error:
        print(error, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
