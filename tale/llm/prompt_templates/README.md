# LLM Prompt Templates

This directory contains individual prompt template files used by the LlamaTale LLM system.

## Structure

Each `.txt` file in this directory corresponds to a prompt template key that was previously stored in `llm_config.yaml`. The filename (without the `.txt` extension) becomes the key in the `llm_config.params` dictionary.

For example:
- `PRE_PROMPT.txt` → `llm_config.params['PRE_PROMPT']`
- `DIALOGUE_PROMPT.txt` → `llm_config.params['DIALOGUE_PROMPT']`
- `CREATE_CHARACTER_PROMPT.txt` → `llm_config.params['CREATE_CHARACTER_PROMPT']`

## Editing Prompts

To edit a prompt:
1. Open the corresponding `.txt` file in your text editor
2. Make your changes
3. Save the file
4. The changes will be loaded automatically the next time the application starts

## Prompt Categories

The prompts are organized into several categories:

### System Prompts
- `PRE_PROMPT.txt` - Base system prompt for the LLM
- `PRE_JSON_PROMPT.txt` - System prompt for JSON-formatted responses
- `BASE_PROMPT.txt` - Base prompt template for general tasks

### Character & NPC Prompts
- `CREATE_CHARACTER_PROMPT.txt` - Prompt for creating new characters
- `DIALOGUE_PROMPT.txt` - Prompt for NPC dialogue
- `REACTION_PROMPT.txt` - Prompt for character reactions
- `REQUEST_FOLLOW_PROMPT.txt` - Prompt for follow requests

### Action Prompts
- `ACTION_PROMPT.txt` - Prompt for character actions
- `IDLE_ACTION_PROMPT.txt` - Prompt for idle character behavior
- `COMBAT_PROMPT.txt` - Prompt for combat descriptions

### World Building Prompts
- `CREATE_LOCATION_PROMPT.txt` - Prompt for creating locations
- `CREATE_ZONE_PROMPT.txt` - Prompt for creating zones
- `CREATE_DUNGEON_LOCATIONS.txt` - Prompt for dungeon generation
- `START_LOCATION_PROMPT.txt` - Prompt for starting location

### Story Prompts
- `STORY_BACKGROUND_PROMPT.txt` - Prompt for story background
- `STORY_PLOT_PROMPT.txt` - Prompt for plot generation
- `ADVANCE_STORY_PROMPT.txt` - Prompt for advancing the story

### Event Prompts
- `DAY_CYCLE_EVENT_PROMPT.txt` - Prompt for day/night transitions
- `NARRATIVE_EVENT_PROMPT.txt` - Prompt for narrative events
- `PLAYER_ENTER_PROMPT.txt` - Prompt for player entering locations

### Quest Prompts
- `QUEST_PROMPT.txt` - Prompt for quest generation
- `NOTE_QUEST_PROMPT.txt` - Prompt for note-based quests
- `NOTE_LORE_PROMPT.txt` - Prompt for lore notes

### Template Definitions (JSON Schemas)
These files define the JSON structure that the LLM should follow:
- `DIALOGUE_TEMPLATE.txt`
- `ACTION_TEMPLATE.txt`
- `ITEM_TEMPLATE.txt`
- `CREATURE_TEMPLATE.txt`
- `EXIT_TEMPLATE.txt`
- `NPC_TEMPLATE.txt`
- `LOCATION_TEMPLATE.txt`
- `ZONE_TEMPLATE.txt`
- `DUNGEON_LOCATION_TEMPLATE.txt`
- `CHARACTER_TEMPLATE.txt`
- `FOLLOW_TEMPLATE.txt`

### World Generation
- `WORLD_ITEMS.txt` - Prompt for generating multiple items
- `WORLD_ITEM_SINGLE.txt` - Prompt for generating a single item
- `WORLD_CREATURES.txt` - Prompt for generating multiple creatures
- `WORLD_CREATURE_SINGLE.txt` - Prompt for generating a single creature

### Other Prompts
- `TRAVEL_PROMPT.txt` - Prompt for character travel decisions
- `GOAL_PROMPT.txt` - Prompt for character goal generation
- `ITEMS_PROMPT.txt` - Prompt fragment for adding items
- `SPAWN_PROMPT.txt` - Prompt fragment for spawning NPCs/mobs
- `RANDOM_SPAWN_PROMPT.txt` - Prompt for random spawns
- `JSON_GRAMMAR.txt` - JSON grammar definition for constrained generation

## Notes

- Prompts use Python string formatting syntax with curly braces (e.g., `{context}`, `{character_name}`)
- JSON templates use double curly braces for literal braces (e.g., `{{"key": "value"}}`)
- Changes to these files require restarting the application to take effect
- Configuration values (like `WORD_LIMIT`, `BACKEND`, etc.) remain in the root `llm_config.yaml` file
