"""
Favorites Manager - Save and manage favorite commands
"""
import json
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
FAVORITES_FILE = BASE_DIR / "config" / "favorites.json"


def save_favorite(command: str, description: str = "") -> None:
    """Save a command as favorite"""
    FAVORITES_FILE.parent.mkdir(parents=True, exist_ok=True)
    
    favorites = []
    if FAVORITES_FILE.exists():
        try:
            favorites = json.loads(FAVORITES_FILE.read_text())
        except:
            favorites = []
    
    # Check if already exists
    for fav in favorites:
        if fav["command"] == command:
            return  # Already favorited
    
    favorites.append({
        "command": command,
        "description": description,
        "created": str(Path(__file__).stat().st_mtime)
    })
    
    FAVORITES_FILE.write_text(json.dumps(favorites, indent=2, ensure_ascii=False))


def get_favorites() -> list:
    """Get all favorite commands"""
    if not FAVORITES_FILE.exists():
        return []
    
    try:
        return json.loads(FAVORITES_FILE.read_text())
    except:
        return []


def remove_favorite(command: str) -> None:
    """Remove a command from favorites"""
    favorites = get_favorites()
    favorites = [f for f in favorites if f["command"] != command]
    FAVORITES_FILE.write_text(json.dumps(favorites, indent=2, ensure_ascii=False))


def list_favorites_formatted() -> str:
    """Get formatted list of favorites for display"""
    favorites = get_favorites()
    if not favorites:
        return "No favorites saved yet."
    
    result = "📌 **FAVORITES:**\n"
    for i, fav in enumerate(favorites, 1):
        desc = f" - {fav['description']}" if fav['description'] else ""
        result += f"{i}. {fav['command']}{desc}\n"
    
    return result
