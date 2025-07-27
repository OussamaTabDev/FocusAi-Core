import json
from pathlib import Path
from datetime import datetime
import logging
def save_session_data(file_path: str, session_data: dict):
    """Save session data to JSON file"""
    try:
        history_path = Path(file_path)
        history_path.parent.mkdir(exist_ok=True)
        
        history = []
        if history_path.exists():
            with open(history_path, "r") as f:
                history = json.load(f)
        
        history.append(session_data)
        
        with open(history_path, "w") as f:
            json.dump(history, f, indent=2)
    except Exception as e:
        logging.error(f"Error saving session data: {e}")
        raise