from fastapi import FastAPI, BackgroundTasks, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import asyncio
import uuid
import random
import os

from src.agents.crew import run_show_pipeline, generate_signoff_message
from src.audio.tts import synthesize_dialogue, TTSQueueManager
from src.audio.mixer import mix_show
from src.config_loader import load_programs_config, get_agent_config

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
    guest_name: str = None
    program_type: str = "custom"

class CallerRequest(BaseModel):
    caller_prompt: str
    caller_topic: str

class ForceTransitionRequest(BaseModel):
    program_id: str
    interrupt_reason: str = "We have breaking news!"

# In-memory state
state = {
    "current_program": None,
    "upcoming_programs": [],
    "logs": []
}

# Load the catalog of available programs from YAML
programs_catalog = load_programs_config()
QUEUE_SIZE = 4

# A token to cancel the currently generating program
cancellation_token = {"cancelled": False}

def log_debug(message):
    state["logs"].append(message)
    print(message)
    if len(state["logs"]) > 50:
        state["logs"].pop(0)

def fill_queue():
    """Ensures the queue always has QUEUE_SIZE programs in it by pulling randomly from the catalog."""
    while len(state["upcoming_programs"]) < QUEUE_SIZE:
        if not programs_catalog:
            break
        prog_def = random.choice(programs_catalog)
        show = {
            "id": uuid.uuid4().hex[:8],
            "title": prog_def.get("title"),
            "theme": prog_def.get("theme"),
            "rj_name": prog_def.get("presenter"),
            "guest_name": prog_def.get("guest"),
            "type": prog_def.get("program_type")
        }
        state["upcoming_programs"].append(show)
        log_debug(f"Auto-queued program: {show['title']}")

def parse_crew_output(output_text, presenter_file):
    dialogues = []
    lines = output_text.split('\n')
    current_speaker = None
    current_text = []

    # Try to load the actual presenter's display name for fallback
    presenter_name = "Host"
    try:
        conf = get_agent_config("presenters", presenter_file)
        presenter_name = conf.get("name", "Host")
    except:
        pass

    for line in lines:
        line = line.strip()
        if not line:
            continue

        if ':' in line and not line.startswith('*'):
            parts = line.split(':', 1)
            speaker = parts[0].strip()

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

    if not dialogues and current_text:
        dialogues.append({"speaker": presenter_name, "text": " ".join(current_text)})

    return dialogues

async def process_queue():
    while True:
        # Keep queue full
        fill_queue()

        if state["upcoming_programs"] and not state["current_program"]:
            state["current_program"] = state["upcoming_programs"].pop(0)

        if state["current_program"]:
            prog = state["current_program"]
            log_debug(f"Starting program: {prog.get('title', prog['theme'])} with {prog['rj_name']}")

            # Reset cancellation token for the new run
            cancellation_token["cancelled"] = False

            # Generate a unique workspace for this show to prevent file overlap races
            show_workspace = os.path.join("output", prog["id"])
            os.makedirs(show_workspace, exist_ok=True)
            os.makedirs("assets", exist_ok=True)

            try:
                log_debug("Executing CrewAI Agents...")
                loop = asyncio.get_running_loop()

                # We wrap run_show_pipeline in a future so we can abandon it if cancelled
                future = loop.run_in_executor(None, lambda: run_show_pipeline(
                    theme=prog['theme'],
                    presenter_file=prog['rj_name'],
                    guest_file=prog.get('guest_name'),
                    caller_id=prog.get('caller_id', 'RandomCaller'),
                    caller_prompt=prog.get('caller_prompt'),
                    caller_topic=prog.get('caller_topic'),
                    cancellation_token=cancellation_token
                ))

                # Wait for crew to finish or be cancelled (we check cancellation state inside the loop)
                # However since CrewAI is heavily synchronous inside, it might block the executor thread.
                # That's okay, we'll just abandon the result if cancellation_token is true.
                raw_output = await future

                if cancellation_token["cancelled"]:
                    log_debug(f"Program {prog.get('title')} was interrupted. Abandoning generation.")
                    state["current_program"] = None
                    continue

                if hasattr(raw_output, 'raw'):
                    raw_output = raw_output.raw
                elif not isinstance(raw_output, str):
                    raw_output = str(raw_output)

                log_debug(f"CrewAI finished. Parsing {len(raw_output)} chars.")

                dialogues = parse_crew_output(raw_output, prog['rj_name'])

                if cancellation_token["cancelled"]:
                    state["current_program"] = None
                    continue

                log_debug(f"Parsed {len(dialogues)} dialogue chunks. Synthesizing audio...")

                await loop.run_in_executor(None, lambda: synthesize_dialogue(dialogues, output_dir=show_workspace))

                if cancellation_token["cancelled"]:
                    state["current_program"] = None
                    continue

                log_debug("TTS Generation Complete. Mixing audio...")

                final_path = f"output/show_{prog['id']}.mp3"
                await loop.run_in_executor(None, lambda: mix_show(output_dir=show_workspace, final_mix_path=final_path))
                log_debug(f"Finished Program. Saved to {final_path}")

                # Cleanup the workspace after successful generation
                try:
                    import shutil
                    shutil.rmtree(show_workspace)
                except Exception as cleanup_e:
                    log_debug(f"Warning: Failed to cleanup workspace {show_workspace}: {cleanup_e}")

            except Exception as e:
                log_debug(f"Error in pipeline: {e}")

            state["current_program"] = None

        await asyncio.sleep(2)

