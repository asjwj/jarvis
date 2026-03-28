"""
Statistics Dashboard
Displays usage reports and analytics
"""
import json
import sys
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional

def get_base_dir():
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent.parent

CONFIG_DIR = get_base_dir() / "config"
STATS_CONFIG = CONFIG_DIR / "statistics.json"

class StatisticsPanel:
    """Manages statistics and usage reports."""
    
    def __init__(self):
        self.config = self._load_config()
        self._ensure_data_dir()
    
    def _ensure_data_dir(self):
        """Ensure data directory exists."""
        data_dir = get_base_dir() / "data"
        data_dir.mkdir(exist_ok=True)
    
    def _load_config(self) -> Dict:
        """Load statistics configuration."""
        try:
            with open(STATS_CONFIG, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return {
                "daily_stats": {},
                "weekly_stats": {},
                "monthly_stats": {},
                "total_stats": {
                    "total_commands": 0,
                    "total_conversations": 0,
                    "total_tasks_completed": 0,
                    "total_time_saved_minutes": 0
                },
                "model_usage": {},
                "action_stats": {},
                "last_updated": None
            }
    
    def _save_config(self):
        """Save statistics configuration."""
        try:
            self.config["last_updated"] = datetime.now().isoformat()
            with open(STATS_CONFIG, "w", encoding="utf-8") as f:
                json.dump(self.config, f, indent=4, ensure_ascii=False)
        except Exception as e:
            print(f"[Statistics] Save error: {e}")
    
    def log_action(self, action_type: str, model: str = None, 
                   success: bool = True, duration_ms: int = 0):
        """Log an action for statistics."""
        today = datetime.now().strftime("%Y-%m-%d")
        
        # Daily stats
        if "daily_stats" not in self.config:
            self.config["daily_stats"] = {}
        
        if today not in self.config["daily_stats"]:
            self.config["daily_stats"][today] = {
                "commands": 0,
                "conversations": 0,
                "tasks": 0,
                "errors": 0,
                "by_type": {},
                "by_model": {}
            }
        
        day_stats = self.config["daily_stats"][today]
        day_stats["commands"] = day_stats.get("commands", 0) + 1
        
        if not success:
            day_stats["errors"] = day_stats.get("errors", 0) + 1
        
        # By type
        by_type = day_stats.get("by_type", {})
        by_type[action_type] = by_type.get(action_type, 0) + 1
        day_stats["by_type"] = by_type
        
        # By model
        if model:
            by_model = day_stats.get("by_model", {})
            by_model[model] = by_model.get(model, 0) + 1
            day_stats["by_model"] = by_model
        
        # Total stats
        total = self.config.get("total_stats", {})
        total["total_commands"] = total.get("total_commands", 0) + 1
        self.config["total_stats"] = total
        
        # Model usage
        if model:
            model_usage = self.config.get("model_usage", {})
            model_usage[model] = model_usage.get(model, 0) + 1
            self.config["model_usage"] = model_usage
        
        # Action stats
        action_stats = self.config.get("action_stats", {})
        action_stats[action_type] = action_stats.get(action_type, 0) + 1
        self.config["action_stats"] = action_stats
        
        self._save_config()
    
    def get_daily_stats(self, days: int = 7) -> List[Dict]:
        """Get daily statistics for the past N days."""
        stats = []
        today = datetime.now()
        
        for i in range(days):
            date = (today - timedelta(days=i)).strftime("%Y-%m-%d")
            day_stats = self.config.get("daily_stats", {}).get(date, {
                "commands": 0,
                "conversations": 0,
                "tasks": 0,
                "errors": 0
            })
            day_stats["date"] = date
            stats.append(day_stats)
        
        return stats
    
    def get_summary(self, period: str = "week") -> Dict:
        """Get summary statistics."""
        if period == "day":
            days = 1
        elif period == "week":
            days = 7
        elif period == "month":
            days = 30
        else:
            days = 7
        
        daily = self.get_daily_stats(days)
        
        total_commands = sum(d.get("commands", 0) for d in daily)
        total_errors = sum(d.get("errors", 0) for d in daily)
        
        # Most used actions
        all_actions = {}
        for d in daily:
            for action, count in d.get("by_type", {}).items():
                all_actions[action] = all_actions.get(action, 0) + count
        
        top_actions = sorted(all_actions.items(), key=lambda x: x[1], reverse=True)[:5]
        
        # Most used model
        all_models = {}
        for d in daily:
            for model, count in d.get("by_model", {}).items():
                all_models[model] = all_models.get(model, 0) + count
        
        top_models = sorted(all_models.items(), key=lambda x: x[1], reverse=True)[:3]
        
        return {
            "period": period,
            "days": days,
            "total_commands": total_commands,
            "total_errors": total_errors,
            "success_rate": round((total_commands - total_errors) / total_commands * 100, 1) if total_commands > 0 else 100,
            "avg_per_day": round(total_commands / days, 1),
            "top_actions": top_actions,
            "top_models": top_models,
            "daily_breakdown": daily
        }
    
    def get_total_stats(self) -> Dict:
        """Get all-time statistics."""
        return self.config.get("total_stats", {
            "total_commands": 0,
            "total_conversations": 0,
            "total_tasks_completed": 0,
            "total_time_saved_minutes": 0
        })
    
    def format_dashboard(self) -> str:
        """Format statistics as a dashboard string."""
        summary = self.get_summary("week")
        total = self.get_total_stats()
        
        lines = []
        lines.append("╔══════════════════════════════════════════════════╗")
        lines.append("║          📊 J.A.R.V.I.S İSTATİSTİK PANELİ        ║")
        lines.append("╠══════════════════════════════════════════════════╣")
        lines.append("")
        lines.append("📅 **HAFTALIK ÖZET**")
        lines.append(f"   ├─ Toplam komut: {summary['total_commands']}")
        lines.append(f"   ├─ Ortalama/gün: {summary['avg_per_day']}")
        lines.append(f"   ├─ Başarı oranı: {summary['success_rate']}%")
        lines.append(f"   └─ Hata sayısı: {summary['total_errors']}")
        lines.append("")
        lines.append("📈 **TÜM ZAMANLAR**")
        lines.append(f"   ├─ Toplam komut: {total.get('total_commands', 0):,}")
        lines.append(f"   └─ Tamamlanan görev: {total.get('total_tasks_completed', 0):,}")
        lines.append("")
        
        if summary.get("top_actions"):
            lines.append("🏆 **EN ÇOK KULLANILAN**")
            for action, count in summary["top_actions"][:3]:
                lines.append(f"   • {action}: {count}")
            lines.append("")
        
        if summary.get("top_models"):
            lines.append("🤖 **MODEL KULLANIMI**")
            for model, count in summary["top_models"]:
                lines.append(f"   • {model}: {count}")
            lines.append("")
        
        lines.append("╚══════════════════════════════════════════════════╝")
        
        return "\n".join(lines)
    
    def format_weekly_chart(self) -> str:
        """Format weekly data as ASCII chart."""
        daily = self.get_daily_stats(7)
        
        lines = ["📊 **HAFTALIK AKTİVİTE**\n"]
        
        # Find max for scaling
        max_val = max(d.get("commands", 0) for d in daily) if daily else 1
        if max_val == 0:
            max_val = 1
        
        chart_height = 6
        
        # Draw chart
        for level in range(chart_height, 0, -1):
            threshold = (max_val / chart_height) * level
            row = f"   │ "
            for d in daily:
                val = d.get("commands", 0)
                bar = "█" if val >= threshold else "░"
                row += f"{bar:^6}"
            lines.append(row)
        
        # X-axis
        lines.append("   └─" + "─" * 42)
        
        # Labels
        labels = ""
        for d in daily:
            day = datetime.strptime(d["date"], "%Y-%m-%d").strftime("%a")
            labels += f"{day:^6}"
        lines.append(f"     {labels}")
        
        # Values
        values = ""
        for d in daily:
            val = d.get("commands", 0)
            values += f"{val:^6}"
        lines.append(f"     {values}")
        
        return "\n".join(lines)
    
    def get_model_comparison(self) -> str:
        """Get model comparison statistics."""
        model_usage = self.config.get("model_usage", {})
        
        if not model_usage:
            return "📊 Model kullanım verisi yok."
        
        total = sum(model_usage.values())
        
        lines = ["🤖 **MODEL KARŞILAŞTIRMASI**\n"]
        sorted_models = sorted(model_usage.items(), key=lambda x: x[1], reverse=True)
        
        max_count = max(model_usage.values()) if model_usage else 1
        bar_max = 20
        
        for model, count in sorted_models:
            percentage = (count / total * 100) if total > 0 else 0
            bar_len = int((count / max_count) * bar_max) if max_count > 0 else 0
            bar = "█" * bar_len + "░" * (bar_max - bar_len)
            lines.append(f"{model[:10]:10} │{bar}│ {count:3} ({percentage:5.1f}%)")
        
        return "\n".join(lines)
    
    def get_action_breakdown(self) -> str:
        """Get action type breakdown."""
        action_stats = self.config.get("action_stats", {})
        
        if not action_stats:
            return "📋 İşlem verisi yok."
        
        total = sum(action_stats.values())
        
        lines = ["📋 **İŞLEM TÜRÜ DAĞILIMI**\n"]
        sorted_actions = sorted(action_stats.items(), key=lambda x: x[1], reverse=True)
        
        max_count = max(action_stats.values()) if action_stats else 1
        bar_max = 20
        
        for action, count in sorted_actions[:10]:
            percentage = (count / total * 100) if total > 0 else 0
            bar_len = int((count / max_count) * bar_max) if max_count > 0 else 0
            bar = "█" * bar_len + "░" * (bar_max - bar_len)
            lines.append(f"{action[:15]:15} │{bar}│ {count:3} ({percentage:5.1f}%)")
        
        return "\n".join(lines)
    
    def reset_daily_stats(self, date: str = None):
        """Reset daily stats for a specific date or today."""
        if date is None:
            date = datetime.now().strftime("%Y-%m-%d")
        
        if date in self.config.get("daily_stats", {}):
            del self.config["daily_stats"][date]
            self._save_config()
            return True
        return False
    
    def export_stats(self) -> Dict:
        """Export all statistics as a dictionary."""
        return {
            "exported_at": datetime.now().isoformat(),
            "config": self.config,
            "summary_week": self.get_summary("week"),
            "summary_month": self.get_summary("month"),
            "total": self.get_total_stats()
        }


# Global instance
_stats = None

def get_statistics() -> StatisticsPanel:
    global _stats
    if _stats is None:
        _stats = StatisticsPanel()
    return _stats


def stats_action(parameters: dict, player=None) -> str:
    """Handle statistics actions."""
    action = parameters.get("action", "dashboard")
    stats = get_statistics()
    
    if action == "dashboard":
        return stats.format_dashboard()
    
    elif action == "chart":
        return stats.format_weekly_chart()
    
    elif action == "models":
        return stats.get_model_comparison()
    
    elif action == "actions":
        return stats.get_action_breakdown()
    
    elif action == "summary":
        period = parameters.get("period", "week")
        summary = stats.get_summary(period)
        
        lines = [f"📊 **{period.upper()} ÖZETİ**\n"]
        lines.append(f"Toplam komut: {summary['total_commands']}")
        lines.append(f"Başarı oranı: {summary['success_rate']}%")
        lines.append(f"Ortalama/gün: {summary['avg_per_day']}")
        
        return "\n".join(lines)
    
    elif action == "export":
        export = stats.export_stats()
        return f"📤 İstatistikler dışa aktarıldı: {len(str(export))} bytes"
    
    elif action == "reset":
        if stats.reset_daily_stats():
            return "✅ Günlük istatistikler sıfırlandı"
        return "❌ Sıfırlanacak veri bulunamadı"
    
    return f"❌ Bilinmeyen işlem: {action}"
