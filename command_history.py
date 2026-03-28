"""
Command History Manager - Stores and retrieves command history
"""
import json
from pathlib import Path
from datetime import datetime

BASE_DIR = Path(__file__).resolve().parent.parent
HISTORY_FILE = BASE_DIR / "config" / "command_history.json"


def save_command(command: str) -> None:
    """Save a command to history"""
    HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)
    
    history = []
    if HISTORY_FILE.exists():
        try:
            history = json.loads(HISTORY_FILE.read_text())
        except:
            history = []
    
    # Add new command with timestamp
    history.append({
        "command": command,
        "timestamp": datetime.now().isoformat(),
        "used_count": 1
    })
    
    # Keep last 100 commands
    history = history[-100:]
    
    HISTORY_FILE.write_text(json.dumps(history, indent=2, ensure_ascii=False))


def get_history() -> list:
    """Get all commands from history"""
    if not HISTORY_FILE.exists():
        return []
    
    try:
        return json.loads(HISTORY_FILE.read_text())
    except:
        return []


def search_history(query: str) -> list:
    """Search history by query"""
    history = get_history()
    return [h for h in history if query.lower() in h["command"].lower()]


def clear_history() -> None:
    """Clear all history"""
    if HISTORY_FILE.exists():
        HISTORY_FILE.write_text(json.dumps([], indent=2))
