"""
J.A.R.V.I.S Agent Mode - Full Access Mode
This mode gives AI full access to all system functions and tools.
"""
import os
import json
import asyncio
import threading
from pathlib import Path
from datetime import datetime

# Config paths
def get_base_dir():
    import sys
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent.parent

BASE_DIR = get_base_dir()
CONFIG_DIR = BASE_DIR / "config"

class AgentMode:
    def __init__(self):
        self.enabled = False
        self.mode_name = "STANDARD"
        self.full_access_tools = self._get_full_access_tools()
        
    def _get_full_access_tools(self):
        """All tools available in full access mode"""
        return [
            # System Control
            "system_control",
            "file_operations",
            "process_control",
            "network_control",
            "registry_control",
            
            # AI & ML
            "code_generation",
            "code_analysis",
            "data_processing",
            "machine_learning",
            
            # Web & Internet
            "web_scraping",
            "api_integration",
            "browser_automation",
            
            # Media
            "image_processing",
            "video_processing",
            "audio_processing",
            "document_processing",
            
            # Database
            "database_operations",
            "data_analysis",
            
            # Security
            "security_scan",
            "encryption",
            
            # Automation
            "task_automation",
            "workflow_control",
        ]
    
    def enable(self, ui=None):
        """Enable full access mode"""
        self.enabled = True
        self.mode_name = "FULL ACCESS"
        
        message = """
╔══════════════════════════════════════════════════════════╗
║           🚀 FULL ACCESS MODE ACTIVE 🚀             ║
╠══════════════════════════════════════════════════════════╣
║  • All system functions enabled                      ║
║  • Advanced AI capabilities active                   ║
║  • Multi-step tasks supported                       ║
║  • File, network, database operations open          ║
║  • Automation and script execution open             ║
╚══════════════════════════════════════════════════════════╝
        """
        
        if ui:
            ui.write_log("SYS: 🚀 FULL ACCESS MODE ENABLED!")
            ui.write_log("SYS: All system functions are open.")
        
        print(message)
        return "Full Access Mode active. I can now perform all tasks!"
    
    def disable(self, ui=None):
        """Disable full access mode"""
        self.enabled = False
        self.mode_name = "STANDARD"
        
        if ui:
            ui.write_log("SYS: 🔒 SWITCHED TO STANDARD MODE")
            ui.write_log("SYS: Basic functions active.")
        
        return "Switched to standard mode. Basic functions active."
    
    def get_status(self):
        """Return mode status"""
        return {
            "enabled": self.enabled,
            "mode_name": self.mode_name,
            "tools_count": len(self.full_access_tools),
            "tools": self.full_access_tools if self.enabled else []
        }
    
    def format_status(self):
        """Return formatted status"""
        status = self.get_status()
        if status["enabled"]:
            tools_list = "\n".join([f"  ✓ {t}" for t in status["tools"][:10]])
            more = f"  ... and {len(status['tools']) - 10} more"
            return f"""🤖 **FULL ACCESS MODE STATUS:**

🔹 Mode: {status['mode_name']}
🔹 Active Tools: {status['tools_count']}
🔹 Available Tools:
{tools_list}
{more if len(status['tools']) > 10 else ''}

💡 Commands:
/agent on  - Enable full access mode
/agent off - Return to standard mode"""
        else:
            return """🤖 **MODE STATUS:**

🔹 Mode: STANDARD
🔹 Full access mode is off

💡 Commands:
/agent on  - Enable full access mode
/agent off - Return to standard mode"""

# Singleton instance
_agent_mode_instance = None

def get_agent_mode():
    global _agent_mode_instance
    if _agent_mode_instance is None:
        _agent_mode_instance = AgentMode()
    return _agent_mode_instance

def agent_mode_action(parameters, player=None):
    """Agent mode action handler"""
    agent = get_agent_mode()
    action = parameters.get("action", "").lower() if parameters else ""
    
    if action in ["on", "enable", "active", "acik", "ac"]:
        return agent.enable(player)
    elif action in ["off", "disable", "pasif", "kapa"]:
        return agent.disable(player)
    elif action in ["status", "durum", "info"]:
        return agent.format_status()
    else:
        return agent.format_status()