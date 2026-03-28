"""
Database Integration for Persistent Storage
Uses SQLite for local data storage
"""
import json
import sqlite3
import os
import sys
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, List, Any

def get_base_dir():
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent.parent

DATA_DIR = get_base_dir() / "data"
DB_PATH = DATA_DIR / "jarvis_data.db"

class Database:
    """SQLite database manager for JARVIS."""
    
    def __init__(self):
        self.conn = None
        self._ensure_data_dir()
        self._connect()
        self._init_tables()
    
    def _ensure_data_dir(self):
        """Ensure data directory exists."""
        os.makedirs(DATA_DIR, exist_ok=True)
    
    def _connect(self):
        """Connect to the database."""
        try:
            self.conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
            self.conn.row_factory = sqlite3.Row
        except Exception as e:
            print(f"[Database] Connection error: {e}")
    
    def _init_tables(self):
        """Initialize database tables."""
        if not self.conn:
            return
        
        cursor = self.conn.cursor()
        
        # Usage Statistics
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS usage_stats (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                action_type TEXT NOT NULL,
                model_used TEXT,
                duration_ms INTEGER DEFAULT 0,
                success INTEGER DEFAULT 1,
                metadata TEXT
            )
        """)
        
        # Conversation History
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS conversation_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                user_message TEXT NOT NULL,
                ai_response TEXT,
                model TEXT,
                tokens_used INTEGER DEFAULT 0,
                metadata TEXT
            )
        """)
        
        # Scheduled Tasks (backup for task_scheduler)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS scheduled_tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                action TEXT NOT NULL,
                schedule TEXT NOT NULL,
                schedule_type TEXT DEFAULT 'daily',
                task_type TEXT DEFAULT 'command',
                description TEXT,
                enabled INTEGER DEFAULT 1,
                created_at TEXT NOT NULL,
                last_run TEXT,
                next_run TEXT,
                run_count INTEGER DEFAULT 0,
                fail_count INTEGER DEFAULT 0
            )
        """)
        
        # Favorites
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS favorites (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                command TEXT UNIQUE NOT NULL,
                description TEXT,
                usage_count INTEGER DEFAULT 0,
                last_used TEXT,
                created_at TEXT NOT NULL
            )
        """)
        
        # Projects
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS projects (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                path TEXT UNIQUE NOT NULL,
                description TEXT,
                context_summary TEXT,
                languages TEXT,
                file_count INTEGER DEFAULT 0,
                line_count INTEGER DEFAULT 0,
                created_at TEXT NOT NULL,
                last_accessed TEXT
            )
        """)
        
        # Settings
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT,
                updated_at TEXT NOT NULL
            )
        """)
        
        self.conn.commit()
    
    def log_usage(self, action_type: str, model_used: str = None, 
                  duration_ms: int = 0, success: bool = True, 
                  metadata: Dict = None) -> int:
        """Log an action usage."""
        if not self.conn:
            return -1
        
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO usage_stats (timestamp, action_type, model_used, duration_ms, success, metadata)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            datetime.now().isoformat(),
            action_type,
            model_used,
            duration_ms,
            1 if success else 0,
            json.dumps(metadata) if metadata else None
        ))
        self.conn.commit()
        return cursor.lastrowid
    
    def log_conversation(self, user_message: str, ai_response: str = None,
                        model: str = None, tokens_used: int = 0,
                        metadata: Dict = None) -> int:
        """Log a conversation."""
        if not self.conn:
            return -1
        
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO conversation_history 
            (timestamp, user_message, ai_response, model, tokens_used, metadata)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            datetime.now().isoformat(),
            user_message,
            ai_response,
            model,
            tokens_used,
            json.dumps(metadata) if metadata else None
        ))
        self.conn.commit()
        return cursor.lastrowid
    
    def get_usage_stats(self, days: int = 7, action_type: str = None) -> List[Dict]:
        """Get usage statistics."""
        if not self.conn:
            return []
        
        cursor = self.conn.cursor()
        
        query = "SELECT * FROM usage_stats WHERE timestamp >= datetime('now', ?)"
        params = [f"-{days} days"]
        
        if action_type:
            query += " AND action_type = ?"
            params.append(action_type)
        
        query += " ORDER BY timestamp DESC"
        
        cursor.execute(query, params)
        return [dict(row) for row in cursor.fetchall()]
    
    def get_usage_summary(self, days: int = 7) -> Dict:
        """Get usage summary statistics."""
        if not self.conn:
            return {}
        
        cursor = self.conn.cursor()
        
        # Total actions
        cursor.execute("""
            SELECT COUNT(*) as total, 
                   SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) as successful,
                   AVG(duration_ms) as avg_duration
            FROM usage_stats 
            WHERE timestamp >= datetime('now', ?)
        """, [f"-{days} days"])
        
        total_row = cursor.fetchone()
        
        # Actions by type
        cursor.execute("""
            SELECT action_type, COUNT(*) as count
            FROM usage_stats 
            WHERE timestamp >= datetime('now', ?)
            GROUP BY action_type
            ORDER BY count DESC
        """, [f"-{days} days"])
        
        by_type = {row["action_type"]: row["count"] for row in cursor.fetchall()}
        
        # Actions by model
        cursor.execute("""
            SELECT model_used, COUNT(*) as count
            FROM usage_stats 
            WHERE timestamp >= datetime('now', ?) AND model_used IS NOT NULL
            GROUP BY model_used
            ORDER BY count DESC
        """, [f"-{days} days"])
        
        by_model = {row["model_used"]: row["count"] for row in cursor.fetchall()}
        
        # Daily activity
        cursor.execute("""
            SELECT DATE(timestamp) as date, COUNT(*) as count
            FROM usage_stats 
            WHERE timestamp >= datetime('now', ?)
            GROUP BY DATE(timestamp)
            ORDER BY date
        """, [f"-{days} days"])
        
        daily = [(row["date"], row["count"]) for row in cursor.fetchall()]
        
        return {
            "total": total_row["total"] or 0,
            "successful": total_row["successful"] or 0,
            "failed": (total_row["total"] or 0) - (total_row["successful"] or 0),
            "avg_duration_ms": round(total_row["avg_duration"] or 0, 2),
            "by_type": by_type,
            "by_model": by_model,
            "daily": daily
        }
    
    def get_conversations(self, limit: int = 50, search: str = None) -> List[Dict]:
        """Get conversation history."""
        if not self.conn:
            return []
        
        cursor = self.conn.cursor()
        
        query = "SELECT * FROM conversation_history"
        params = []
        
        if search:
            query += " WHERE user_message LIKE ? OR ai_response LIKE ?"
            params = [f"%{search}%", f"%{search}%"]
        
        query += " ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)
        
        cursor.execute(query, params)
        return [dict(row) for row in cursor.fetchall()]
    
    def save_favorite(self, command: str, description: str = "") -> bool:
        """Save a favorite command."""
        if not self.conn:
            return False
        
        cursor = self.conn.cursor()
        try:
            cursor.execute("""
                INSERT OR REPLACE INTO favorites (command, description, usage_count, last_used, created_at)
                VALUES (?, ?, 
                    COALESCE((SELECT usage_count FROM favorites WHERE command = ?), 0),
                    ?, ?)
            """, (command, description, command, datetime.now().isoformat(), datetime.now().isoformat()))
            self.conn.commit()
            return True
        except:
            return False
    
    def get_favorites(self) -> List[Dict]:
        """Get all favorites."""
        if not self.conn:
            return []
        
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM favorites ORDER BY usage_count DESC")
        return [dict(row) for row in cursor.fetchall()]
    
    def increment_favorite_usage(self, command: str):
        """Increment favorite usage count."""
        if not self.conn:
            return
        
        cursor = self.conn.cursor()
        cursor.execute("""
            UPDATE favorites 
            SET usage_count = usage_count + 1, last_used = ?
            WHERE command = ?
        """, (datetime.now().isoformat(), command))
        self.conn.commit()
    
    def delete_favorite(self, command: str) -> bool:
        """Delete a favorite."""
        if not self.conn:
            return False
        
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM favorites WHERE command = ?", (command,))
        self.conn.commit()
        return cursor.rowcount > 0
    
    def save_project(self, name: str, path: str, description: str = "",
                    context_summary: str = "", languages: Dict = None,
                    file_count: int = 0, line_count: int = 0) -> bool:
        """Save a project."""
        if not self.conn:
            return False
        
        cursor = self.conn.cursor()
        try:
            cursor.execute("""
                INSERT OR REPLACE INTO projects 
                (name, path, description, context_summary, languages, file_count, line_count, created_at, last_accessed)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                name, path, description, context_summary,
                json.dumps(languages) if languages else None,
                file_count, line_count,
                datetime.now().isoformat(), datetime.now().isoformat()
            ))
            self.conn.commit()
            return True
        except Exception as e:
            print(f"[Database] Save project error: {e}")
            return False
    
    def get_projects(self) -> List[Dict]:
        """Get all projects."""
        if not self.conn:
            return []
        
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM projects ORDER BY last_accessed DESC")
        results = []
        for row in cursor.fetchall():
            d = dict(row)
            if d.get("languages"):
                d["languages"] = json.loads(d["languages"])
            results.append(d)
        return results
    
    def save_setting(self, key: str, value: Any):
        """Save a setting."""
        if not self.conn:
            return
        
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO settings (key, value, updated_at)
            VALUES (?, ?, ?)
        """, (key, json.dumps(value), datetime.now().isoformat()))
        self.conn.commit()
    
    def get_setting(self, key: str, default: Any = None) -> Any:
        """Get a setting."""
        if not self.conn:
            return default
        
        cursor = self.conn.cursor()
        cursor.execute("SELECT value FROM settings WHERE key = ?", (key,))
        row = cursor.fetchone()
        if row:
            try:
                return json.loads(row["value"])
            except:
                return row["value"]
        return default
    
    def close(self):
        """Close database connection."""
        if self.conn:
            self.conn.close()


