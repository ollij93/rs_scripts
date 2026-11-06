#!/usr/bin/env python3
"""Compare the main-game collection logs for two players."""

import argparse
from html.parser import HTMLParser
import subprocess
import sys
import unicodedata

from query import USER_AGENT, query_player


COLLECTION_LOG_URL = "https://oldschool.runescape.wiki/w/Collection_log/Table"
ITEM_LOOKUP_URL = "https://oldschool.runescape.wiki/w/Special:Lookup?type=item&id={}"


class CollectionLogParser(HTMLParser):
    """Read item IDs, names, and global completion rates from the Wiki table."""

    def __init__(self):
        """Set up state for reading the table rows."""
        super().__init__(convert_charrefs=True)
        self.items = {}
        self.item_id = None
        self.item_name = None
        self.cell_index = 0
        self.global_percent_parts = []

    def handle_starttag(self, tag, attrs):
        """Read each item's name and completion rate from its table row."""
        attributes = dict(attrs)
        if tag == "tr" and "data-item-id" in attributes:
            self.item_id = int(attributes["data-item-id"])
            self.item_name = None
            self.cell_index = 0
            self.global_percent_parts = []
        elif tag == "td" and self.item_id is not None:
            self.cell_index += 1
        elif (
            tag == "a"
            and self.item_id is not None
            and self.cell_index == 1
            and self.item_name is None
        ):
            self.item_name = attributes.get("title")

    def handle_data(self, data):
        """Capture the text in the global completion column."""
        if self.item_id is not None and self.cell_index == 3:
            self.global_percent_parts.append(data)

    def handle_endtag(self, tag):
        """Save the item name and global completion rate when a row ends."""
        if tag == "tr" and self.item_id is not None:
            if self.item_name:
                global_percent = " ".join(" ".join(self.global_percent_parts).split())
                self.items[self.item_id] = {
                    "name": self.item_name,
                    "global_percent": global_percent or "N/A",
                }
            self.item_id = None
            self.item_name = None
            self.cell_index = 0
            self.global_percent_parts = []


class ItemTitleParser(HTMLParser):
    """Read the page title for one item ID lookup."""

    def __init__(self):
        """Set up state for reading the item page heading."""
        super().__init__(convert_charrefs=True)
        self.read_heading = False
        self.title_parts = []

    def handle_starttag(self, tag, attrs):
        """Start reading the main page heading."""
        if tag == "h1" and dict(attrs).get("id") == "firstHeading":
            self.read_heading = True

    def handle_data(self, data):
        """Keep text from the main page heading."""
        if self.read_heading:
            self.title_parts.append(data)

    def handle_endtag(self, tag):
        """Stop reading when the main page heading ends."""
        if tag == "h1":
            self.read_heading = False


def fetch_wiki_page(url, description):
    """Download one Wiki page and return its HTML text."""
    result = subprocess.run(
        [
            "curl",
            "--silent",
            "--show-error",
            "--location",
            "--write-out",
            "\n%{http_code}",
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
        raise RuntimeError(f"Could not download {description}: {detail}")

    try:
        html, status_text = result.stdout.rsplit("\n", 1)
        status = int(status_text)
    except (ValueError, IndexError) as error:
        raise RuntimeError(f"Could not download {description}: invalid HTTP response") from error
    if not 200 <= status < 300:
        raise RuntimeError(f"Could not download {description}: HTTP {status}")
    return html


def fetch_item_details():
    """Download the Wiki table and return item names and completion rates."""
    html = fetch_wiki_page(COLLECTION_LOG_URL, "the collection log item list")

    parser = CollectionLogParser()
    parser.feed(html)
    if not parser.items:
        raise RuntimeError("The Wiki response did not contain collection log items; the page may have changed.")
    return parser.items


def add_item_lookup_names(item_ids, item_map):
    """Resolve item IDs that are not listed as collection-log rows."""
    for item_id in sorted(set(item_ids) - item_map.keys()):
        html = fetch_wiki_page(
            ITEM_LOOKUP_URL.format(item_id),
            f"the Wiki page for item ID {item_id}",
        )
        parser = ItemTitleParser()
        parser.feed(html)
        title = " ".join(" ".join(parser.title_parts).split())
        if title:
            item_map[item_id] = {"name": title, "global_percent": "N/A"}


def render_comparison_table(players, player_data, item_map):
    """Render held items for all players, ordered by global completion rate."""
    player_item_ids = [set(data["collection_log"]) for data in player_data]
    item_ids = set().union(*player_item_ids)

    def details(item_id):
        return item_map.get(
            item_id,
            {"name": f"Unknown item ID {item_id}", "global_percent": "N/A"},
        )

    def sort_key(item_id):
        percentage = "".join(details(item_id)["global_percent"].split()).rstrip("%")
        try:
            return (0, -float(percentage), details(item_id)["name"].casefold())
        except ValueError:
            return (1, 0, details(item_id)["name"].casefold())

    def cell(value):
        """Keep item names valid inside Markdown table cells."""
        return str(value).replace("|", "\\|").replace("\n", "<br>")

    def display_width(value):
        """Count terminal columns, including wide symbols and player names."""
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

    rows = []
    for item_id in sorted(item_ids, key=sort_key):
        item = details(item_id)
        rows.append(
            [
                cell(item["name"]),
                *("✅" if item_id in ids else "❌" for ids in player_item_ids),
                cell(item["global_percent"]),
            ]
        )

    headings = ["Item Name", *players, "Global %"]
    heading_details = [
        "",
        *(f"({len(ids)} slots)" for ids in player_item_ids),
        "",
    ]
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
            pad(heading, widths[index]) for index, heading in enumerate(headings)
        )
        + " |",
        "| "
        + " | ".join(
            pad(detail, widths[index])
            for index, detail in enumerate(heading_details)
        )
        + " |",
        "|-" + "-|-".join("-" * width for width in widths) + "-|",
    ]
    for row in rows:
        rendered_row = " | ".join(
            pad(value, widths[index]) for index, value in enumerate(row)
        )
        lines.append("| " + rendered_row + " |")
    return "\n".join(lines)


def main():
    """Query and compare standard-profile collection logs for each account."""
    parser = argparse.ArgumentParser(description="Compare RuneScape collection logs.")
    parser.add_argument(
        "players",
        nargs="+",
        metavar="PLAYER",
        help="one or more RuneScape player names",
    )
    args = parser.parse_args()

    try:
        item_map = fetch_item_details()
        player_data = [
            query_player(player, "STANDARD") for player in args.players
        ]
        item_ids = [
            item_id
            for data in player_data
            for item_id in data["collection_log"]
        ]
        add_item_lookup_names(item_ids, item_map)
        print(
            render_comparison_table(
                args.players,
                player_data,
                item_map,
            )
        )
    except (RuntimeError, ValueError, subprocess.TimeoutExpired) as error:
        print(error, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
