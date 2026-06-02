import os
from crewai import Agent, Task, Crew, Process

# Make sure GEMINI_API_KEY is available in the environment
# os.environ["GEMINI_API_KEY"] = os.environ.get("GEMINI_API_KEY", "")

def get_producer_agent():
    return Agent(
        role='Producer Orchestrator',
        goal='Manage the show schedule, select the active RJ, and generate high-level show briefs.',
        backstory='A veteran radio producer who knows exactly what the audience wants and how to keep the show flowing.',
        verbose=True,
        llm='gemini/gemini-1.5-flash',
        allow_delegation=True
    )

def get_rj_max_agent():
    return Agent(
        role='Radio Jockey Max',
        goal='Entertain the audience with high energy, fast-paced speaking, and modern slang.',
        backstory='RJ Max is the life of the party, always up to date with the latest trends and speaks at 100 miles an hour.',
        verbose=True,
        llm='gemini/gemini-1.5-flash',
        allow_delegation=False
    )

def get_rj_luna_agent():
    return Agent(
        role='Radio Jockey Luna',
        goal='Host a low-energy, slow-paced, introspective show as a cosmic philosopher.',
        backstory='RJ Luna is deep, calm, and constantly contemplating the mysteries of the universe, bringing a relaxing vibe to the station.',
        verbose=True,
        llm='gemini/gemini-1.5-flash',
        allow_delegation=False
    )

def get_rj_dave_agent():
    return Agent(
        role='Radio Jockey Dave',
        goal='Host a sarcastic, classic rock-themed segment while expressing disdain for modern technology.',
        backstory='RJ Dave is an old-school classic rocker who misses the good old days. He hates smartphones, social media, and modern pop culture.',
        verbose=True,
        llm='gemini/gemini-1.5-flash',
        allow_delegation=False
    )

def get_fake_caller_agent(caller_id="Anonymous", custom_prompt=None):
    # Append caller ID to backstory for memory entity context
    backstory_suffix = f" You are caller {caller_id}."
    if custom_prompt:
        backstory = f"{custom_prompt}. {backstory_suffix}"
    else:
        backstory = 'You are a random caller with a wild persona (could be a VIP, a drunk uncle, a prank teenager, or a single mom). You go bonkers and stir things up.' + backstory_suffix

    return Agent(
        role='Random Fake Caller',
        goal='Call into the show to create dynamic, unpredictable, and funny interruptions based on the current topic.',
        backstory=backstory,
        verbose=True,
        llm='gemini/gemini-1.5-flash',
        allow_delegation=False
    )

def run_show_pipeline(theme, rj_name, caller_id="Anonymous", caller_prompt=None, caller_topic=None):
    rj_agents = {
        'Max': get_rj_max_agent(),
        'Luna': get_rj_luna_agent(),
        'Dave': get_rj_dave_agent()
    }

    selected_rj = rj_agents.get(rj_name)
    if not selected_rj:
        raise ValueError(f"Unknown RJ: {rj_name}")

    producer = get_producer_agent()
    caller = get_fake_caller_agent(caller_id, caller_prompt)

    monologue_task = Task(
        description=f'Write an engaging opening monologue for the radio segment about the theme "{theme}". The monologue should strictly follow your persona.',
        expected_output='A monologue introducing the theme.',
        agent=selected_rj
    )

    interruption_desc = f'Call into the show and interrupt the RJ\'s monologue about "{theme}". Introduce your random, crazy persona and give a wild, funny opinion or problem related to the theme.'
    if caller_topic:
        interruption_desc = f'Call into the show and interrupt the RJ\'s monologue. Introduce yourself based on your persona and aggressively discuss this specific topic: "{caller_topic}".'

    interruption_task = Task(
        description=interruption_desc,
        expected_output='A dialogue snippet of the caller interrupting the RJ.',
        agent=caller,
        context=[monologue_task]
    )

    response_task = Task(
        description=f'Respond to the crazy caller\'s interruption about "{theme}". Maintain your persona while addressing the caller\'s wild statements.',
        expected_output='A dialogue snippet of the RJ responding to the caller.',
        agent=selected_rj,
        context=[interruption_task]
    )

    formatting_task = Task(
        description='Format the entire interaction (Monologue, Caller Interruption, RJ Response) into a structured dialogue format suitable for Text-to-Speech (TTS) generation. Ensure the text is split into short, easily readable sentences. Use clear speaker labels (e.g., RJ Max: ... or Caller: ...). Keep sentences concise for faster TTS generation.',
        expected_output='A fully structured script of the radio segment with clear speaker labels and short sentences.',
        agent=producer,
        context=[monologue_task, interruption_task, response_task]
    )

    crew = Crew(
        agents=[producer, selected_rj, caller],
        tasks=[monologue_task, interruption_task, response_task, formatting_task],
        process=Process.sequential,
        memory=True,
        embedder={
            "provider": "google",
            "config": {
                "model": "models/embedding-001",
                "api_key": os.environ.get("GEMINI_API_KEY", "dummy_key_for_validation")
            }
        },
        verbose=True
    )

    result = crew.kickoff()
    return result
