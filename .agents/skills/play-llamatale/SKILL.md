---
name: play-llamatale
description: Load this skill when the user wants to play a LlamaTale story (e.g. The Prancing Llama) interactively from the CLI. Covers how to launch the game as a background process, how to send commands and poll for output, the character-creation flow, and the basic commands to get going. The game itself is self-explanatory — explore it through its own output, and do not read the story's source files to find answers.
---

# Playing a LlamaTale story

## Launch

From the repo root:

```
python3.10 -m stories.prancingllama.story
```

This uses the real LLM backend configured in `llm_config.yaml` (mistral, key from
`MISTRAL_API_KEY`). For an offline run with canned responses, prefix with
`LLAMATALE_BACKEND=dummy`.

## Drive it as a background process

The console game reads commands from stdin and writes to stdout — it does not push
updates. So:

1. Start it with `tools.process.start` (keep the returned `processId`).
2. Send a command with `tools.process.write({ processId, text: "look\n" })`.
3. Poll for output with `tools.process.output({ processId, cursor, waitMs, maxBytes })`,
   advancing `cursor` to `nextCursor` each time. Poll every ~2–3 s; the game ticks on a
   timer, so NPCs may act between your commands and show up in later polls.
4. Keep each polling batch short — a single `run_typescript` call has a ~60 s budget.
5. Stop with `tools.process.stop({ processId })`.

## Character creation

The game asks a few questions at startup: a name (lowercase a–z, 3–16 chars), gender
(m/f), confirm the choices, and one free-text custom question (e.g. your trade). Answer
them in order; anything reasonable works.

## Getting going

The game is self-explanatory — read the room descriptions and the `>>` prompt, and use
`help` in-game for the command list. A few basics:

- `look` — describe the room, its exits, items, and who is here
- `inventory` — what you carry, plus your money
- movement by direction: `north`, `south`, `east`, `west`, `up`, `down` (aliases like
  `n` work too)
- `take <item>`, `read <item>`, `say <something>`, `emote <action>`

Set a goal for yourself (find a place, talk to someone, retrieve something) and follow
the descriptions — exits and objects are mentioned in the text.

## No cheating

Do not read the story's own files under `stories/` (zones, npcs, story.py, resources)
to learn exits, items, or solutions — play through the game's output only. The `tale/`
framework code is fine to consult for mechanics, but the story content must come from
the game itself.
