import pytest
import os
from unittest.mock import patch, MagicMock
from src.audio.tts import synthesize_dialogue

@patch('src.audio.tts.genai.Client')
def test_tts_queue_mocked_success(mock_client_class, tmp_path):
    out_dir = str(tmp_path / "output")

    # Mock Gemini response
    mock_client = MagicMock()
    mock_client_class.return_value = mock_client

    # Needs to be async
    async def mock_generate_content(*args, **kwargs):
        response = MagicMock()
        part = MagicMock()
        part.inline_data.mime_type = "audio/wav"
        part.inline_data.data = b"mocked_audio_bytes"
        response.candidates = [MagicMock()]
        response.candidates[0].content.parts = [part]
        return response

    mock_client.aio.models.generate_content.side_effect = mock_generate_content

    dialogues = [
        {"speaker": "RJ Max", "text": "Hello world!"},
        {"speaker": "RJ Luna", "text": "Space is cool."}
    ]

    synthesize_dialogue(dialogues, out_dir)

    # Verify outputs
    import glob
    files = glob.glob(os.path.join(out_dir, "*.wav"))
    assert len(files) == 2

    # Verify continuous sequencing (index check)
    files.sort()
    assert "dialogue_00000000_rj_max_" in os.path.basename(files[0])
    assert "dialogue_00000001_rj_luna_" in os.path.basename(files[1])

@patch('src.audio.tts.genai.Client')
def test_tts_queue_mocked_failure_fallback(mock_client_class, tmp_path):
    out_dir = str(tmp_path / "output")

    # Mock Gemini response to fail
    mock_client = MagicMock()
    mock_client_class.return_value = mock_client

    async def mock_generate_content_fail(*args, **kwargs):
        raise Exception("API Rate Limit Exceeded")

    mock_client.aio.models.generate_content.side_effect = mock_generate_content_fail

    dialogues = [
        {"speaker": "Caller Mike", "text": "I love this show!"}
    ]

    synthesize_dialogue(dialogues, out_dir)

    # Verify fallback txt was created
    import glob
    files = glob.glob(os.path.join(out_dir, "*.txt"))
    assert len(files) == 1
    assert "dialogue_00000000_caller_mike" in os.path.basename(files[0])

    with open(files[0], 'r') as f:
        content = f.read()
    assert content == "Caller Mike: I love this show!"

@pytest.mark.skipif(not os.environ.get("GEMINI_API_KEY"), reason="No Gemini API Key found")
def test_tts_live_api():
    # Only runs if the API key is actually set, verifying the SDK works natively
    out_dir = "tests/live_output"
    if not os.path.exists(out_dir):
        os.makedirs(out_dir)

    dialogues = [{"speaker": "RJ Dave", "text": "Testing the live API."}]
    synthesize_dialogue(dialogues, out_dir)

    import glob
    files = glob.glob(os.path.join(out_dir, "*.wav"))
    assert len(files) >= 1

    # cleanup
    for f in files:
        os.remove(f)
    os.rmdir(out_dir)
