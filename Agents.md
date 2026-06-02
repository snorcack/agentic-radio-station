# Agentic Radio Station Architecture

This repository contains a CrewAI-based multi-agent system that runs an automated radio station.

## Agent Definitions
1. **Producer Agent (Orchestrator):** Manages show schedules, selects the active Radio Jockey (RJ) for the segment, and generates show briefs.
2. **Radio Jockeys (RJs):**
   - **RJ Max:** High-energy, speaks fast, uses modern slang.
   - **RJ Luna:** Low-energy, slow-paced, introspective, cosmic philosopher.
   - **RJ Dave:** Sarcastic, classic rocker, hates modern tech.
3. **Fake Caller Agent:** Generates dynamic, persona-driven interruptions/opinions based on the active show topic.

## Core Modules to Build
- `src/agents/crew.py`: Contains CrewAI agent definitions, tasks, and orchestrator loops.
- `src/audio/tts.py`: Connects to Gemini API (`google-genai`) to synthesize text scripts into WAV/MP3 files using native audio output.
- `src/audio/mixer.py`: Uses `pydub` to overlay background music, transitions, and voice tracks.
- `src/main.py`: The entry point that loops the entire radio show lifecycle.
