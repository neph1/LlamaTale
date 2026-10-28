# Proposal: Modern LLM Interface for LlamaTale

## Problem Statement

LlamaTale currently uses JSON as its interface with the LLM, enforced via GBNF grammar
constrained generation (`JSON_GRAMMAR.txt`). This has two known problems:

1. **Grammar is not semantics.** Even when the grammar is followed perfectly, the LLM can
   produce syntactically valid JSON that is semantically wrong: wrong action types, targets
   that don't exist, fields with wrong types, or nonsensical content that happens to parse.
2. **Fragile parsing.** LLMs format JSON in many different ways — markdown fences
   (` ```json ... ``` `), reasoning sections (`<think>...</think>`), double-encoded JSON,
   trailing commas, Python literals (`None`, `True`, `False`), extra prose before/after
   the JSON block. The `json_util.py` sanitization pipeline (194 lines) exists to handle
   all these cases, and it's a constant source of bugs.

This was a reasonable approach when models were less capable. Modern models and backends
have moved on.

## Current Architecture (Summary)

```
LlmUtil (llm_utils.py)
  ├── StoryBuilding    → free-text generation (story background, advance plot)
  ├── WorldBuilding    → JSON generation (locations, zones, items, creatures, dungeons)
  ├── CharacterBuilding → JSON generation (characters, dialogue, actions, follow)
  └── QuestBuilding    → JSON generation (quests)
        ↓
    IoUtil (llm_io.py) → IoAdapter (kobold_cpp / llama_cpp / openai)
        ↓
    HTTP POST to backend
```

JSON-requiring call sites (all use `json_grammar` + `json_util.safe_load()`):

| Call site | File | Output shape |
|---|---|---|
| `build_location` | `world_building.py:52` | `{name, description, exits[], items[], npcs[], indoors}` |
| `generate_start_location` | `world_building.py:202` | `{name, exits[], items[], npcs[]}` |
| `generate_start_zone` | `world_building.py:222` | `{name, description, races[], items[], mood, level}` |
| `_generate_zone` | `world_building.py:139` | `{name, description, races[], items[], mood, level, size}` |
| `_generate_dungeon_config` | `world_building.py:162` | `{name, description, races[], items[], max_depth}` |
| `generate_world_items` | `world_building.py:247` | `{item: {name, type, short_descr, level, value}}` |
| `generate_world_creatures` | `world_building.py:283` | `{creature: {name, body, mass, hp, type, level, ...}}` |
| `generate_random_spawn` | `world_building.py:318` | `{items[], npcs[], mobs[]}` |
| `generate_dungeon_locations` | `world_building.py:367` | `[{index, name, description}, ...]` |
| `generate_dungeon_entrance` | `world_building.py:386` | `{direction, name, short_descr, long_descr}` |
| `generate_dialogue` | `character.py:38` | `{response, sentiment, give}` |
| `generate_character` | `character.py:76` | `{name, description, appearance, personality, money, level, gender, age, race, occupation}` |
| `free_form_action` | `character.py:157` | `[{goal, thoughts, action, target, text}, ...]` or single dict |
| `request_follow` | `character.py:190` | `{response, reason}` |
| `generate_note_quest` | `quest_building.py:33` | `{reason, type, target, location, name}` |

Free-text call sites (no JSON, no grammar):

| Call site | File | Purpose |
|---|---|---|
| `evoke` | `llm_utils.py:77` | Rewrite player input in story voice |
| `generate_story_background` | `story_building.py:15` | Story background prose |
| `advance_story_section` | `story_building.py:24` | Advance plot outline |
| `perform_idle_action` | `character.py:94` | NPC idle action description |
| `perform_travel_action` | `character.py:119` | NPC travel decision |
| `perform_reaction` | `character.py:132` | NPC reaction to events |
| `generate_quest` | `quest_building.py:20` | Quest reason text |
| `generate_note_lore` | `world_building.py:353` | Lore note text |
| `describe_day_cycle_transition` | `llm_utils.py:289` | Day/night transition text |
| `generate_narrative_event` | `llm_utils.py:302` | Narrative event text |

The response objects (`ActionResponse`, `FollowResponse`, `LocationResponse`,
`WorldItemsResponse`, `WorldCreaturesResponse`, `LocationDescriptionResponse`) all
consume parsed dicts and add validation/sanitization on top.

## Proposed Approach: Schema-Driven Structured Output + Typed Response Models

### Core idea