@app.on_event("startup")
async def startup_event():
    # Clear output directory from previous runs
    os.makedirs("output", exist_ok=True)
    for f in os.listdir("output"):
        os.remove(os.path.join("output", f))

    # Pre-fill queue initially
    fill_queue()
    asyncio.create_task(process_queue())

@app.get("/state")
async def get_state():
    return state

@app.get("/programs/available")
async def get_available_programs():
    return {"programs": programs_catalog}

@app.post("/programs/force")
async def force_transition(req: ForceTransitionRequest):
    # Find the target program
    target_prog = next((p for p in programs_catalog if p.get("id") == req.program_id), None)
    if not target_prog:
        raise HTTPException(status_code=404, detail="Program not found in catalog")

    show = {
        "id": uuid.uuid4().hex[:8],
        "title": target_prog.get("title"),
        "theme": target_prog.get("theme"),
        "rj_name": target_prog.get("presenter"),
        "guest_name": target_prog.get("guest"),
        "type": target_prog.get("program_type")
    }

    # 1. Trigger Cancellation of Current Program
    cancellation_token["cancelled"] = True

    current = state.get("current_program")
    if current:
        log_debug(f"Triggering graceful interrupt for {current.get('title')}. Next up: {show['title']}")
        try:
            # Quick LLM call to get sign-off
            loop = asyncio.get_running_loop()
            sign_off_text = await loop.run_in_executor(None, lambda: generate_signoff_message(
                presenter_file=current['rj_name'],
                interrupt_reason=req.interrupt_reason,
                next_show=show['title']
            ))

            # Format and TTS the signoff
            # Try to get presenter name
            presenter_name = "Host"
            try:
                conf = get_agent_config("presenters", current['rj_name'])
                presenter_name = conf.get("name", "Host")
            except:
                pass

            signoff_dialogue = [{"speaker": presenter_name, "text": sign_off_text}]

            # Determine the show workspace
            show_workspace = os.path.join("output", current["id"])
            if not os.path.exists(show_workspace):
                os.makedirs(show_workspace)

            # Synthesize just the signoff into the current show's workspace
            await loop.run_in_executor(None, lambda: synthesize_dialogue(signoff_dialogue, output_dir=show_workspace, start_index=999))

            # Mix whatever was completed + signoff
            await loop.run_in_executor(None, lambda: mix_show(output_dir=show_workspace, final_mix_path=f"output/interrupted_{current['id']}.mp3"))
            log_debug("Successfully saved interrupted show.")

            # Cleanup the workspace
            try:
                import shutil
                shutil.rmtree(show_workspace)
            except:
                pass
        except Exception as e:
            log_debug(f"Error generating graceful interrupt: {e}")
    else:
        log_debug(f"No active program to interrupt. Forcing {show['title']} to the front.")

    # 2. Insert new program at the front
    state["upcoming_programs"].insert(0, show)
    return {"status": "success", "message": "Transition forced"}

@app.post("/program")
async def add_program(req: ShowRequest):
    show = {
        "id": uuid.uuid4().hex[:8],
        "title": f"Custom Show: {req.theme}",
        "theme": req.theme,
        "rj_name": req.rj_name, # should be the yaml filename
        "guest_name": req.guest_name,
        "type": req.program_type
    }
    state["upcoming_programs"].append(show)
    log_debug(f"Added custom program to queue: {req.theme}")
    return {"status": "success", "program": show}

@app.post("/caller")
async def inject_caller(req: CallerRequest):
    active_rj = "max.yaml" # Default
    if state["current_program"]:
        active_rj = state["current_program"].get("rj_name", "max.yaml")
    elif state["upcoming_programs"]:
        active_rj = state["upcoming_programs"][0].get("rj_name", "max.yaml")

    show = {
        "id": uuid.uuid4().hex[:8],
        "title": f"Caller Interruption: {req.caller_topic}",
        "theme": req.caller_topic,
        "rj_name": active_rj,
        "type": "caller_injection",
        "caller_id": uuid.uuid4().hex[:4],
        "caller_prompt": req.caller_prompt,
        "caller_topic": req.caller_topic
    }

    state["upcoming_programs"].insert(0, show)
    log_debug(f"Injected random caller topic: {req.caller_topic}")
    return {"status": "success", "program": show}
