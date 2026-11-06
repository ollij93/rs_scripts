#!/usr/bin/env python3
"""Compare fields in RuneLite Sync player data."""

import argparse
import json
import subprocess
import sys

from query import query_player


def get_field(document, field_path):
    """Read a value by its dot-separated path."""
    value = document
    for name in field_path.split("."):
        try:
            value = value[name]
        except (KeyError, TypeError) as error:
            raise ValueError(f"Field '{field_path}' was not found in the response") from error
    return value


def compare_values(player_a, player_b, left, right, label="Values"):
    """Return a readable difference between two values."""
    if isinstance(left, list) and isinstance(right, list):
        # Show only unique values that one player has and the other does not.
        only_a = sorted(set(left) - set(right), key=str)
        only_b = sorted(set(right) - set(left), key=str)
        lines = [f"{label} {player_a} has that {player_b} does not:"]
        lines.extend(str(value) for value in only_a)
        lines.extend(("", f"{label} {player_b} has that {player_a} does not:"))
        lines.extend(str(value) for value in only_b)
        return "\n".join(lines)

    return f"{player_a}: {json.dumps(left, indent=2)}\n{player_b}: {json.dumps(right, indent=2)}"


def compare_documents(player_a, player_b, data_a, data_b, field, label="Values"):
    """Compare one field in two player response documents."""
    left = get_field(data_a, field)
    right = get_field(data_b, field)
    return compare_values(player_a, player_b, left, right, label)


def main():
    """Run the query-and-compare command-line interface."""
    parser = argparse.ArgumentParser(description="Compare a RuneLite Sync field for two players.")
    parser.add_argument("player_a", help="first RuneScape player name")
    parser.add_argument("player_b", help="second RuneScape player name")
    parser.add_argument("--activity", required=True, help="RuneLite Sync activity or data category")
    parser.add_argument("--field", required=True, help="dot-separated JSON field to compare")
    args = parser.parse_args()

    try:
        data_a = query_player(args.player_a, args.activity)
        data_b = query_player(args.player_b, args.activity)
        print(compare_documents(args.player_a, args.player_b, data_a, data_b, args.field))
    except (RuntimeError, ValueError, subprocess.TimeoutExpired) as error:
        print(error, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
