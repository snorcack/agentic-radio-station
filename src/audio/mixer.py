import os
import glob
from pydub import AudioSegment
from pydub.generators import Sine

def generate_placeholder_assets(assets_dir="assets"):
    if not os.path.exists(assets_dir):
        os.makedirs(assets_dir)

    music_path = os.path.join(assets_dir, "music.mp3")
    ring_path = os.path.join(assets_dir, "ring.mp3")

    # Generate placeholder music (low frequency drone)
    if not os.path.exists(music_path):
        drone = Sine(110).to_audio_segment(duration=5000)
        drone = drone - 20  # reduce volume
        drone.export(music_path, format="mp3")
        print(f"Generated placeholder asset: {music_path}")

    # Generate placeholder phone ring (classic dual tone)
    if not os.path.exists(ring_path):
        tone1 = Sine(440).to_audio_segment(duration=400)
        tone2 = Sine(480).to_audio_segment(duration=400)
        silence = AudioSegment.silent(duration=200)
        ring_cycle = tone1.overlay(tone2) + silence + tone1.overlay(tone2) + AudioSegment.silent(duration=1000)
        ring_cycle.export(ring_path, format="mp3")
        print(f"Generated placeholder asset: {ring_path}")

def mix_show(output_dir="output", assets_dir="assets", final_mix_path="output/show.mp3"):
    generate_placeholder_assets(assets_dir)

    # Load assets
    music = AudioSegment.from_mp3(os.path.join(assets_dir, "music.mp3"))
    ring = AudioSegment.from_mp3(os.path.join(assets_dir, "ring.mp3"))

    # Get all dialogue files (both .wav and .txt fallbacks), sorted by the 8-digit index
    dialogue_wavs = glob.glob(os.path.join(output_dir, "dialogue_*.wav"))
    dialogue_txts = glob.glob(os.path.join(output_dir, "dialogue_*.txt"))
    dialogue_files = sorted(dialogue_wavs + dialogue_txts)

    if not dialogue_files:
        print("No dialogue files found in output directory.")
        return

    master_track = AudioSegment.empty()

    for filepath in dialogue_files:
        filename = os.path.basename(filepath)

        # If it's a text fallback, generate 2 seconds of silence instead of audio
        if filepath.endswith('.txt'):
            segment = AudioSegment.silent(duration=2000)
            print(f"Skipped missing audio for text fallback: {filename}")
        else:
            segment = AudioSegment.from_wav(filepath)

        # Check if caller is in the filename to prefix with ring
        if "_caller" in filename.lower():
            master_track += ring

        master_track += segment
        # Add a short pause between segments
        master_track += AudioSegment.silent(duration=300)

    # Match background music duration
    bg_music = AudioSegment.empty()
    while len(bg_music) < len(master_track):
        bg_music += music

    # Truncate bg music to exact length of voice track and lower volume
    bg_music = bg_music[:len(master_track)] - 15

    # Overlay voices on background music
    final_mix = bg_music.overlay(master_track)

    # Export
    final_mix.export(final_mix_path, format="mp3")
    print(f"Exported final mix to {final_mix_path} (Duration: {len(final_mix)/1000.0}s)")

if __name__ == "__main__":
    mix_show()
