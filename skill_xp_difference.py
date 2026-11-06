#!/usr/bin/env python3
"""Compare skill XP differences for two RuneScape players."""

import argparse
import subprocess
import sys
import unicodedata

from skill_comparison import SKILLS, query_hiscores


GREEN = "\033[32m"
RED = "\033[31m"
RESET = "\033[0m"


def render_difference_table(player_a, player_b, data_a, data_b):
    """Render skill XP values, sorted by player B XP minus player A XP."""
    show_color = sys.stdout.isatty()
    rows = []
    for skill in SKILLS:
        xp_a = data_a[skill]["xp"]
        xp_b = data_b[skill]["xp"]
        difference = xp_b - xp_a if xp_a is not None and xp_b is not None else None
        rows.append((skill, xp_a, xp_b, difference))

    # Missing XP values sort after rows with a usable signed difference.
    rows.sort(
        key=lambda row: (row[3] is None, row[3] if row[3] is not None else 0)
    )

    def display_width(value):
        """Count terminal columns for skill names and account names."""
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

    def format_xp(value):
        return "N/A" if value is None else f"{value:,}"

    def colour_xp(value, other_value):
        """Use the same per-skill high and low colours as the skill table."""
        rendered = format_xp(value)
        if not show_color or value is None or other_value is None or value == other_value:
            return rendered
        if value > other_value:
            return f"{GREEN}{rendered}{RESET}"
        return f"{RED}{rendered}{RESET}"

    def format_difference(value):
        return "N/A" if value is None else f"{value:+,}"

    headings = [
        "Skill",
        player_a,
        player_b,
        f"XP Difference ({player_b} - {player_a})",
    ]
    widths = [
        max(
            [display_width(headings[index])]
            + [
                display_width(
                    row[index]
                    if index == 0
                    else format_xp(row[index])
                    if index in {1, 2}
                    else format_difference(row[index])
                )
                for row in rows
            ]
        )
        for index in range(len(headings))
    ]

    lines = [
        "| "
        + " | ".join(
            pad(heading, widths[index]) for index, heading in enumerate(headings)
        )
        + " |",
        "|-" + "-|-".join("-" * width for width in widths) + "-|",
    ]
    for skill, xp_a, xp_b, difference in rows:
        values = [
            skill,
            colour_xp(xp_a, xp_b),
            colour_xp(xp_b, xp_a),
            format_difference(difference),
        ]
        lines.append(
            "| "
            + " | ".join(
                pad(value, widths[index]) for index, value in enumerate(values)
            )
            + " |"
        )
    return "\n".join(lines)


def main():
    """Query two accounts and print their skill XP differences."""
    parser = argparse.ArgumentParser(
        description="Compare skill XP differences for two RuneScape players."
    )
    parser.add_argument("player_a", metavar="PLAYER_A", help="first RuneScape player name")
    parser.add_argument("player_b", metavar="PLAYER_B", help="second RuneScape player name")
    args = parser.parse_args()

    try:
        data_a = query_hiscores(args.player_a)
        data_b = query_hiscores(args.player_b)
        print(render_difference_table(args.player_a, args.player_b, data_a, data_b))
    except (RuntimeError, subprocess.TimeoutExpired) as error:
        print(error, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
