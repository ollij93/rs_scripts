#!/usr/bin/env python3
"""Compare music track unlocks for multiple RuneScape accounts."""

import argparse
import subprocess
import sys
import unicodedata

from query import query_player


def get_music_tracks(player, player_data):
    """Return the track unlock map for one player, or raise a clear error."""
    tracks = player_data.get("music_tracks")
    if not isinstance(tracks, dict):
        raise RuntimeError(
            f"Could not read music tracks for {player}: response has no music track data"
        )

    for track_name, unlocked in tracks.items():
        if not isinstance(track_name, str) or not isinstance(unlocked, bool):
            raise RuntimeError(f"Could not read music tracks for {player}: invalid track entry")
    return tracks


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


def pad_cell(value, width):
    """Pad a table cell to its visible terminal width."""
    return value + " " * (width - display_width(value))


def render_music_table(players, player_tracks):
    """Render every track reported for any player in an aligned table."""
    track_names = sorted(
        set().union(*(tracks.keys() for tracks in player_tracks)),
        key=str.casefold,
    )
    rows = [
        [track_name]
        + ["✅" if tracks.get(track_name, False) else "❌" for tracks in player_tracks]
        for track_name in track_names
    ]
    headings = ["Music Track", *players]
    widths = [
        max([display_width(headings[index])] + [display_width(row[index]) for row in rows])
        for index in range(len(headings))
    ]

    # Use terminal-visible widths so the emoji columns line up with account names.
    lines = [
        "| " + " | ".join(pad_cell(value, widths[index]) for index, value in enumerate(headings)) + " |",
        "|-" + "-|-".join("-" * width for width in widths) + "-|",
    ]
    for row in rows:
        lines.append(
            "| " + " | ".join(pad_cell(value, widths[index]) for index, value in enumerate(row)) + " |"
        )
    return "\n".join(lines)


def main():
    """Query each account and print its music track comparison."""
    parser = argparse.ArgumentParser(
        description="Compare unlocked music tracks for RuneScape accounts."
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
        player_tracks = [
            get_music_tracks(player, data)
            for player, data in zip(args.players, player_data)
        ]
        print(render_music_table(args.players, player_tracks))
    except (RuntimeError, subprocess.TimeoutExpired) as error:
        print(error, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
