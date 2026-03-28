"""
Project Context Manager
Analyzes and introduces project folders to the AI
"""
import os
import json
import sys
from pathlib import Path
from typing import Optional, Dict, List, Any
from datetime import datetime

def get_base_dir():
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent.parent

CONFIG_DIR = get_base_dir() / "config"
CONTEXT_CONFIG = CONFIG_DIR / "context.json"

class ContextManager:
    """Manages project context for AI."""
    
    def __init__(self):
        self.config = self._load_config()
        
    def _load_config(self) -> Dict:
        """Load context configuration."""
        try:
            with open(CONTEXT_CONFIG, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"[ContextManager] Config load error: {e}")
            return {
                "project_contexts": {},
                "active_context": None,
                "auto_detect": True,
                "context_settings": {
                    "max_file_size_kb": 500,
                    "include_extensions": [".py", ".js", ".json"],
                    "exclude_dirs": ["node_modules", ".git"],
                    "exclude_files": ["*.pyc"]
                }
            }
    
    def _save_config(self):
        """Save context configuration."""
        try:
            os.makedirs(CONFIG_DIR, exist_ok=True)
            with open(CONTEXT_CONFIG, "w", encoding="utf-8") as f:
                json.dump(self.config, f, indent=4, ensure_ascii=False)
        except Exception as e:
            print(f"[ContextManager] Config save error: {e}")
    
    def analyze_project(self, project_path: str) -> Dict[str, Any]:
        """Analyze a project folder and generate context summary."""
        path = Path(project_path).resolve()
        
        if not path.exists():
            return {"success": False, "error": "Path does not exist"}
        
        if not path.is_dir():
            return {"success": False, "error": "Path is not a directory"}
        
        settings = self.config.get("context_settings", {})
        exclude_dirs = set(settings.get("exclude_dirs", []))
        exclude_files = set(settings.get("exclude_files", []))
        include_exts = set(settings.get("include_extensions", []))
        max_size_kb = settings.get("max_file_size_kb", 500)
        
        structure = {
            "name": path.name,
            "path": str(path),
            "files": [],
            "dirs": [],
            "summary": "",
            "languages": {},
            "total_files": 0,
            "total_lines": 0,
            "readme_content": None,
            "package_info": None
        }
        
        try:
            for root, dirs, files in os.walk(path):
                # Filter directories
                dirs[:] = [d for d in dirs if d not in exclude_dirs]
                
                # Get relative path
                rel_root = Path(root).relative_to(path)
                
                for d in dirs:
                    structure["dirs"].append(str(rel_root / d) if str(rel_root) != "." else d)
                
                for f in files:
                    # Check exclusions
                    if any(f.endswith(ext.replace("*", "")) for ext in exclude_files):
                        continue
                    
                    file_path = Path(root) / f
                    rel_path = file_path.relative_to(path)
                    
                    # Check extension
                    ext = file_path.suffix.lower()
                    if include_exts and ext not in include_exts:
                        # Still count important files
                        if f.lower() not in ["readme.md", "readme.txt", "package.json", "requirements.txt"]:
                            continue
                    
                    # Check file size
                    try:
                        size_kb = file_path.stat().st_size / 1024
                        if size_kb > max_size_kb:
                            continue
                    except:
                        continue
                    
                    structure["total_files"] += 1
                    
                    # Read content for important files
                    file_info = {
                        "name": f,
                        "path": str(rel_path),
                        "ext": ext,
                        "size_kb": round(size_kb, 2)
                    }
                    
                    # Count lines
                    try:
                        with open(file_path, "r", encoding="utf-8", errors="ignore") as file:
                            lines = len(file.readlines())
                            file_info["lines"] = lines
                            structure["total_lines"] += lines
                            
                            # Track languages
                            if ext in [".py", ".js", ".ts", ".java", ".cpp", ".c", ".go", ".rs"]:
                                structure["languages"][ext] = structure["languages"].get(ext, 0) + lines
                    except:
                        pass
                    
                    structure["files"].append(file_info)
                    
                    # Get README content
                    if f.lower() in ["readme.md", "readme.txt", "readme"]:
                        try:
                            with open(file_path, "r", encoding="utf-8", errors="ignore") as file:
                                content = file.read(2000)
                                structure["readme_content"] = content[:500]
                        except:
                            pass
                    
                    # Get package info
                    if f == "package.json":
                        try:
                            with open(file_path, "r", encoding="utf-8") as file:
                                pkg = json.load(file)
                                structure["package_info"] = {
                                    "name": pkg.get("name", "Unknown"),
                                    "version": pkg.get("version", "?"),
                                    "dependencies": len(pkg.get("dependencies", {})),
                                    "scripts": list(pkg.get("scripts", {}).keys())[:5]
                                }
                        except:
                            pass
                
                # Limit depth
                if len(structure["dirs"]) > 50:
                    break
            
            # Generate summary
            structure["summary"] = self._generate_summary(structure)
            
            return {"success": True, "data": structure}
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _generate_summary(self, structure: Dict) -> str:
        """Generate a text summary of the project."""
        lines = []
        lines.append(f"📁 **Proje: {structure['name']}**")
        lines.append(f"📍 Yol: `{structure['path']}`")
        lines.append("")
        lines.append(f"📊 **İstatistikler:**")
        lines.append(f"- Dosya sayısı: {structure['total_files']}")
        lines.append(f"- Dizin sayısı: {len(structure['dirs'])}")
        lines.append(f"- Toplam satır: {structure['total_lines']:,}")
        lines.append("")
        
        if structure["languages"]:
            lines.append("💻 **Diller:**")
            sorted_langs = sorted(structure["languages"].items(), key=lambda x: x[1], reverse=True)
            for ext, lines_count in sorted_langs[:5]:
                lang_name = {
                    ".py": "Python", ".js": "JavaScript", ".ts": "TypeScript",
                    ".java": "Java", ".cpp": "C++", ".c": "C", ".go": "Go", ".rs": "Rust"
                }.get(ext, ext)
                lines.append(f"- {lang_name}: {lines_count:,} satır")
            lines.append("")
        
        if structure.get("readme_content"):
            lines.append("📝 **README Önizleme:**")
            lines.append(structure["readme_content"][:300] + "...")
            lines.append("")
        
        if structure.get("package_info"):
            pkg = structure["package_info"]
            lines.append("📦 **Paket Bilgisi:**")
            lines.append(f"- İsim: {pkg['name']}")
            lines.append(f"- Versiyon: {pkg['version']}")
            lines.append(f"- Bağımlılıklar: {pkg['dependencies']}")
            if pkg.get("scripts"):
                lines.append(f"- Komutlar: {', '.join(pkg['scripts'])}")
            lines.append("")
        
        # Top-level directories
        top_dirs = [d for d in structure["dirs"] if "/" not in d and "\\" not in d][:10]
        if top_dirs:
            lines.append("📂 **Ana Dizinler:**")
            for d in top_dirs:
                lines.append(f"- `{d}/`")
        
        return "\n".join(lines)
    
    def save_project_context(self, name: str, project_path: str) -> Dict[str, Any]:
        """Analyze and save a project context."""
        result = self.analyze_project(project_path)
        
        if not result.get("success"):
            return result
        
        data = result["data"]
        
        project_context = {
            "name": name,
            "path": project_path,
            "summary": data["summary"],
            "languages": data.get("languages", {}),
            "file_count": data["total_files"],
            "line_count": data["total_lines"],
            "readme": data.get("readme_content"),
            "package_info": data.get("package_info"),
            "saved_at": datetime.now().isoformat(),
            "file_tree": self._generate_file_tree(data["files"])
        }
        
        self.config["project_contexts"][name] = project_context
        self._save_config()
        
        return {
            "success": True,
            "message": f"✅ Proje '{name}' kaydedildi!",
            "summary": data["summary"]
        }
    
    def _generate_file_tree(self, files: List[Dict]) -> List[str]:
        """Generate a simplified file tree."""
        tree = []
        for f in sorted(files, key=lambda x: x["path"])[:100]:
            tree.append(f["path"])
        return tree
    
    def get_project_context(self, name: str) -> Optional[Dict]:
        """Get saved project context."""
        return self.config.get("project_contexts", {}).get(name)
    
    def list_projects(self) -> List[Dict]:
        """List all saved projects."""
        projects = self.config.get("project_contexts", {})
        return [
            {
                "name": name,
                "path": info.get("path"),
                "file_count": info.get("file_count", 0),
                "line_count": info.get("line_count", 0),
                "saved_at": info.get("saved_at"),
                "languages": info.get("languages", {})
            }
            for name, info in projects.items()
        ]
    
    def set_active_context(self, name: str) -> Dict[str, Any]:
        """Set the active project context."""
        projects = self.config.get("project_contexts", {})
        
        if name not in projects:
            return {"success": False, "error": f"Project '{name}' not found"}
        
        self.config["active_context"] = name
        self._save_config()
        
        return {
            "success": True,
            "message": f"✅ Aktif proje: {name}",
            "context": projects[name]
        }
    
    def delete_project(self, name: str) -> bool:
        """Delete a saved project context."""
        projects = self.config.get("project_contexts", {})
        
        if name in projects:
            del projects[name]
            
            if self.config.get("active_context") == name:
                self.config["active_context"] = None
            
            self._save_config()
            return True
        
        return False
    
    def format_for_ai(self, name: str) -> str:
        """Format project context for AI system prompt."""
        project = self.get_project_context(name)
        
        if not project:
            return ""
        
        lines = []
        lines.append("\n" + "="*50)
        lines.append(f"📁 PROJE BAĞLAMI: {project.get('name', name)}")
        lines.append("="*50)
        lines.append("")
        lines.append(project.get("summary", ""))
        lines.append("")
        lines.append("📄 **Dosya Yapısı:**")
        
        for f in project.get("file_tree", [])[:30]:
            lines.append(f"  - {f}")
        
        if len(project.get("file_tree", [])) > 30:
            lines.append(f"  ... ve {len(project['file_tree']) - 30} dosya daha")
        
        lines.append("")
        lines.append("="*50)
        
        return "\n".join(lines)


