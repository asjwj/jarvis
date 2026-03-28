"""
Export Manager - Export conversations to various formats
"""
import json
from pathlib import Path
from datetime import datetime

BASE_DIR = Path(__file__).resolve().parent.parent
EXPORT_DIR = BASE_DIR / "exports"


def export_chat_txt(messages: list, filename: str = None) -> str:
    """Export chat to TXT file"""
    EXPORT_DIR.mkdir(parents=True, exist_ok=True)
    
    if filename is None:
        filename = f"chat_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    
    filepath = EXPORT_DIR / filename
    
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write("=" * 60 + "\n")
        f.write(f"J.A.R.V.I.S CHAT EXPORT\n")
        f.write(f"Exported: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write("=" * 60 + "\n\n")
        
        for msg in messages:
            role = msg.get("role", "").upper()
            content = msg.get("content", "")
            f.write(f"[{role}]\n{content}\n\n")
    
    return str(filepath)


def export_chat_json(messages: list, filename: str = None) -> str:
    """Export chat to JSON file"""
    EXPORT_DIR.mkdir(parents=True, exist_ok=True)
    
    if filename is None:
        filename = f"chat_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    
    filepath = EXPORT_DIR / filename
    
    export_data = {
        "exported_at": datetime.now().isoformat(),
        "version": "1.0",
        "messages": messages
    }
    
    filepath.write_text(json.dumps(export_data, indent=2, ensure_ascii=False))
    
    return str(filepath)


def export_chat_markdown(messages: list, filename: str = None) -> str:
    """Export chat to Markdown file"""
    EXPORT_DIR.mkdir(parents=True, exist_ok=True)
    
    if filename is None:
        filename = f"chat_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
    
    filepath = EXPORT_DIR / filename
    
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write("# J.A.R.V.I.S Chat Export\n\n")
        f.write(f"**Exported:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        f.write("---\n\n")
        
        for msg in messages:
            role = msg.get("role", "").upper()
            content = msg.get("content", "")
            
            if role == "YOU":
                f.write(f"### 👤 You\n\n{content}\n\n")
            else:
                f.write(f"### 🤖 {role}\n\n{content}\n\n")
            
            f.write("---\n\n")
    
    return str(filepath)


def list_exports() -> str:
    """List all exported files"""
    if not EXPORT_DIR.exists():
        return "No exports yet."
    
    exports = list(EXPORT_DIR.glob("chat_*"))
    if not exports:
        return "No exports found."
    
    result = "📁 **EXPORTS:**\n"
    for exp in sorted(exports, reverse=True)[:10]:  # Last 10
        size_kb = exp.stat().st_size / 1024
        result += f"• {exp.name} ({size_kb:.1f} KB)\n"
    
    return result
