---
name: llamatale-story-builder
description: Build and modify a LlamaTale story/world using the in-process MCP StoryManager tools. Use when creating or editing zones, locations, exits, catalogue items/creatures, spawning live world objects, setting story progression or the start location, or saving/loading a story. Covers the recommended build workflow, the {success, error} validation-feedback pattern, and the dict shapes for each object type.
---

# LlamaTale Story Builder

Build and modify a LlamaTale story/world through the in-process MCP
**StoryManager** tools. This skill gives you the mental model, the recommended
build workflow, how to read validation feedback, and the object dict shapes.
The individual tools are discoverable via `list_tools`; this skill is about
using them *well*, in the right order, and recovering from errors.

## The mental model

- **Zones contain locations.** A location is addressed as `(zone, name)`.
  Zones and locations are looked up **by name** — names are their identity and
  must be unique.
- The **catalogue** holds item/creature *templates* (plain dicts): `add_item`,
  `add_creature`. These are reusable blueprints, not live objects.
- The **world store** holds *live* objects (real `Living`/`Item`) prepared
  before play: `add_world_npc`, `add_world_item`. It does **not** place them in
  a location.
- **Spawning** copies a catalogue template into a live location: `spawn_npc`,
  `spawn_item`. This is how objects actually appear in the world.
- **Story progression** (`set_story_context`, `advance_story_section`) and the
  **start location** (`set_start_location`) shape the narrative and where the
  player begins.

## Recommended build workflow

Work top-down so each step has what it needs:

1. `get_config` / `set_config` — set `name`, `type`, `world_info`, `world_mood`.
2. `zone_example` → `add_zone` — create the start zone.
3. `location_example` → `add_location` — add locations to that zone.
4. `exit_example` → `set_exits` — bind exits between locations.
5. `add_item` / `add_creature` — populate the catalogue with templates.
6. `spawn_npc` / `spawn_item` — place live objects into locations.
7. `set_start_location` — where the player begins (`zone`, `name`).
8. `save` — persist the story.

Use the `*_example` tools (`zone_example`, `location_example`, `exit_example`)
to see the full field list for each object before you build one.

## Reading validation feedback

The four object-building tools — `add_zone`, `add_location`, `add_world_npc`,
`add_world_item` — return a named dict, **not** a bare bool:

```json
{"success": true,  "error": ""}
{"success": false, "error": "zone 'Forest' not found"}
```

On `success: false`, **read `error` and fix the input** — do not retry the same
input unchanged. Common errors and their fixes:

- `missing required field 'name' (a non-empty string) for <kind>` → add a
  non-empty `name`.
- `<kind> must be a dict` → pass a dict, not a string or number.
- `zone 'X' not found` → create the zone first, or correct the zone name.
- `<kind> 'X' already exists` → it's a duplicate; use a new name, or `remove_*`
  first.
- `failed to build <Kind>: ...` → a field has the wrong shape (e.g.
  `world_location` must be a 3-tuple `[x, y, z]`).

The catalogue `add_item`/`add_creature` and `spawn_*`/`set_exits` still return a
bare `bool`; a `false` there means "not added" (often a duplicate or unknown
reference) — check the relevant `list_*` tool to see why.

## Object dict shapes

Minimal working shapes (add optional fields as needed; the `*_example` tools and
tool docstrings list everything):

- **zone**: `{"name": "...", "description": "..."}`
- **location**: `{"name": "...", "descr": "..."}` — optional `short_descr`,
  `world_location` (`[x, y, z]`), `items`
- **exit**: `{"direction": "north", "name": "<target location>"}` — optional
  `short_descr`, `long_descr`
- **catalogue item**: `{"name": "...", "type": "..."}` — optional `short_descr`,
  `level`, `value`
- **catalogue creature**: `{"name": "...", "type": "Mob" | "Npc", "level": N}` —
  optional `race`, `gender`, `hp`, `aggressive`, `unarmed_attack`
- **world npc**: `{"name": "...", "type": "Mob" | "Npc", "race": "...",
  "gender": "m" | "f", "level": N}`
- **world item**: `{"name": "...", "type": "..."}` — optional `value`

## Gotchas

- `set_exits` **auto-creates missing target locations**, so exits are always
  bound — you can reference a location by name before it exists.
- The **world store** is for *preparing* a story before it is played; it does
  not insert into a location. Use `spawn_*` to place objects in a location.
- List tools (`list_zones`, `list_items`, `list_locations`, ...) return a single
  JSON array string, not one content item per element.
- **Snapshot before risky mutations**: `save(path)` first, then `load(path)` to
  roll back if a change goes wrong.
- Keep names unique and stable — they are how everything is addressed.

## LLM-backed generation (optional)

`generate_world_items`, `generate_world_creatures`, `generate_start_zone`, and
`generate_location` produce content via the LLM and apply it to the story. Use
them to bootstrap a world quickly, then refine the result with the manual tools
above.
