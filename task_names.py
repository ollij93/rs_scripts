"""Load local task ID-to-name catalogs used by comparison scripts."""

import json
from pathlib import Path


TASK_NAME_CATALOGS = {
    # These local maps keep terminal output independent of Wiki availability.
    "combat_achievements": Path(__file__).with_name("combat_achievement_names.json"),
    "sea_charting": Path(__file__).with_name("sea_charting_names.json"),
}
# Combat IDs follow osrs-tools. Sea IDs match the Wiki data-seachartid values.


def load_task_name_catalog(catalog_name):
    """Load a bundled ID-to-name catalog for a supported task type."""
    try:
        catalog_path = TASK_NAME_CATALOGS[catalog_name]
    except KeyError as error:
        raise ValueError(f"Unknown task name catalog: {catalog_name}") from error
    with catalog_path.open(encoding="utf-8") as names_file:
        raw_names = json.load(names_file)
    if not isinstance(raw_names, dict):
        raise RuntimeError(
            f"The {catalog_name.replace('_', ' ')} name catalog is invalid."
        )

    names = {}
    for raw_id, task_name in raw_names.items():
        if not isinstance(task_name, str):
            raise RuntimeError(
                f"The {catalog_name.replace('_', ' ')} name catalog is invalid."
            )
        try:
            task_id = int(raw_id)
        except (TypeError, ValueError) as error:
            raise RuntimeError(
                f"The {catalog_name.replace('_', ' ')} name catalog is invalid."
            ) from error
        names[task_id] = task_name
    return names


def get_task_name(task_id, task_names):
    """Return a catalog name or a clear label for an unmapped task ID."""
    return task_names.get(task_id, f"Unknown task ID {task_id}")
