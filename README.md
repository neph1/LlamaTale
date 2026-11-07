
<p align="center">
  <img src="https://github.com/neph1/LlamaTale/assets/7988802/35f5924c-77bb-4686-9127-07a3251f6873?raw=true" alt="A prancing Llama"/>
</p>
<p align="center"> Welcome to LlamaTale! </p>

What is LlamaTale?

It is a continuation of the archived IF/MUD framework Tale.

It uses an LLM backend to describe locations and npcs vivid way.

It generates dialogue for NPC's based on the story context and their character.

Check the wiki on how to get started : https://github.com/neph1/LlamaTale/wiki 

Or <a href="https://discord.gg/SmUNnPZXYd">join the discord server</a> if you have any questions.

## Running with Docker

A `Dockerfile` is included for easy distribution. Build the image:

    docker build -t llamatale .

Run the bundled "Prancing Llama" story as a multi-player MUD server (web UI at `http://localhost:8180/tale/`):

    docker run -p 8180:8180 -v llamatale-data:/data llamatale

Or run it as single-player interactive fiction in your browser:

    docker run -p 8180:8180 -v llamatale-data:/data llamatale -g /app/stories/prancingllama -w

The `/data` volume persists MUD accounts (`useraccounts.sqlite`), savegames and uploads.

LlamaTale needs an external LLM backend. Point the container at yours with environment variables:

| Variable | Purpose | Example |
|---|---|---|
| `LLAMATALE_BACKEND` | LLM backend (`kobold_cpp`, `llama_cpp`, `openai`, ...) | `kobold_cpp` |
| `LLAMATALE_BACKEND_URL` | URL of the LLM backend server | `http://koboldcpp:5001` |
| `<BACKEND>_URL` | Backend-specific URL override (e.g. `KOBOLD_CPP_URL`) | `http://host.docker.internal:5001` |
| `OPENAI_API_KEY` / `KOBOLD_CPP_API_PASSWORD` | API credentials (passed through to the backend) | |
| `LLAMATALE_IMAGE_GEN_ADDRESS` / `LLAMATALE_IMAGE_GEN_PORT` | Image generation server (only if the story enables it) | `automatic1111` / `7860` |
| `LLAMATALE_HOST` / `LLAMATALE_PORT` | Bind address/port of the web server (default `0.0.0.0:8180` in the image) | |

`docker-compose.yml` wires this up with a volume and an optional `koboldcpp` service on a shared network:

    docker compose up

To verify the image without an LLM server, run the automated smoke test (headless story run with a built-in dummy LLM backend) inside the container:

    docker run --rm --entrypoint python -w /app llamatale -m tale.smoketest --game /app/stories/prancingllama --script /app/stories/prancingllama/smoke_test.txt

The container has a `HEALTHCHECK` that probes the web UI, so `docker ps` shows `healthy` once the game is up.


![prancingllama3](https://github.com/neph1/LlamaTale/assets/7988802/07e382b9-2ae1-4230-82c8-3bcfb77556e2)


More features (See https://github.com/neph1/LlamaTale/releases for a more up to date list):
* Run the <a href="https://github.com/neph1/LlamaTale/wiki/The-Land-of-Anything-%E2%80%90-Prompt-your-own-story">'Anything' story</a> to get a completely customized world. Answer a few questions on what you'd like and the LLM will generate the world, background, world, common items and creatures.
* Npcs can have <a href="https://github.com/neph1/LlamaTale/releases/tag/v0.18.0">pre-defined avatars</a>, which are used when talking to them.
* Npcs have 'idle' actions and reactions, brought to life by the LLM. This sometimes leads to <a href="https://github.com/neph1/LlamaTale/releases/tag/v0.11.0">drama</a>.
* Use Stable Diffusion to generate avatars for npcs you meet.
* Use <a href="https://github.com/neph1/LlamaTale/wiki/Be-a-Game-Master">"Game Master"</a> commands to affect the world and characters.
* Combat results are rolled by the MUD, but the LLM tries to describe them in a more fluid way.
* Characters have a memories of past events and conversations, as well as a flexible 'sentiment' towards other characters.
* You can mix predefined locations with dynamically generated ones. Ie, create a base and let the LLM do the rest.
* <a href="https://github.com/neph1/LlamaTale/releases/tag/v0.17.0">Quests</a>. See new places and meet new people with the (simple) automated quest system.
* Support for KoboldCpp and OpenAI API based backends.
