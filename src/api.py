from fastapi import FastAPI, BackgroundTasks, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import asyncio
import uuid
from typing import List, Optional
import os

from src.agents.crew import run_show_pipeline
from src.audio.tts import synthesize_dialogue
from src.audio.mixer import mix_show

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

class ShowRequest(BaseModel):
    theme: str
    rj_name: str

class CallerRequest(BaseModel):
    caller_prompt: str
    caller_topic: str

# In-memory state
state = {
    "current_program": None,
    "upcoming_programs": [],
    "logs": []
}

def log_debug(message):
    state["logs"].append(message)
    print(message)
    if len(state["logs"]) > 50:
        state["logs"].pop(0)

# Parsing utility to convert raw text output from CrewAI into structured dialogues list
def parse_crew_output(output_text):
    dialogues = []
    lines = output_text.split('\n')
    current_speaker = None
    current_text = []

    for line in lines:
        line = line.strip()
        if not line:
            continue

        if ':' in line and not line.startswith('*'): # simplistic heuristic for speaker label
            parts = line.split(':', 1)
            speaker = parts[0].strip()

            # Filter out non-speakers (like actions or generic labels if they don't look right)
            if len(speaker) > 20 or speaker.lower() in ['format', 'note']:
                current_text.append(line)
                continue

            if current_speaker:
                dialogues.append({"speaker": current_speaker, "text": " ".join(current_text)})

            current_speaker = speaker
            current_text = [parts[1].strip()]
        else:
            current_text.append(line)

    if current_speaker:
        dialogues.append({"speaker": current_speaker, "text": " ".join(current_text)})

    # Fallback if no structured speakers found
    if not dialogues and current_text:
        dialogues.append({"speaker": "RJ Max", "text": " ".join(current_text)})

    return dialogues

async def process_queue():
    while True:
        if not state["upcoming_programs"] and not state["current_program"]:
            await asyncio.sleep(5)
            continue

        if state["upcoming_programs"] and not state["current_program"]:
            state["current_program"] = state["upcoming_programs"].pop(0)

        if state["current_program"]:
            prog = state["current_program"]
            log_debug(f"Starting program: {prog['theme']} with {prog['rj_name']}")

            # Ensure output directories exist
            os.makedirs("output", exist_ok=True)
            os.makedirs("assets", exist_ok=True)

            try:
                # Run Pipeline
                log_debug("Executing CrewAI Agents...")

                # We need to run sync code in executor
                loop = asyncio.get_running_loop()
                raw_output = await loop.run_in_executor(None, lambda: run_show_pipeline(
                    theme=prog['theme'],
                    rj_name=prog['rj_name'],
                    caller_id=prog.get('caller_id', 'RandomCaller'),
                    caller_prompt=prog.get('caller_prompt'),
                    caller_topic=prog.get('caller_topic')
                ))

                # It might return a CrewOutput object instead of string in newer crewai versions
                if hasattr(raw_output, 'raw'):
                    raw_output = raw_output.raw
                elif not isinstance(raw_output, str):
                    raw_output = str(raw_output)

                log_debug(f"CrewAI finished. Parsing {len(raw_output)} chars.")

                dialogues = parse_crew_output(raw_output)
                log_debug(f"Parsed {len(dialogues)} dialogue chunks. Synthesizing audio...")

                await loop.run_in_executor(None, lambda: synthesize_dialogue(dialogues))
                log_debug("TTS Generation Complete. Mixing audio...")

                await loop.run_in_executor(None, lambda: mix_show())
                log_debug(f"Finished Program: {prog['theme']}. Saved to output/show.mp3")

            except Exception as e:
                log_debug(f"Error in pipeline: {e}")

            state["current_program"] = None

        await asyncio.sleep(2)

@app.on_event("startup")
async def startup_event():
    asyncio.create_task(process_queue())

@app.get("/state")
async def get_state():
    return state

@app.post("/program")
async def add_program(req: ShowRequest):
    show = {
        "id": uuid.uuid4().hex[:8],
        "theme": req.theme,
        "rj_name": req.rj_name,
        "type": "regular"
    }
    state["upcoming_programs"].append(show)
    log_debug(f"Added program to queue: {req.theme}")
    return {"status": "success", "program": show}

@app.post("/caller")
async def inject_caller(req: CallerRequest):
    # If there is a current program, interrupt it or queue it next
    active_rj = "Max" # Default
    if state["current_program"]:
        active_rj = state["current_program"].get("rj_name", "Max")
    elif state["upcoming_programs"]:
        active_rj = state["upcoming_programs"][0].get("rj_name", "Max")

    show = {
        "id": uuid.uuid4().hex[:8],
        "theme": req.caller_topic,
        "rj_name": active_rj,
        "type": "caller_injection",
        "caller_id": uuid.uuid4().hex[:4],
        "caller_prompt": req.caller_prompt,
        "caller_topic": req.caller_topic
    }

    # We put it at the front of the queue to happen next
    state["upcoming_programs"].insert(0, show)
    log_debug(f"Injected random caller topic: {req.caller_topic}")
    return {"status": "success", "program": show}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
