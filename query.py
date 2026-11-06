#!/usr/bin/env python3
"""Query player data from the RuneLite Sync API."""

import argparse
import json
import subprocess
import sys
from urllib.parse import quote


API_ROOT = "https://sync.runescape.wiki/runelite/player"
WIKI_ROOT = "https://oldschool.runescape.wiki/"
USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/156.0.0.0 Safari/537.36"
)


def fetch_json(url, player, activity):
    """Fetch and decode one player response from RuneLite Sync."""
    result = subprocess.run(
        [
            "curl",
            "--silent",
            "--show-error",
            "--location",
            "--write-out",
            "\n%{http_code}",
            "--header",
            "Accept: application/json, text/plain, */*",
            "--header",
            f"Referer: {WIKI_ROOT}",
            "--header",
            "Sec-Fetch-Dest: empty",
            "--header",
            "Sec-Fetch-Mode: cors",
            "--header",
            "Sec-Fetch-Site: cross-site",
            "--user-agent",
            USER_AGENT,
            url,
        ],
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )

    if result.returncode != 0:
        detail = result.stderr.strip() or f"curl exited with status {result.returncode}"
        raise RuntimeError(f"Could not query {player} ({activity}): {detail}")

    try:
        body, status_text = result.stdout.rsplit("\n", 1)
        status = int(status_text)
    except (ValueError, IndexError) as error:
        raise RuntimeError(f"Could not query {player} ({activity}): invalid HTTP response") from error

    if status == 403:
        detail = (
            "The Wiki query succeeds in a browser, but this request was denied. "
            "This is a client or network access block, not proof that the player has no data."
        )
        raise RuntimeError(f"Could not query {player} ({activity}): HTTP 403 Forbidden. {detail}")
    if not 200 <= status < 300:
        try:
            error_document = json.loads(body)
        except json.JSONDecodeError:
            error_document = None
        if isinstance(error_document, dict) and isinstance(error_document.get("error"), str):
            raise RuntimeError(
                f"Could not query {player} ({activity}): HTTP {status}: "
                f"{error_document['error']}"
            )
        raise RuntimeError(f"Could not query {player} ({activity}): HTTP {status}")

    try:
        return json.loads(body)
    except json.JSONDecodeError as error:
        raise RuntimeError(f"Could not query {player} ({activity}): response was not valid JSON") from error


def query_player(player, activity):
    """Return the JSON response for one player and activity."""
    url = f"{API_ROOT}/{quote(player, safe='')}/{quote(activity, safe='')}"
    return fetch_json(url, player, activity)


def main():
    """Run the query command-line interface."""
    parser = argparse.ArgumentParser(description="Query RuneLite Sync player data.")
    parser.add_argument("player", help="RuneScape player name")
    parser.add_argument("activity", help="RuneLite Sync activity or data category")
    args = parser.parse_args()

    try:
        data = query_player(args.player, args.activity)
    except (RuntimeError, subprocess.TimeoutExpired) as error:
        print(error, file=sys.stderr)
        return 1

    print(json.dumps(data, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
