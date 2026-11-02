LlamaTale is a continuation of the archived IF/MUD framework Tale, written mostly in Python, with various frontends.

It uses an LLM backend to describe locations and npcs vivid way. LLM's are also used to generate various types of content.

Most gen-ai related files are in the tale/llm folder.

Prefer the usage of dedicated tools, like edit, grep and glob over shell commands, where possible.

Python version and command is: python3.10

---

# Core Architecture

## Object Hierarchy

```
MudObject (abstract base)
  |
  +-- Location (contains livings + items, has exits)
  |     |
  |     +-- Exit (connection to another Location)
  |           |
  |           +-- Door
  |
  +-- Item (physical objects)
  |     |
  |     +-- Weapon
  |     +-- Armour
  |     +-- Wearable
  |     +-- Container
  |     +-- Key
  |
  +-- Living (entities with AI/behavior)
        |
        +-- Player (controlled by human)
        +-- NPC (AI-controlled)
              |
              +-- Shopkeeper
```

Every object that can hold other objects does so in its \"inventory\" (a set).
You can't access it directly, `object.inventory` returns a frozenset copy of it.
Except Location: it separates the items and livings it contains internally.
Use its `enter`/`leave` methods instead.

## Key Files

### tale/base.py
Core mudlib objects. Defines the entire object hierarchy above.
- `MudObject`: Abstract base for all objects. Handles naming, descriptions, registration.
- `Location`: Contains `livings` and `items` sets, plus `exits` dict. Manages look/look descriptions.
- `Item`: Physical objects that can be moved, carried, or contained.
- `Living`: Entities with stats, inventory, soul (for social interaction), and tick behavior.
- `Stats`: Character statistics (hp, ac, wc, attributes, skills).
- `Soul`: Social identity for Living entities.
- `MudObjRegistry`: Tracks all objects by vnum (virtual number).

### tale/driver.py
Base driver class. Common functionality for both IF and MUD modes.
- `Commands`: Manages registered commands (verbs), privilege system, command validation.
- `Driver`: Core game loop, player management, command parsing, tick system.
- Command registration uses decorators. Commands are mapped to verb names.
- Privilege system allows different command access levels.

### tale/driver_if.py
Single-user Interactive Fiction driver.
- `IFDriver`: One player, one story instance.
- Handles save/load game functionality.
- Supports console, GUI, and web IO types.
- Character loading from JSON/image files.

### tale/driver_mud.py
Multi-user MUD server driver.
- `MudDriver`: Multiple concurrent players.
- FastAPI web server for WebSocket connections.
- Account system with `MudAccounts`.
- Message-of-the-Day (MOTD) support.
- Restricted mode for new player control.

### tale/player.py
Player-specific code.
- `Player`: Extends `Living` with player-specific features.
- `PlayerConnection`: Manages IO, input/output queues, screen settings.
- Input handling via queue-based system.
- Output formatting, screen width/indent management.
- Tell system for messaging.

## Game Modes

### IF Mode (`GameMode.IF`)
- Single player, linear story experience.
- Savegames enabled by default.
- Multiple IO backends (console, GUI, web).
- Character loading from external files.

### MUD Mode (`GameMode.MUD`)
- Multi-player, persistent world.
- Web-based WebSocket connections.
- Account management and privileges.
- No savegame support (persistent world).


Commands are registered as functions decorated with tale command decorators.
They map to verb names in `verbdefs.VERBS`.

Privilege levels:
- Empty string: available to all players
- Other values: restricted privileges (e.g., "wizard")

Command attributes:
- `disabled_in_mode`: disable in specific game modes
- `overrides_soul`: override soul parsing
- `no_soul_parse`: skip soul verb parsing

---

# Story System

LlamaTale uses a story configuration system to define the setting, world, and narrative structure.

## Key Files

### tale/story.py
Story configuration and base classes.
- `StoryConfig`: Serializable configuration settings for a story. Contains all world-building parameters:
  - `name`, `author`, `version`: Story metadata
  - `supported_modes`: Set of `GameMode` values (IF/MUD)
  - `player_name`, `player_gender`, `player_race`: Default player settings
  - `money_type`: `MoneyType` enum (FANTASY/MODERN/NOTHING)
  - `server_tick_method`: `TickMethod` enum (COMMAND/TIMER)
  - `startlocation_player`, `startlocation_wizard`: Starting locations
  - `savegames_enabled`: Whether savegames are allowed
  - `context`, `type`, `world_info`, `world_mood`: LLM context parameters
  - `day_night`, `random_events`: World simulation features
  - `available_games`: List of sub-games
- `StoryBase`: Base class for your story implementation. Override these methods:
  - `init(driver)`: Called after driver initialization
  - `create_account_dialog()`: Custom character creation dialog
  - `init_player(player)`: Initialize player after login
  - `welcome(player)`, `goodbye(player)`: Player messages
  - `story_success(player)`, `story_failure(player)`: End-game messages
- `GameMode`: Enum (IF, MUD)
- `TickMethod`: Enum (COMMAND, TIMER)
- `MoneyType`: Enum (FANTASY, MODERN, NOTHING)

### tale/story_context.py
Story progression and narrative structure.
- `StoryContext`: Manages story sections and progress.
  - `base_story`: Base plot description
  - `current_section`: Active story section
  - `past_sections`: List of completed sections
  - `progress`: Float tracking advancement (0.0 to length)
  - `increase_progress()`: Periodically called method to advance story
  - `to_context()`, `to_context_with_past()`: Generate LLM context strings
  - `from_json()`, `to_json()`: Serialization for save games
  - Decorated with `@call_periodically(10, 20)` for automatic progress updates

## Story Configuration

Stories are defined by extending `StoryBase` and setting `StoryConfig`:

```python
from tale.story import StoryBase, StoryConfig, GameMode

class MyStory(StoryBase):
    config = StoryConfig()
    config.name = "My Adventure"
    config.author = "Author Name"
    config.supported_modes = {GameMode.IF}
    config.type = "A fantasy adventure"
    config.world_info = "A world of magic and danger"
    config.world_mood = 3  # 5 = happy, -5 = nightmare
```

## Story Progression

Stories can have sections that progress over time:
- `StoryContext` tracks which section is active
- Progress advances automatically (COMMAND or TIMER tick method)
- When progress crosses integer thresholds, LLM advances to next section
- Past sections are preserved for context

## Example

See `stories/test_story` for a complete example story implementation.
