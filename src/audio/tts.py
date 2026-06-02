import os
import asyncio
import uuid
import random
from google import genai
from google.genai import types

# Default voice mappings
VOICE_MAP = {
    "RJ Max": "Puck",
    "RJ Dave": "Charon",
    "RJ Luna": "Aoede",
}

CALLER_VOICES = ["Kore", "Fenrir", "Leda", "Orion", "Lyra", "Vega", "Rigel", "Sirius"]

class TTSQueueManager:
    def __init__(self, output_dir="output"):
        self.output_dir = output_dir
        self.queue = asyncio.Queue()
        self.client = genai.Client() # Assumes GEMINI_API_KEY is set in environment
        self.model_name = os.environ.get("GEMINI_AUDIO_MODEL", "gemini-2.5-flash")

        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)

    def get_voice_for_speaker(self, speaker):
        if speaker in VOICE_MAP:
            return VOICE_MAP[speaker]
        # Assign a random voice for callers
        return random.choice(CALLER_VOICES)

    async def worker(self):
        while True:
            item = await self.queue.get()
            if item is None:
                self.queue.task_done()
                break

            speaker, text, index = item['speaker'], item['text'], item['index']
            voice_name = self.get_voice_for_speaker(speaker)

            try:
                # Generate audio using Gemini's native audio modality
                response = await self.client.aio.models.generate_content(
                    model=self.model_name,
                    contents=text,
                    config=types.GenerateContentConfig(
                        response_modalities=["AUDIO"],
                        speech_config=types.SpeechConfig(
                            voice_config=types.VoiceConfig(
                                prebuilt_voice_config=types.PrebuiltVoiceConfig(
                                    voice_name=voice_name
                                )
                            )
                        )
                    )
                )

                # Extract and save audio bytes
                for part in response.candidates[0].content.parts:
                    if part.inline_data and part.inline_data.mime_type.startswith("audio/"):
                        speaker_safe = speaker.replace(' ', '_').lower()
                        filename = os.path.join(self.output_dir, f"dialogue_{index:08d}_{speaker_safe}_{uuid.uuid4().hex[:8]}.wav")
                        with open(filename, "wb") as f:
                            f.write(part.inline_data.data)
                        print(f"Generated {filename} for {speaker}")
                        break
            except Exception as e:
                print(f"Error generating audio for {speaker}: {e}. Falling back to text-only mode.")
                speaker_safe = speaker.replace(' ', '_').lower()
                txt_filename = os.path.join(self.output_dir, f"dialogue_{index:08d}_{speaker_safe}_{uuid.uuid4().hex[:8]}.txt")
                with open(txt_filename, "w") as f:
                    f.write(f"{speaker}: {text}")
                print(f"Generated text fallback {txt_filename}")
            finally:
                self.queue.task_done()

    async def process_dialogues(self, dialogues):
        """
        dialogues is a list of dicts: [{"speaker": "RJ Max", "text": "Hello world!"}, ...]
        """
        # Start a couple of worker tasks to process in background (maintaining a buffer)
        workers = [asyncio.create_task(self.worker()) for _ in range(3)]

        # Find the highest existing index to allow for continuous append
        starting_index = 0
        import glob
        existing_files = glob.glob(os.path.join(self.output_dir, "dialogue_*.wav"))
        for ef in existing_files:
            try:
                idx = int(os.path.basename(ef).split('_')[1])
                if idx >= starting_index:
                    starting_index = idx + 1
            except:
                pass

        for i, dialogue in enumerate(dialogues):
            await self.queue.put({
                "speaker": dialogue.get("speaker", "Unknown"),
                "text": dialogue.get("text", ""),
                "index": starting_index + i
            })

        await self.queue.join()

        # Stop workers
        for _ in range(3):
            await self.queue.put(None)
        await asyncio.gather(*workers)
        print("Finished processing all dialogues in queue.")

def synthesize_dialogue(dialogues: list, output_dir: str = "output", start_index: int = None):
    """
    Synchronous wrapper to initialize the async queue manager and process dialogues.
    """
    manager = TTSQueueManager(output_dir=output_dir)
    # We patch process_dialogues slightly to accept a custom start_index just for this wrapper if provided
    async def run_with_index():
        if start_index is not None:
            # Quick override
            workers = [asyncio.create_task(manager.worker()) for _ in range(3)]
            for i, dialogue in enumerate(dialogues):
                await manager.queue.put({
                    "speaker": dialogue.get("speaker", "Unknown"),
                    "text": dialogue.get("text", ""),
                    "index": start_index + i
                })
            await manager.queue.join()
            for _ in range(3):
                await manager.queue.put(None)
            await asyncio.gather(*workers)
        else:
            await manager.process_dialogues(dialogues)

    asyncio.run(run_with_index())