# Global instance
_context_manager = None

def get_context_manager() -> ContextManager:
    global _context_manager
    if _context_manager is None:
        _context_manager = ContextManager()
    return _context_manager


def context_action(parameters: dict, player=None) -> str:
    """Handle context management actions."""
    action = parameters.get("action", "list")
    manager = get_context_manager()
    
    if action == "analyze":
        path = parameters.get("path", "")
        if not path:
            return "❌ Proje yolu gerekli: /context analyze /path/to/project"
        
        result = manager.analyze_project(path)
        if result.get("success"):
            return result["data"]["summary"]
        return f"❌ {result.get('error')}"
    
    elif action == "save":
        name = parameters.get("name", "")
        path = parameters.get("path", "")
        
        if not name or not path:
            return "❌ İsim ve yol gerekli: /context save myproject /path"
        
        result = manager.save_project_context(name, path)
        if result.get("success"):
            return result["message"] + "\n\n" + result.get("summary", "")
        return f"❌ {result.get('error')}"
    
    elif action == "list":
        projects = manager.list_projects()
        if not projects:
            return "📭 Kayıtlı proje yok. /context save <isim> <yol> ile ekleyin."
        
        lines = ["📁 **KAYITLI PROJELER:**\n"]
        for p in projects:
            lines.append(f"📂 **{p['name']}**")
            lines.append(f"   Yol: `{p['path']}`")
            lines.append(f"   Dosyalar: {p['file_count']} | Satırlar: {p['line_count']:,}")
            langs = [f"{k[1:]}: {v}" for k, v in p.get("languages", {}).items()]
            if langs:
                lines.append(f"   Diller: {', '.join(langs)}")
            lines.append("")
        
        return "\n".join(lines)
    
    elif action == "set":
        name = parameters.get("name", "")
        if not name:
            return "❌ Proje ismi gerekli: /context set myproject"
        
        result = manager.set_active_context(name)
        if result.get("success"):
            return result["message"]
        return f"❌ {result.get('error')}"
    
    elif action == "delete":
        name = parameters.get("name", "")
        if not name:
            return "❌ Proje ismi gerekli: /context delete myproject"
        
        if manager.delete_project(name):
            return f"✅ '{name}' silindi"
        return f"❌ '{name}' bulunamadı"
    
    elif action == "info":
        name = parameters.get("name", "")
        project = manager.get_project_context(name)
        if project:
            return manager.format_for_ai(name)
        return f"❌ '{name}' bulunamadı"
    
    return f"❌ Bilinmeyen işlem: {action}"
