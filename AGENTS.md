# AI Radio Station Architecture & Context
**For Future AI Agents & Maintainers**

This document provides a comprehensive overview of the AI Radio Station architecture. It is designed to help future AI agents understand the codebase, context, and data flow so they can easily build new features or debug existing ones without needing to read every file.

---

## 1. System Overview
The system is a continuous, 24/7 autonomous radio station orchestrator. It uses CrewAI to generate structured podcast scripts between different personas, native Google Gemini Text-to-Speech (TTS) to generate the audio, and PyDub to mix the final show with sound effects and background music.

The entire system is configuration-driven using YAML files, and features a FastAPI backend combined with a React (Vite/Tailwind) frontend dashboard.

## 2. Directory Structure & Core Components

- `config/`: The central brain for dynamic content. Contains YAML files defining `presenters/`, `producers/`, `guests/`, `callers/`, and the main `programs.yaml` schedule catalog.
- `src/api.py`: The **FastAPI Backend**. It maintains a continuous background loop (`process_queue`) that ensures 4 programs are always queued. It executes the pipeline, handles API endpoints, and manages the state.
- `src/agents/crew.py`: The **CrewAI Pipeline**. It loads YAML configs, instantiates agents (Producer, RJ, Guest, Caller), and coordinates sequential Tasks (Monologue -> Interruption -> Response -> Formatting) into a single structured dialogue output.
- `src/audio/tts.py`: The **TTS Engine**. Uses `google-genai` native `AUDIO` modalities. It runs an async queue manager to process dialogue snippets in parallel, mapping speaker roles to specific Gemini voices. Falls back to generating `.txt` files if the API fails.
- `src/audio/mixer.py`: The **Audio Mixer**. Uses `pydub`. It reads the chronological `dialogue_*.wav` files, inserts phone ring SFX for caller segments, inserts silence for `.txt` fallbacks, layers the entire sequence over looped background music, exports `show.mp3`, and **cleans up intermediate files**.
- `frontend/`: The **React UI**. A Vite application running a dashboard that polls `/state` every 2 seconds.

## 3. The Graceful Interrupt Mechanism
One of the most complex features is the "Force Transition" / Graceful Interrupt feature.
If a user forces a transition via the UI:
1. The backend (`api.py`) receives a `POST /programs/force`.
2. It sets a global `cancellation_token["cancelled"] = True`.
3. The background worker loop observes this token and **abandons** the currently generating CrewAI script or TTS processing queue.
4. The backend makes a rapid, isolated LLM call (`generate_signoff_message` in `crew.py`) to generate a 2-sentence sign-off matching the current RJ's persona ("We have breaking news, up next is...").
5. The sign-off is converted to TTS and mixed with whatever audio was successfully completed *before* the cancellation.
6. The forced program is injected at the front of the queue and begins processing immediately.
*Note: To prevent file collisions during this race, every show runs inside a uniquely named workspace (`output/<prog_id>/`).*

## 4. API Endpoints

- `GET /state`: Returns the current queue, the active program, and pipeline execution logs.
- `GET /programs/available`: Returns the catalog of shows parsed from `config/programs.yaml`.
- `POST /program`: Adds a custom string-based program to the back of the queue.
- `POST /caller`: Injects a random caller into the front of the queue (to interrupt the next/current show).
- `POST /programs/force`: Takes a `program_id` and an `interrupt_reason`, triggers the Graceful Interrupt mechanism, and forces the show to play next.

## 5. Adding New Features (Agent Guide)

When instructed to add new features, keep these architectural rules in mind:

* **Adding Personas:** Do not hardcode new agents in Python. Simply create a new `.yaml` file in `config/presenters/` (or guests, callers, etc.). The `config_loader.py` will handle the rest.
* **Modifying the Audio Pipeline:** All intermediate TTS files are numbered chronologically (`dialogue_0000001_...`). If you add new audio elements (like advertisements or jingles), inject them into the PyDub master track sequence in `src/audio/mixer.py` based on their filename or index.
* **Async Concurrency:** The backend runs FastAPI (async) but CrewAI and PyDub are heavily synchronous. We wrap them in `loop.run_in_executor` in `api.py`. Be careful not to block the main event loop if you add new processing steps.
* **Testing Requirements:** `pydub` requires `ffmpeg` installed on the host machine. If you write tests, mock PyDub functionality or ensure the test environment provides `ffmpeg`. (Tests currently mock CrewAI and API calls to prevent expensive runs).

## 6. How to Run Locally
A Windows batch file (`run_station.bat`) is provided in the root directory. It automatically prompts for the `GEMINI_API_KEY`, installs backend and frontend dependencies, and boots both servers. If no key is provided, it falls back to a dummy key (mock mode) where CrewAI will fail but the system won't crash.