# Global instance
_db = None

def get_database() -> Database:
    global _db
    if _db is None:
        _db = Database()
    return _db


def database_action(parameters: dict, player=None) -> str:
    """Handle database actions."""
    action = parameters.get("action", "stats")
    db = get_database()
    
    if action == "stats":
        summary = db.get_usage_summary(days=7)
        
        lines = ["📊 **KULLANIM İSTATİSTİKLERİ (7 GÜN):**\n"]
        lines.append(f"📈 Toplam işlem: {summary['total']}")
        lines.append(f"✅ Başarılı: {summary['successful']}")
        lines.append(f"❌ Başarısız: {summary['failed']}")
        lines.append(f"⏱️ Ortalama süre: {summary['avg_duration_ms']:.0f}ms")
        lines.append("")
        
        if summary.get("by_type"):
            lines.append("📋 **İşlem Türlerine Göre:**")
            for atype, count in summary["by_type"].items():
                lines.append(f"  • {atype}: {count}")
            lines.append("")
        
        if summary.get("by_model"):
            lines.append("🤖 **Model Kullanımı:**")
            for model, count in summary["by_model"].items():
                lines.append(f"  • {model}: {count}")
        
        return "\n".join(lines)
    
    elif action == "history":
        limit = parameters.get("limit", 20)
        conversations = db.get_conversations(limit=limit)
        
        if not conversations:
            return "📭 Sohbet geçmişi boş."
        
        lines = ["💬 **SON SOHBETLER:**\n"]
        for i, conv in enumerate(conversations[:10], 1):
            timestamp = conv.get("timestamp", "")[:16]
            msg = conv.get("user_message", "")[:50]
            lines.append(f"{i}. [{timestamp}] {msg}...")
        
        return "\n".join(lines)
    
    elif action == "favorites":
        favorites = db.get_favorites()
        
        if not favorites:
            return "📭 Kayıtlı favori yok."
        
        lines = ["⭐ **FAVORİ KOMUTLAR:**\n"]
        for fav in favorites:
            lines.append(f"📌 {fav['command']}")
            lines.append(f"   Kullanım: {fav['usage_count']}x | Son: {fav.get('last_used', 'Hiç')[:16]}")
        
        return "\n".join(lines)
    
    elif action == "clear":
        return "⚠️ Veri silme işlemi güvenlik nedeniyle devre dışı. Elle silmek için veritabanını silebilirsiniz."
    
    return f"❌ Bilinmeyen işlem: {action}"