Replace the generic JSON grammar + text-parsing pipeline with **JSON Schema-driven
structured output** at the backend level, combined with **Pydantic models** on the
client side for validation. This gives us:

1. **Backend-enforced schema conformance** — modern llama.cpp, KoboldCpp, and OpenAI-
   compatible servers all support `response_format: {type: "json_schema", json_schema: {...}}`
   which constrains generation to produce valid JSON matching the schema. This is
   strictly better than a generic "valid JSON" grammar because the schema also
   constrains field names, types, and required fields.

2. **Type-safe client models** — Pydantic models replace the hand-rolled sanitization
   in `json_util.py` and the `Response` classes. Validation errors become structured
   exceptions with clear messages, not silent fallbacks.

3. **Graceful degradation** — when the backend doesn't support structured output,
   fall back to prompt-based JSON with the existing `json_util.safe_load()` pipeline
   as a safety net (not the primary path).

### Architecture

```
LlmUtil (llm_utils.py) — unchanged public API
  ├── StoryBuilding    → free-text (unchanged)
  ├── WorldBuilding    → structured output via Pydantic models
  ├── CharacterBuilding → structured output via Pydantic models
  └── QuestBuilding    → structured output via Pydantic models
        ↓
    IoUtil (llm_io.py) — extended with structured output support
        ↓
    IoAdapter (kobold_cpp / llama_cpp / openai)
        ↓
    HTTP POST with response_format: {type: "json_schema", json_schema: {...}}
        ↓
    Pydantic model validation on the response
```

### New components

#### 1. `tale/llm/schemas.py` — Pydantic models for all structured outputs

Each model defines the expected shape and generates its own JSON Schema:

```python
from pydantic import BaseModel, Field
from typing import List, Optional, Literal

class ExitSchema(BaseModel):
    direction: str
    name: str
    short_descr: str = ""

class ItemSchema(BaseModel):
    name: str
    type: Literal["Weapon", "Wearable", "Health", "Money", "Trash", "Other"] = "Other"
    short_descr: str = ""
    level: int = 1
    value: int = 0

class NpcSchema(BaseModel):
    name: str
    sentiment: str = ""
    race: str = ""
    gender: Literal["m", "f", "n"] = "n"
    level: int = 1
    aggressive: bool = False
    description: str = ""
    occupation: str = ""
    appearance: str = ""

class LocationSchema(BaseModel):
    name: str
    description: str = ""
    exits: List[ExitSchema] = []
    items: List[ItemSchema] = []
    npcs: List[NpcSchema] = []
    indoors: bool = False

class DialogueSchema(BaseModel):
    response: str
    sentiment: str = ""
    give: Optional[str] = None

class ActionSchema(BaseModel):
    goal: str = ""
    thoughts: str = ""
    action: str
    target: str = ""
    text: str = ""

class FollowSchema(BaseModel):
    response: str  # "yes" or "no"
    reason: str = ""

class CharacterSchema(BaseModel):
    name: str
    description: str = ""
    appearance: str = ""
    personality: str = ""
    money: int = 0
    level: int = 1
    gender: Literal["m", "f", "n"] = "n"
    age: int = 0
    race: str = ""
    occupation: str = ""

class ZoneSchema(BaseModel):
    name: str
    description: str = ""
    races: List[str] = []
    items: List[str] = []
    mood: int = 0
    level: int = 1

class WorldItemSchema(BaseModel):
    item: ItemSchema

class WorldCreatureSchema(BaseModel):
    creature: NpcSchema

class SpawnSchema(BaseModel):
    items: List[ItemSchema] = []
    npcs: List[NpcSchema] = []
    mobs: List[str] = []

class DungeonLocationSchema(BaseModel):
    index: int
    name: str
    description: str = ""

class DungeonEntranceSchema(BaseModel):
    direction: str
    name: str
    short_descr: str = ""
    long_descr: str = ""

class NoteQuestSchema(BaseModel):
    reason: str
    type: Literal["talk", "find", "kill", "escort"] = "talk"
    target: str = ""
    location: str = ""
    name: str = ""
```

#### 2. `IoUtil` extensions

Add a `structured_request()` method that:

1. Accepts a Pydantic model class as the expected output type.
2. Generates the JSON Schema from the model: `Model.model_json_schema()`.
3. Sends the request with `response_format: {type: "json_schema", json_schema: {name: ..., schema: ..., strict: true}}`.
4. Parses the response text as JSON (should always succeed with structured output).
5. Validates with `Model.model_validate_json(response_text)`.
6. Returns the validated model instance.

