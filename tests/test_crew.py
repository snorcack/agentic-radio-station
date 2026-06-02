import os
import pytest
from unittest.mock import patch, MagicMock
from src.agents.crew import run_show_pipeline

@patch('src.agents.crew.Crew')
def test_crewai_pipeline_compilation(mock_crew_class):
    # Setup mock crew instance
    mock_crew_instance = MagicMock()
    mock_crew_class.return_value = mock_crew_instance
    mock_crew_instance.kickoff.return_value = "Mocked Dialog Output"

    # Run pipeline
    result = run_show_pipeline(theme="Space Travel", presenter_file="luna.yaml", caller_id="Alien123")

    # Verify crew was compiled correctly
    assert result == "Mocked Dialog Output"
    mock_crew_class.assert_called_once()
    mock_crew_instance.kickoff.assert_called_once()

    # Inspect arguments passed to Crew()
    _, kwargs = mock_crew_class.call_args
    agents = kwargs.get('agents', [])
    assert len(agents) == 3
    assert agents[0].role == 'Producer Orchestrator'
    assert agents[1].role == 'Radio Jockey'
    assert agents[2].role == 'Random Fake Caller'
    assert 'Alien123' in agents[2].backstory
    assert kwargs.get('memory') is True

def test_unknown_rj_exception():
    with pytest.raises(ValueError) as exc:
        run_show_pipeline(theme="Tech", presenter_file="unknown.yaml")
    assert "Unknown presenter config" in str(exc.value)

@pytest.mark.skipif(not os.environ.get("GEMINI_API_KEY"), reason="No Gemini API Key found")
def test_crewai_live_api():
    # Only runs if API key is provided
    result = run_show_pipeline(theme="Testing Live Run", presenter_file="max.yaml", caller_id="LiveTester")
    # Verify we get some string output back
    assert isinstance(result, str)
    assert len(result) > 10
