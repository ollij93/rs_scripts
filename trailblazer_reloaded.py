#!/usr/bin/env python3
"""Compare Trailblazer Reloaded task completions for two players."""

import argparse
from html.parser import HTMLParser
import subprocess
import sys

from compare import compare_values
from query import USER_AGENT, query_player


TASKS_URL = "https://oldschool.runescape.wiki/w/Trailblazer_Reloaded_League/Tasks"


class TaskTableParser(HTMLParser):
    """Read task IDs and names from task table rows."""

    def __init__(self):
        """Set up state for reading one task row at a time."""
        super().__init__(convert_charrefs=True)
        self.tasks = {}
        self.task_id = None
        self.cell_index = 0
        self.task_name_parts = []

    def handle_starttag(self, tag, attrs):
        """Track a task row and its name cell."""
        attributes = dict(attrs)
        if tag == "tr" and "data-taskid" in attributes:
            self.task_id = int(attributes["data-taskid"])
            self.cell_index = 0
            self.task_name_parts = []
        elif tag == "td" and self.task_id is not None:
            self.cell_index += 1

    def handle_data(self, data):
        """Keep text from the task name cell."""
        if self.task_id is not None and self.cell_index == 2:
            self.task_name_parts.append(data)

    def handle_endtag(self, tag):
        """Save the task name when its row ends."""
        if tag == "tr" and self.task_id is not None:
            task_name = " ".join(" ".join(self.task_name_parts).split())
            if task_name:
                self.tasks[self.task_id] = task_name
            self.task_id = None


def fetch_task_names():
    """Download the Wiki task table and return its task ID map."""
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
            TASKS_URL,
        ],
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    if result.returncode != 0:
        detail = result.stderr.strip() or f"curl exited with status {result.returncode}"
        raise RuntimeError(f"Could not download the Trailblazer task list: {detail}")

    try:
        html, status_text = result.stdout.rsplit("\n", 1)
        status = int(status_text)
    except (ValueError, IndexError) as error:
        raise RuntimeError("Could not download the Trailblazer task list: invalid HTTP response") from error
    if not 200 <= status < 300:
        raise RuntimeError(f"Could not download the Trailblazer task list: HTTP {status}")

    parser = TaskTableParser()
    parser.feed(html)
    if not parser.tasks:
        raise RuntimeError("The Wiki response did not contain task rows; the page may have changed.")
    return parser.tasks


def task_names(player_data, task_map):
    """Map a player's task IDs to readable task names."""
    names = []
    for task_id in player_data["league_tasks"]:
        try:
            names.append(task_map[task_id])
        except KeyError as error:
            raise ValueError(f"The Wiki task list does not contain task ID {task_id}") from error
    return names


def main():
    """Query and compare Trailblazer tasks for two players."""
    parser = argparse.ArgumentParser(description="Compare Trailblazer Reloaded tasks for two players.")
    parser.add_argument("player_a", help="first RuneScape player name")
    parser.add_argument("player_b", help="second RuneScape player name")
    args = parser.parse_args()

    try:
        task_map = fetch_task_names()
        data_a = query_player(args.player_a, "TRAILBLAZER_RELOADED_LEAGUE")
        data_b = query_player(args.player_b, "TRAILBLAZER_RELOADED_LEAGUE")
        names_a = task_names(data_a, task_map)
        names_b = task_names(data_b, task_map)
        print(compare_values(args.player_a, args.player_b, names_a, names_b, label="Tasks"))
    except (RuntimeError, ValueError, subprocess.TimeoutExpired) as error:
        print(error, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