For backends that don't support `json_schema` response format:

- **KoboldCpp**: supports `grammar` field with GBNF, and newer versions (v1.90.2+)
  also accept JSON Schema in the `grammar` field or via `response_format`.
- **llama.cpp server**: supports `response_format: {type: "json_schema", json_schema: {...}}`
  on `/v1/chat/completions` (converts to GBNF internally), and `grammar` on `/completion`.
- **OpenAI**: supports `response_format: {type: "json_schema", json_schema: {...}}`
  natively (requires `strict: true`).
- **Fallback**: if the backend returns an error or doesn't support the field, retry
  without structured output and use `json_util.safe_load()` + `Model.model_validate()`.

#### 3. Response class migration

The existing `Response` classes (`ActionResponse`, `FollowResponse`, etc.) become
thin adapters over the Pydantic models:

```python
# Before
class ActionResponse:
    def __init__(self, response: dict):
        response = self._sanitize_free_form_response(response)
        self.goal = response.get('goal', '')
        self.text = response.get('text', '')
        # ... 30 lines of sanitization

# After
class ActionResponse:
    def __init__(self, model: ActionSchema):
        self.goal = model.goal
        self.text = model.text
        self.target = model.target
        self.item = ""  # not in schema, kept for compat
        self.action = model.action
        self.sentiment = ""
        self.thoughts = model.thoughts
```

Or better: return the Pydantic model directly and update call sites.

#### 4. Backend config changes

Each `backend_*.yaml` gets a new field:

```yaml
# backend_llama_cpp.yaml
STRUCTURED_OUTPUT_KEY: "response_format"  # or "grammar" for older versions
STRUCTURED_OUTPUT_TYPE: "json_schema"     # or "gbnf" for grammar-based
SUPPORTS_STRUCTURED_OUTPUT: true
```

### Migration path

**Phase 1: Add infrastructure (no behavior change)**

- Add `tale/llm/schemas.py` with Pydantic models for all structured outputs.
- Add `structured_request()` to `IoUtil` alongside existing `synchronous_request()`.
- Add `SUPPORTS_STRUCTURED_OUTPUT` to backend configs.
- Add tests with mocked backends.

**Phase 2: Migrate JSON call sites one by one**

Start with the simplest, highest-value ones:

1. `request_follow` → `FollowSchema` (simple: 2 fields)
2. `generate_dialogue` → `DialogueSchema` (simple: 3 fields)
3. `free_form_action` → `ActionSchema` (medium: 5 fields)
4. `generate_character` → `CharacterSchema` (medium: 10 fields)
5. `build_location` / `generate_start_location` → `LocationSchema` (complex: nested)
6. Remaining world building call sites

Each migration:
- Replace `json_util.safe_load(text)` with `Model.model_validate_json(text)`.
- Replace `request_body['grammar'] = self.json_grammar` with structured output config.
- Update the `Response` class or return the model directly.
- Update tests.

**Phase 3: Clean up**

- Remove `JSON_GRAMMAR.txt` and grammar injection from all call sites.
- Reduce `json_util.py` to just the fallback path (or remove entirely if all backends
  support structured output).
- Remove `json_grammar` / `json_grammar_key` parameters from `WorldBuilding`,
  `CharacterBuilding`, `QuestBuilding` constructors.

### What stays the same

- `LlmUtil` public API — all method signatures unchanged.
- `IoUtil.synchronous_request()` — still available for free-text calls.
- Context classes (`ActionContext`, `DialogueContext`, etc.) — unchanged.
- Prompt templates — mostly unchanged, but `PRE_JSON_PROMPT.txt` and JSON template
  instructions can be simplified or removed (the schema replaces them).
- Backend abstraction (`IoAdapter`) — extended, not replaced.
- Free-text generation — completely unchanged.

### Benefits

1. **Guaranteed valid JSON** — backend constrains generation to schema-valid JSON.
   No more markdown fences, reasoning sections, or double-encoded JSON.
2. **Type safety** — Pydantic validates types at parse time. `level: int` can't be
   `"high"`. `gender: Literal["m", "f", "n"]` can't be `"male"`.
3. **Better error messages** — Pydantic validation errors say exactly what's wrong
   and where, instead of `json.JSONDecodeError: Expecting ',' delimiter: line 3 column 15`.
4. **Simpler prompts** — no need to include JSON templates in prompts. The schema is
   sent separately. Prompts become shorter and more focused on content, not format.
