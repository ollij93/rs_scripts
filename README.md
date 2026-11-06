# RuneScape queries and comparisons

This repository contains Python scripts to query RuneLite Sync player data and compare values in the responses. The scripts use `curl` for network requests and Python 3 for parsing and comparison.

## Shared modules

`query.py` downloads and decodes one player response. Run it on its own to print the JSON:

```sh
python3 query.py PLAYER ACTIVITY
```

`compare.py` queries two players, then compares one response field. Use dot notation for nested fields. For list fields, it prints values that appear in one player's list and not the other's.

```sh
python3 compare.py PLAYER_A PLAYER_B --activity ACTIVITY --field FIELD
```

Both modules provide functions for the player scripts to import. The player scripts pass response dictionaries from `query.py` to `compare.py`. They do not write player JSON files.

## Main-game collection log

Compare collection-log item IDs for standard-profile players:

```sh
python3 collection_log.py PLAYER_A PLAYER_B [PLAYER_C ...]
```

The script queries the `STANDARD` profile for every account name and compares the `collection_log` field. The API returns item IDs. The script reads item names and global completion rates from the Wiki collection log table, then prints a table for items held by any player. The heading shows each player's slot count. IDs that do not appear in the table are looked up on the Wiki and show `N/A` for the global rate. Every account needs collection-log data in WikiSync.

## Skill levels and XP

Compare skill levels and XP for any number of players:

```sh
python3 skill_comparison.py PLAYER_A PLAYER_B [PLAYER_C ...]
```

The script reads level and XP data from the Old School RuneScape hiscores. It prints one row for each skill. In a terminal, green marks the highest level or XP across the accounts for that skill, and red marks the lowest. It does not colour values when all accounts have the same value.

Compare XP differences for exactly two players:

```sh
python3 skill_xp_difference.py PLAYER_A PLAYER_B
```

The difference is `PLAYER_B XP - PLAYER_A XP`. The script prints signed values and sorts from the lowest difference to the highest. A negative value means PLAYER_A has more XP. A positive value means PLAYER_B has more XP. In a terminal, the higher XP value for each skill is green and the lower is red. Ties are uncoloured.

## Other account comparisons

These scripts accept one or more player names unless the command says otherwise.

Compare quest completion states:

```sh
python3 quest_comparison.py PLAYER_A PLAYER_B [PLAYER_C ...]
```

The table uses ✅ for completed quests, ⏳ for quests in progress, and ❌ for quests that have not started. In a terminal, completed and incomplete cells use green and red when players differ. In-progress and not-started quests both count as incomplete for this color comparison.

Compare boss and raid kill counts:

```sh
python3 boss_kill_comparison.py PLAYER_A PLAYER_B [PLAYER_C ...]
```

In a terminal, green marks the highest available kill count and red marks the lowest for each boss or raid. Ties are uncoloured.

Compare clue counts and other Hiscores activities:

```sh
python3 activity_comparison.py PLAYER_A PLAYER_B [PLAYER_C ...]
```

These scripts read named activities and scores from the official Hiscores. An unavailable score appears as `N/A`; it does not mean zero.

In a terminal, green marks the highest available score and red marks the lowest for each activity. Ties are uncoloured.

Compare achievement diary progress by region and tier:

```sh
python3 achievement_diary_comparison.py PLAYER_A PLAYER_B [PLAYER_C ...]
```

In a terminal, green marks the highest completed task count and red marks the lowest for each region and tier. Ties and `N/A` values are uncoloured.

Compare completed combat achievements:

```sh
python3 combat_achievement_comparison.py PLAYER_A PLAYER_B [PLAYER_C ...]
```

Compare unlocked music tracks:

```sh
python3 music_track_comparison.py PLAYER_A PLAYER_B [PLAYER_C ...]
```

Compare sea charting progress:

```sh
python3 sea_charting_comparison.py PLAYER_A PLAYER_B [PLAYER_C ...]
```

The WikiSync response provides numeric IDs for combat achievements and sea charting. Both scripts use bundled ID-to-name catalogs, so name lookup does not depend on a live Wiki request. The combat achievement catalog comes from [osrs-tools](https://github.com/jamescer/osrs-tools/tree/master/src/runescape/model/combat-achievements/tasks). The sea charting catalog comes from the [OSRS Wiki sea charting task table](https://oldschool.runescape.wiki/w/Sea_charting).

## Requirements

Python 3, `curl`, and network access are required. The collection-log script needs the Wiki collection log table.
