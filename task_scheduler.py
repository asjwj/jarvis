"""
Task Scheduler
Schedules tasks to run at specific times
"""
import json
import sys
import threading
import time
import os
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any
from croniter import croniter

def get_base_dir():
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent.parent

CONFIG_DIR = get_base_dir() / "config"
SCHEDULER_CONFIG = CONFIG_DIR / "scheduler.json"

class TaskScheduler:
    """Manages scheduled tasks."""
    
    def __init__(self):
        self.config = self._load_config()
        self.tasks = self.config.get("scheduled_tasks", [])
        self.running = False
        self._worker_thread = None
        self._callbacks = {}
        
    def _load_config(self) -> Dict:
        """Load scheduler configuration."""
        try:
            with open(SCHEDULER_CONFIG, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"[TaskScheduler] Config load error: {e}")
            return {"scheduled_tasks": [], "settings": {"enabled": True}}
    
    def _save_config(self):
        """Save scheduler configuration."""
        try:
            os.makedirs(CONFIG_DIR, exist_ok=True)
            self.config["scheduled_tasks"] = self.tasks
            with open(SCHEDULER_CONFIG, "w", encoding="utf-8") as f:
                json.dump(self.config, f, indent=4, ensure_ascii=False)
        except Exception as e:
            print(f"[TaskScheduler] Config save error: {e}")
    
    def register_callback(self, task_type: str, callback):
        """Register a callback function for task execution."""
        self._callbacks[task_type] = callback
    
    def add_task(self, name: str, action: str, schedule: str, 
                 task_type: str = "command", description: str = "",
                 enabled: bool = True) -> Dict[str, Any]:
        """Add a new scheduled task."""
        # Validate schedule
        if not self._validate_schedule(schedule):
            return {"success": False, "error": "Geçersiz zamanlama formatı"}
        
        task = {
            "id": self._generate_id(),
            "name": name,
            "action": action,
            "schedule": schedule,
            "schedule_type": self._detect_schedule_type(schedule),
            "task_type": task_type,
            "description": description,
            "enabled": enabled,
            "created_at": datetime.now().isoformat(),
            "last_run": None,
            "next_run": self._calculate_next_run(schedule),
            "run_count": 0,
            "fail_count": 0
        }
        
        self.tasks.append(task)
        self._save_config()
        
        return {
            "success": True,
            "message": f"✅ Görev eklendi: {name}",
            "task_id": task["id"],
            "next_run": task["next_run"]
        }
    
    def _validate_schedule(self, schedule: str) -> bool:
        """Validate schedule format."""
        # Cron format
        if len(schedule.split()) >= 5:
            try:
                croniter(schedule)
                return True
            except:
                pass
        
        # Time format (HH:MM)
        if ":" in schedule:
            parts = schedule.split(":")
            if len(parts) == 2:
                try:
                    hour = int(parts[0])
                    minute = int(parts[1])
                    return 0 <= hour <= 23 and 0 <= minute <= 59
                except:
                    pass
        
        # Interval format (e.g., "every 5 minutes", "every hour")
        if "every" in schedule.lower():
            return True
        
        # Date-time format
        if "daily" in schedule.lower() or "weekly" in schedule.lower():
            return True
        
        return False
    
    def _detect_schedule_type(self, schedule: str) -> str:
        """Detect the type of schedule."""
        if len(schedule.split()) >= 5:
            return "cron"
        if ":" in schedule and len(schedule.split(":")) == 2:
            return "daily_time"
        if "minute" in schedule.lower():
            return "interval_minutes"
        if "hour" in schedule.lower():
            return "interval_hours"
        if "daily" in schedule.lower():
            return "daily"
        if "weekly" in schedule.lower():
            return "weekly"
        return "custom"
    
    def _calculate_next_run(self, schedule: str) -> Optional[str]:
        """Calculate next run time."""
        try:
            if len(schedule.split()) >= 5:
                cron = croniter(schedule, datetime.now())
                return cron.get_next(datetime).isoformat()
            
            if ":" in schedule:
                parts = schedule.split(":")
                hour = int(parts[0])
                minute = int(parts[1])
                
                now = datetime.now()
                next_run = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
                
                if next_run <= now:
                    next_run += timedelta(days=1)
                
                return next_run.isoformat()
            
            # Interval
            interval_match = None
            unit_match = None
            
            import re
            numbers = re.findall(r'\d+', schedule)
            if numbers:
                interval_match = int(numbers[0])
            
            if "minute" in schedule.lower():
                unit_match = "minutes"
            elif "hour" in schedule.lower():
                unit_match = "hours"
            elif "day" in schedule.lower():
                unit_match = "days"
            
            if interval_match and unit_match:
                kwargs = {unit_match: interval_match}
                next_run = datetime.now() + timedelta(**kwargs)
                return next_run.isoformat()
            
        except Exception as e:
            print(f"[TaskScheduler] Next run calc error: {e}")
        
        return None
    
    def _generate_id(self) -> str:
        """Generate unique task ID."""
        existing_ids = [t["id"] for t in self.tasks]
        i = 1
        while f"task_{i}" in existing_ids:
            i += 1
        return f"task_{i}"
    
    def get_tasks(self, enabled_only: bool = False) -> List[Dict]:
        """Get all scheduled tasks."""
        if enabled_only:
            return [t for t in self.tasks if t.get("enabled", True)]
        return self.tasks
    
    def get_task(self, task_id: str) -> Optional[Dict]:
        """Get a specific task."""
        for task in self.tasks:
            if task["id"] == task_id:
                return task
        return None
    
    def update_task(self, task_id: str, updates: Dict) -> Dict[str, Any]:
        """Update a scheduled task."""
        task = self.get_task(task_id)
        
        if not task:
            return {"success": False, "error": "Görev bulunamadı"}
        
        for key, value in updates.items():
            if key in ["name", "action", "schedule", "description", "enabled"]:
                task[key] = value
        
        # Recalculate next run if schedule changed
        if "schedule" in updates:
            task["next_run"] = self._calculate_next_run(updates["schedule"])
            task["schedule_type"] = self._detect_schedule_type(updates["schedule"])
        
        self._save_config()
        
        return {
            "success": True,
            "message": f"✅ Görev güncellendi: {task['name']}"
        }
    
    def delete_task(self, task_id: str) -> bool:
        """Delete a scheduled task."""
        original_len = len(self.tasks)
        self.tasks = [t for t in self.tasks if t["id"] != task_id]
        
        if len(self.tasks) < original_len:
            self._save_config()
            return True
        return False
    
    def toggle_task(self, task_id: str) -> Dict[str, Any]:
        """Toggle task enabled/disabled."""
        task = self.get_task(task_id)
        
        if not task:
            return {"success": False, "error": "Görev bulunamadı"}
        
        task["enabled"] = not task["enabled"]
        self._save_config()
        
        status = "etkinleştirildi" if task["enabled"] else "devre dışı bırakıldı"
        return {
            "success": True,
            "message": f"✅ Görev {status}: {task['name']}"
        }
    
    def run_task(self, task_id: str, player=None) -> Dict[str, Any]:
        """Manually run a task."""
        task = self.get_task(task_id)
        
        if not task:
            return {"success": False, "error": "Görev bulunamadı"}
        
        return self._execute_task(task, player)
    
    def _execute_task(self, task: Dict, player=None) -> Dict[str, Any]:
        """Execute a task."""
        task_type = task.get("task_type", "command")
        action = task.get("action", "")
        
        try:
            # Execute based on type
            if task_type in self._callbacks:
                result = self._callbacks[task_type](action, player)
            else:
                # Default execution
                result = self._default_execute(action, player)
            
            # Update task stats
            task["last_run"] = datetime.now().isoformat()
            task["run_count"] = task.get("run_count", 0) + 1
            task["next_run"] = self._calculate_next_run(task["schedule"])
            
            self._save_config()
            
            return {
                "success": True,
                "message": f"✅ Görev çalıştırıldı: {task['name']}",
                "result": result
            }
            
        except Exception as e:
            task["fail_count"] = task.get("fail_count", 0) + 1
            self._save_config()
            
            return {
                "success": False,
                "error": f"❌ Görev hatası: {str(e)}"
            }
    
    def _default_execute(self, action: str, player=None) -> str:
        """Default task execution."""
        if player:
            player.write_log(f"📋 Görev çalışıyor: {action}")
        return f"Görev '{action}' çalıştırıldı"
    
    def start(self, player=None):
        """Start the scheduler background worker."""
        if self.running:
            return
        
        self.running = True
        self._worker_thread = threading.Thread(target=self._worker, args=(player,), daemon=True)
        self._worker_thread.start()
        
        if player:
            player.write_log("📅 Zamanlayıcı başlatıldı")
    
    def stop(self, player=None):
        """Stop the scheduler."""
        self.running = False
        
        if player:
            player.write_log("📅 Zamanlayıcı durduruldu")
    
    def _worker(self, player=None):
        """Background worker that checks and runs tasks."""
        while self.running:
            try:
                now = datetime.now()
                
                for task in self.tasks:
                    if not task.get("enabled", True):
                        continue
                    
                    next_run_str = task.get("next_run")
                    if not next_run_str:
                        continue
                    
                    try:
                        next_run = datetime.fromisoformat(next_run_str)
                        
                        if now >= next_run:
                            self._execute_task(task, player)
                    except Exception as e:
                        print(f"[TaskScheduler] Task check error: {e}")
                
                # Sleep interval
                interval = self.config.get("settings", {}).get("check_interval_seconds", 30)
                time.sleep(interval)
                
            except Exception as e:
                print(f"[TaskScheduler] Worker error: {e}")
                time.sleep(30)
    
    def format_tasks_list(self) -> str:
        """Format tasks as readable string."""
        if not self.tasks:
            return "📭 Zamanlanmış görev yok. /schedule add ile ekleyin."
        
        lines = ["📅 **ZAMANLANMIŞ GÖREVLER:**\n"]
        
        for task in self.tasks:
            status = "✅" if task.get("enabled") else "❌"
            name = task.get("name", "İsimsiz")
            schedule = task.get("schedule", "?")
            next_run = task.get("next_run", "Bilinmiyor")
            
            if next_run and next_run != "Bilinmiyor":
                try:
                    dt = datetime.fromisoformat(next_run)
                    next_run = dt.strftime("%d.%m.%Y %H:%M")
                except:
                    pass
            
            lines.append(f"{status} **{name}**")
            lines.append(f"   Zamanlama: `{schedule}`")
            lines.append(f"   Sonraki: {next_run}")
            lines.append(f"   Çalıştırma: {task.get('run_count', 0)}x | Hata: {task.get('fail_count', 0)}")
            lines.append("")
        
        return "\n".join(lines)


