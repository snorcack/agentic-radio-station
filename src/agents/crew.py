import os
from crewai import Agent, Task, Crew, Process
from src.config_loader import get_agent_config, get_all_agent_configs

def create_agent_from_config(config_data, allow_delegation=False, extra_backstory=""):
    backstory = config_data.get('backstory', '')

    # Inject extra attributes to make backstory richer
    details = []
    if 'personality' in config_data:
        details.append(f"Personality: {config_data['personality']}")
    if 'expertise' in config_data:
        details.append(f"Expertise: {config_data['expertise']}")
    if 'quirks' in config_data:
        details.append(f"Quirks: {config_data['quirks']}")
    if 'voice' in config_data:
        details.append(f"Voice Style: {config_data['voice']}")

    if details:
        backstory += "\n\nAdditional Details:\n" + "\n".join(details)

    if extra_backstory:
        backstory += f"\n\n{extra_backstory}"

    return Agent(
        role=config_data.get('role', 'Agent'),
        goal=config_data.get('goal', 'Complete the task.'),
        backstory=backstory,
        verbose=True,
        llm='gemini/gemini-1.5-flash',
        allow_delegation=allow_delegation
    )

def get_producer_agent():
    # Load default producer
    config = get_agent_config("producers", "producer.yaml")
    if not config:
        # Fallback if config is missing
        config = {
            "role": "Producer Orchestrator",
            "goal": "Manage the show schedule.",
            "backstory": "A veteran radio producer."
        }
    return create_agent_from_config(config, allow_delegation=True)

def get_presenter_agent(presenter_file: str):
    config = get_agent_config("presenters", presenter_file)
    if not config:
        raise ValueError(f"Unknown presenter config: {presenter_file}")
    return create_agent_from_config(config, allow_delegation=False)

def get_guest_agent(guest_file: str):
    config = get_agent_config("guests", guest_file)
    if not config:
        raise ValueError(f"Unknown guest config: {guest_file}")
    return create_agent_from_config(config, allow_delegation=False)

def get_caller_agent(caller_file: str = "default_caller.yaml", caller_id="Anonymous", custom_prompt=None):
    config = get_agent_config("callers", caller_file)
    if not config:
        config = {
            "role": "Random Fake Caller",
            "goal": "Call into the show.",
            "backstory": "You are a random caller."
        }

    # Merge custom prompt into backstory if provided
    extra = f"You are caller {caller_id}."
    if custom_prompt:
        extra = f"{custom_prompt}. {extra}"

    return create_agent_from_config(config, allow_delegation=False, extra_backstory=extra)

def generate_signoff_message(presenter_file: str, interrupt_reason: str, next_show: str):
    """
    Very fast, isolated LLM call to generate a graceful interrupt signoff.
    """
    selected_rj = get_presenter_agent(presenter_file)
    task = Task(
        description=f'Write a very quick (2 sentences max) graceful sign-off because the show is being interrupted mid-stream. Reason: "{interrupt_reason}". Announce that up next is "{next_show}". Stay in your persona.',
        expected_output='A 1-2 sentence sign-off message.',
        agent=selected_rj
    )
    crew = Crew(
        agents=[selected_rj],
        tasks=[task],
        process=Process.sequential,
        verbose=False
    )
    result = crew.kickoff()
    return result.raw

def run_show_pipeline(theme, presenter_file, guest_file=None, caller_id="Anonymous", caller_prompt=None, caller_topic=None, cancellation_token=None):
    """
    cancellation_token: A dictionary like {"cancelled": False} that can be updated from another thread.
    We'll check it between crew executions if needed, but CrewAI is mostly synchronous.
    (For this MVP we'll check it before starting).
    """
    if cancellation_token and cancellation_token.get("cancelled"):
        return None

    selected_rj = get_presenter_agent(presenter_file)
    producer = get_producer_agent()

    agents = [producer, selected_rj]

    # Guest logic
    guest_agent = None
    if guest_file:
        guest_agent = get_guest_agent(guest_file)
        agents.append(guest_agent)

    # Caller logic
    caller = get_caller_agent(caller_id=caller_id, custom_prompt=caller_prompt)
    agents.append(caller)

    # Define tasks
    monologue_task_desc = f'Write an engaging opening monologue for the radio segment about the theme "{theme}". The monologue should strictly follow your persona.'
    if guest_agent:
        monologue_task_desc += f' After your introduction, introduce your guest, {guest_agent.role}, and ask them an opening question about the theme.'

    monologue_task = Task(
        description=monologue_task_desc,
        expected_output='A monologue introducing the theme (and optionally the guest).',
        agent=selected_rj
    )

    tasks = [monologue_task]

    if guest_agent:
        guest_response_task = Task(
            description=f'Respond to the RJ\'s opening question about the theme "{theme}". Stay in your persona.',
            expected_output='A dialogue snippet of the guest answering the RJ.',
            agent=guest_agent,
            context=[monologue_task]
        )
        tasks.append(guest_response_task)

    interruption_desc = f'Call into the show and interrupt the ongoing discussion about "{theme}". Introduce your random, crazy persona and give a wild, funny opinion or problem related to the theme.'
    if caller_topic:
        interruption_desc = f'Call into the show and interrupt. Introduce yourself based on your persona and aggressively discuss this specific topic: "{caller_topic}".'

    interruption_task = Task(
        description=interruption_desc,
        expected_output='A dialogue snippet of the caller interrupting.',
        agent=caller,
        context=tasks.copy()
    )
    tasks.append(interruption_task)

    response_task = Task(
        description=f'Respond to the crazy caller\'s interruption. Maintain your persona while addressing the caller\'s wild statements.',
        expected_output='A dialogue snippet of the RJ responding to the caller.',
        agent=selected_rj,
        context=[interruption_task]
    )
    tasks.append(response_task)

    formatting_task = Task(
        description='Format the entire interaction into a structured dialogue format suitable for Text-to-Speech (TTS) generation. Ensure the text is split into short, easily readable sentences. Use clear speaker labels (e.g., RJ Name: ... or Caller: ...). Keep sentences concise for faster TTS generation.',
        expected_output='A fully structured script of the radio segment with clear speaker labels and short sentences.',
        agent=producer,
        context=tasks.copy()
    )
    tasks.append(formatting_task)

    crew = Crew(
        agents=agents,
        tasks=tasks,
        process=Process.sequential,
        memory=True,
        embedder={
            "provider": "google-generativeai",
            "config": {
                "model": "models/embedding-001",
                "api_key": os.environ.get("GEMINI_API_KEY", "dummy_key_for_validation")
            }
        },
        verbose=True
    )

    result = crew.kickoff()
    return result
