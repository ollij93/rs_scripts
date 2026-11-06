#!/usr/bin/env python3
"""Compare quest completion states for multiple RuneScape players."""

import argparse
import subprocess
import sys
import unicodedata

from query import query_player


QUEST_STATES = {
    0: "⏳ In progress",
    1: "❌ Not started",
    2: "✅ Completed",
}
GREEN = "\033[32m"
RED = "\033[31m"
RESET = "\033[0m"


def get_quests(player, player_data):
    """Return the quest state map for one player, or raise a clear error."""
    quests = player_data.get("quests")
    if not isinstance(quests, dict):
        raise RuntimeError(f"Could not read quests for {player}: response has no quest data")

    for quest_name, state in quests.items():
        if not isinstance(quest_name, str) or not isinstance(state, int):
            raise RuntimeError(f"Could not read quests for {player}: invalid quest entry")
    return quests


def render_quest_table(players, player_quests):
    """Render every quest reported for any player in an aligned table."""
    show_color = sys.stdout.isatty()
    quest_names = sorted(
        set().union(*(quests.keys() for quests in player_quests)),
        key=str.casefold,
    )
    rows = []
    for quest_name in quest_names:
        states = [quests.get(quest_name) for quests in player_quests]
        has_completed = any(state == 2 for state in states)
        has_incomplete = any(state in {0, 1} for state in states)
        row = [quest_name]
        for state in states:
            # A missing entry means the API did not report that quest for this player.
            value = QUEST_STATES.get(state, f"Unknown ({state})") if state is not None else "N/A"
            if show_color and has_completed and has_incomplete:
                if state == 2:
                    value = f"{GREEN}{value}{RESET}"
                elif state in {0, 1}:
                    value = f"{RED}{value}{RESET}"
            row.append(value)
        rows.append(row)

    def display_width(value):
        """Count visible terminal columns, including wide status symbols."""
        value = value.replace(GREEN, "").replace(RED, "").replace(RESET, "")
        width = 0
        for character in value:
            if unicodedata.combining(character):
                continue
            if character in {"✅", "❌", "⏳"}:
                width += 2
            elif unicodedata.east_asian_width(character) in {"W", "F"}:
                width += 2
            else:
                width += 1
        return width

    def pad(value, width):
        """Pad a table cell to its visible terminal width."""
        return value + " " * (width - display_width(value))

    headings = ["Quest", *players]
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
    """Query quest data for each account and print the comparison table."""
    parser = argparse.ArgumentParser(description="Compare RuneScape quest completion.")
    parser.add_argument(
        "players",
        nargs="+",
        metavar="PLAYER",
        help="one or more RuneScape player names",
    )
    args = parser.parse_args()

    try:
        player_data = [query_player(player, "STANDARD") for player in args.players]
        player_quests = [
            get_quests(player, data)
            for player, data in zip(args.players, player_data)
        ]
        print(render_quest_table(args.players, player_quests))
    except (RuntimeError, subprocess.TimeoutExpired) as error:
        print(error, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