# Global instance
_scheduler = None

def get_scheduler() -> TaskScheduler:
    global _scheduler
    if _scheduler is None:
        _scheduler = TaskScheduler()
    return _scheduler


def scheduler_action(parameters: dict, player=None) -> str:
    """Handle scheduler actions."""
    action = parameters.get("action", "list")
    scheduler = get_scheduler()
    
    if action == "list":
        return scheduler.format_tasks_list()
    
    elif action == "add":
        name = parameters.get("name", "")
        schedule = parameters.get("schedule", "")
        task_action = parameters.get("action", "")
        task_type = parameters.get("task_type", "command")
        description = parameters.get("description", "")
        
        if not name or not schedule:
            return "❌ İsim ve zamanlama gerekli\nÖrnek: /schedule add \"Backup\" \"0 2 * * *\" \"backup_files\""
        
        result = scheduler.add_task(
            name=name,
            action=task_action,
            schedule=schedule,
            task_type=task_type,
            description=description
        )
        
        if result.get("success"):
            return f"{result['message']}\nSonraki çalışma: {result.get('next_run', '?')}"
        return f"❌ {result.get('error')}"
    
    elif action == "delete":
        task_id = parameters.get("task_id", "")
        if not task_id:
            return "❌ Görev ID gerekli"
        
        if scheduler.delete_task(task_id):
            return f"✅ Görev silindi"
        return f"❌ Görev bulunamadı"
    
    elif action == "toggle":
        task_id = parameters.get("task_id", "")
        if not task_id:
            return "❌ Görev ID gerekli"
        
        result = scheduler.toggle_task(task_id)
        if result.get("success"):
            return result["message"]
        return f"❌ {result.get('error')}"
    
    elif action == "run":
        task_id = parameters.get("task_id", "")
        if not task_id:
            return "❌ Görev ID gerekli"
        
        result = scheduler.run_task(task_id, player)
        if result.get("success"):
            return result["message"]
        return f"❌ {result.get('error')}"
    
    elif action == "start":
        scheduler.start(player)
        return "✅ Zamanlayıcı başlatıldı"
    
    elif action == "stop":
        scheduler.stop(player)
        return "✅ Zamanlayıcı durduruldu"
    
    return f"❌ Bilinmeyen işlem: {action}"
