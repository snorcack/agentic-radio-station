import os
import yaml
from typing import Dict, Any, List

CONFIG_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config")

def load_yaml_file(filepath: str) -> Dict[str, Any]:
    if not os.path.exists(filepath):
        print(f"Warning: Configuration file not found at {filepath}")
        return {}
    with open(filepath, 'r') as f:
        return yaml.safe_load(f) or {}

def get_agent_config(agent_type: str, filename: str) -> Dict[str, Any]:
    """
    Loads an agent configuration from the specified directory.
    agent_type should be one of: 'producers', 'presenters', 'callers', 'guests'.
    """
    filepath = os.path.join(CONFIG_DIR, agent_type, filename)
    return load_yaml_file(filepath)

def get_all_agent_configs(agent_type: str) -> Dict[str, Dict[str, Any]]:
    """
    Loads all YAML configs from a specific agent directory and returns them as a dictionary mapped by filename.
    """
    directory = os.path.join(CONFIG_DIR, agent_type)
    configs = {}
    if os.path.exists(directory):
        for filename in os.listdir(directory):
            if filename.endswith(".yaml") or filename.endswith(".yml"):
                configs[filename] = get_agent_config(agent_type, filename)
    return configs

def load_programs_config() -> List[Dict[str, Any]]:
    """
    Loads the list of programs from config/programs.yaml.
    """
    filepath = os.path.join(CONFIG_DIR, "programs.yaml")
    data = load_yaml_file(filepath)
    return data.get("programs", [])