5. **Less code** — `json_util.py` (194 lines), the `_sanitize_*` methods in response
   classes, and the grammar injection boilerplate all go away.
6. **Future-proof** — JSON Schema is the industry standard. New backends (vLLM,
   SGLang, Ollama, etc.) all support it.

### Risks and mitigations

| Risk | Mitigation |
|---|---|
| Backend doesn't support `json_schema` response format | Fall back to `json_object` mode, then to prompt-based JSON + `safe_load()` |
| Schema too complex for GBNF conversion | Keep schemas simple (flat, no deep nesting). Split complex outputs into multiple requests (already done for world items/creatures) |
| Pydantic adds a dependency | Already in the environment (v2.14.0). Add to `requirements.txt` |
| Performance: schema validation overhead | Negligible compared to LLM inference time |
| Model ignores schema semantics (right shape, wrong content) | This is inherent to LLMs. The existing validation in `LocationResponse._validate_location` etc. stays as a second layer |

### Alternative considered: Tool/Function Calling

OpenAI-style tool calling (`tools: [{type: "function", function: {name, parameters}}]`)
is another modern approach. The LLM "calls" a function with structured arguments
instead of returning JSON text. llama.cpp server now supports this.

**Why not tool calling for LlamaTale?**

- Tool calling is designed for **agentic** workflows where the LLM decides which tool
  to call. LlamaTale's use case is **structured data generation** — we always know
  what shape we want.
- Tool calling adds a layer of indirection (parse tool call → extract arguments →
  validate) without adding value for our use case.
- `response_format: json_schema` is simpler and more directly maps to "give me data
  in this shape."
- However, tool calling could be useful for a future "LLM as agent" feature where
  the model decides which game actions to take.

### Alternative considered: TOON / YAML / custom formats

Newer formats like [TOON](https://github.com/toon-format/toon) (Token-Oriented Object
Notation) are more token-efficient than JSON. However:

- Backend support is limited (mostly prompt-based, not constrained generation).
- JSON Schema constrains JSON specifically; TOON would need a different constraint
  mechanism.
- The token savings are modest for our use case (small structured outputs).
- Not worth the complexity for now. Revisit if token efficiency becomes a bottleneck.

## Dependency changes

Add to `requirements.txt`:
```
pydantic>=2.0
```

## Files to create

- `tale/llm/schemas.py` — Pydantic models for all structured outputs

## Files to modify

- `tale/llm/llm_io.py` — add `structured_request()` method
- `tale/llm/io_adapters.py` — add structured output support to adapters
- `tale/llm/world_building.py` — migrate JSON call sites
- `tale/llm/character.py` — migrate JSON call sites
- `tale/llm/quest_building.py` — migrate JSON call sites
- `tale/llm/responses/*.py` — simplify to use Pydantic models
- `backend_*.yaml` — add structured output config fields
- `requirements.txt` — add pydantic

## Files to eventually remove/simplify

- `tale/llm/prompt_templates/JSON_GRAMMAR.txt` — no longer needed
- `tale/json_util.py` — reduce to fallback-only or remove
- `tale/llm/prompt_templates/PRE_JSON_PROMPT.txt` — no longer needed
- JSON template files (`ACTION_TEMPLATE.txt`, `DIALOGUE_TEMPLATE.txt`, etc.) —
  replaced by schemas, but may keep as prompt hints during transition

## Open questions

1. **Should we keep the JSON template prompt fragments during transition?** They don't
   hurt (the schema constrains the output anyway), and removing them is a separate
   prompt-tuning effort. Recommend keeping them initially, removing in Phase 3.

2. **Should `LlmUtil` return Pydantic models or the existing Response classes?**
   Returning models directly is cleaner but changes the API. Wrapping in Response
   classes preserves backward compatibility. Recommend wrapping initially.

3. **How to handle the `ActionResponse._sanitize_free_form_response` logic?** Some
   of that sanitization handles cases where the LLM returns `target` as a dict or
   list instead of a string. With schema constraints, these cases shouldn't occur.
   But as defense-in-depth, we might keep a thin validation layer.

4. **KoboldCpp compatibility**: KoboldCpp's chat completions endpoint (`/v1/chat/completions`)
   supports `response_format` with JSON Schema since v1.90.2. The legacy
   `/api/v1/generate` endpoint only supports `grammar` (GBNF). Should we migrate
   KoboldCpp to use the chat completions endpoint, or keep using `/api/v1/generate`
   with GBNF derived from JSON Schema?
