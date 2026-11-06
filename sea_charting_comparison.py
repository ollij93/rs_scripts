#!/usr/bin/env python3
"""Compare reported sea charting completions for multiple players."""

import argparse
import subprocess
import sys
import unicodedata

from query import query_player
from task_names import get_task_name, load_task_name_catalog


def get_completed_ids(player, player_data):
    """Return validated completed sea charting IDs for one player."""
    completed_ids = player_data.get("sea_charting")
    if not isinstance(completed_ids, list):
        raise RuntimeError(
            f"Could not read sea charting data for {player}: "
            "response has no sea charting data"
        )

    if any(
        not isinstance(task_id, int) or isinstance(task_id, bool)
        for task_id in completed_ids
    ):
        raise RuntimeError(
            f"Could not read sea charting data for {player}: "
            "response contains an invalid task ID"
        )
    return set(completed_ids)


def render_table(players, completed_ids, task_names):
    """Render charting tasks by name and each player's completion."""
    task_ids = sorted(set().union(*completed_ids))
    headings = ["Sea Charting Task", *players]
    heading_details = ["", *(f"({len(ids)} reported)" for ids in completed_ids)]
    rows = [
        [get_task_name(task_id, task_names)]
        + ["✅" if task_id in ids else "❌" for ids in completed_ids]
        for task_id in task_ids
    ]

    def display_width(value):
        """Count visible terminal columns, including wide status symbols."""
        width = 0
        for character in value:
            if unicodedata.combining(character):
                continue
            if character in {"✅", "❌"}:
                width += 2
            elif unicodedata.east_asian_width(character) in {"W", "F"}:
                width += 2
            else:
                width += 1
        return width

    def pad(value, width):
        """Pad a cell to its visible terminal width."""
        return value + " " * (width - display_width(value))

    widths = [
        max(
            [display_width(headings[index]), display_width(heading_details[index])]
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
            pad(value, widths[index]) for index, value in enumerate(heading_details)
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
    """Query each account and print its sea charting comparison."""
    parser = argparse.ArgumentParser(
        description="Compare reported RuneScape sea charting completions."
    )
    parser.add_argument(
        "players",
        nargs="+",
        metavar="PLAYER",
        help="one or more RuneScape player names",
    )
    args = parser.parse_args()

    try:
        task_names = load_task_name_catalog("sea_charting")
        player_data = [query_player(player, "STANDARD") for player in args.players]
        completed_ids = [
            get_completed_ids(player, data)
            for player, data in zip(args.players, player_data)
        ]
        print(render_table(args.players, completed_ids, task_names))
    except (RuntimeError, subprocess.TimeoutExpired) as error:
        print(error, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
