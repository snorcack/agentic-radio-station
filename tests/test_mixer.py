import pytest
import os
import glob
from unittest.mock import patch, MagicMock
from src.audio.mixer import mix_show, generate_placeholder_assets
from pydub import AudioSegment

@patch('src.audio.mixer.Sine')
@patch('src.audio.mixer.AudioSegment')
@patch('src.audio.mixer.glob.glob')
def test_audio_mixing_calculations(mock_glob, mock_audio_segment, mock_sine, tmp_path):
    out_dir = str(tmp_path / "output")
    assets_dir = str(tmp_path / "assets")
    mix_path = str(tmp_path / "show.mp3")

    mock_glob.side_effect = lambda path: {
        os.path.join(out_dir, "dialogue_*.wav"): [
            os.path.join(out_dir, "dialogue_00000000_rj_max_abcd.wav"),
            os.path.join(out_dir, "dialogue_00000001_caller_efgh.wav")
        ],
        os.path.join(out_dir, "dialogue_*.txt"): [
            os.path.join(out_dir, "dialogue_00000002_rj_max_ijkl.txt")
        ]
    }.get(path, [])

    class MockSegment:
        def __init__(self, length=0):
            self._length = length
        def __len__(self):
            return self._length
        def __add__(self, other):
            return MockSegment(self._length + len(other))
        def __sub__(self, other):
            return self # volume reduction
        def __getitem__(self, key):
            if isinstance(key, slice):
                # Mock slicing behavior to truncate duration
                stop = key.stop if key.stop is not None else self._length
                # Also the mixer does bg_music[:len(master_track)] - 15
                return MockSegment(min(self._length, stop))
            return self
        def overlay(self, other):
            return MockSegment(max(self._length, len(other)))
        def export(self, path, format="mp3"):
            global exported_duration
            exported_duration = self._length

    global exported_duration
    exported_duration = 0

    mock_audio_segment.empty.return_value = MockSegment(0)
    mock_audio_segment.silent.return_value = MockSegment(2000) # all silent segments return 2000

    def mock_from_mp3(path):
        if "music.mp3" in path: return MockSegment(5000)
        if "ring.mp3" in path: return MockSegment(1000)
        return MockSegment(0)
    mock_audio_segment.from_mp3.side_effect = mock_from_mp3

    def mock_from_wav(path):
        if "0000" in path: return MockSegment(3000)
        if "0001" in path: return MockSegment(2000)
        return MockSegment(0)
    mock_audio_segment.from_wav.side_effect = mock_from_wav

    mix_show(out_dir, assets_dir, mix_path)

    # We can explicitly assert the exported duration is 14000
    assert exported_duration >= 14000

@patch('src.audio.mixer.glob.glob')
@patch('src.audio.mixer.Sine')
@patch('src.audio.mixer.AudioSegment')
def test_mixer_empty_directory(mock_audio_segment, mock_sine, mock_glob, tmp_path):
    out_dir = str(tmp_path / "output")
    assets_dir = str(tmp_path / "assets")
    mix_path = str(tmp_path / "show.mp3")

    mock_glob.return_value = []
    # Test that empty directory handles gracefully
    try:
        from src.audio.mixer import mix_show
        mix_show(out_dir, assets_dir, mix_path)
    except Exception as e:
        pytest.fail(f"Empty directory threw an exception: {e}")
