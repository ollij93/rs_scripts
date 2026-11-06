#!/usr/bin/env python3
"""Compare completed combat achievement IDs for RuneLite Sync accounts."""

import argparse
import subprocess
import sys
import unicodedata

from query import query_player
from task_names import get_task_name, load_task_name_catalog


def get_completed_ids(player, player_data):
    """Return a validated set of completed achievement IDs for one account."""
    achievement_ids = player_data.get("combat_achievements")
    if not isinstance(achievement_ids, list):
        raise RuntimeError(
            f"Could not read combat achievements for {player}: "
            "response has no achievement data"
        )

    if any(not isinstance(achievement_id, int) or isinstance(achievement_id, bool)
           for achievement_id in achievement_ids):
        raise RuntimeError(
            f"Could not read combat achievements for {player}: "
            "response contains an invalid achievement ID"
        )
    return set(achievement_ids)


def render_table(players, completed_ids, task_names):
    """Render all reported achievements with Wiki names when available."""
    achievement_ids = sorted(set().union(*completed_ids))
    headings = ["Combat Achievement ID", *players]
    rows = [
        [get_task_name(achievement_id, task_names)]
        + ["✅" if achievement_id in player_ids else "❌" for player_ids in completed_ids]
        for achievement_id in achievement_ids
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
        """Pad a table cell to its visible terminal width."""
        return value + " " * (width - display_width(value))

    widths = [
        max([display_width(headings[index])] + [display_width(row[index]) for row in rows])
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
    """Query accounts and print their combat achievement comparison."""
    parser = argparse.ArgumentParser(
        description="Compare completed RuneScape combat achievements."
    )
    parser.add_argument(
        "players",
        nargs="+",
        metavar="PLAYER",
        help="one or more RuneScape player names",
    )
    args = parser.parse_args()

    try:
        # Use the bundled ID map so Wiki access limits do not hide task names.
        task_names = load_task_name_catalog("combat_achievements")
        player_data = [query_player(player, "STANDARD") for player in args.players]
        completed_ids = [
            get_completed_ids(player, data)
            for player, data in zip(args.players, player_data)
        ]
        if not any(completed_ids):
            raise RuntimeError("No combat achievement IDs were returned for these accounts.")
        print(render_table(args.players, completed_ids, task_names))
    except (RuntimeError, subprocess.TimeoutExpired) as error:
        print(error, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
