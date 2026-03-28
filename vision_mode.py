"""
J.A.R.V.I.S Vision Mode - Screen viewing and mouse control permission
"""
from pathlib import Path

def get_base_dir():
    import sys
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent.parent

class VisionMode:
    def __init__(self):
        self.enabled = False
        self.mode_name = "BLIND"
        
    def enable(self, ui=None):
        self.enabled = True
        self.mode_name = "VISION ACTIVE"
        
        message = """
╔══════════════════════════════════════════════════════════╗
║           👁️ VISION MODE ACTIVE 👁️                  ║
╠══════════════════════════════════════════════════════════╣
║  • Screen capture enabled                           ║
║  • Mouse control enabled                            ║
║  • Click and movement enabled                        ║
║  • Keyboard control enabled                          ║
╚══════════════════════════════════════════════════════════╝
        """
        
        if ui:
            ui.write_log("SYS: 👁️ VISION MODE ENABLED!")
            ui.write_log("SYS: Screen capture and mouse control active.")
        
        print(message)
        return "Vision Mode active! I can now see the screen and control the mouse."
    
    def disable(self, ui=None):
        self.enabled = False
        self.mode_name = "BLIND"
        
        if ui:
            ui.write_log("SYS: 🔒 VISION MODE DISABLED")
            ui.write_log("SYS: Screen capture and mouse control off.")
        
        return "Vision Mode disabled. Screen viewing and mouse control off."
    
    def get_status(self):
        return {
            "enabled": self.enabled,
            "mode_name": self.mode_name
        }
    
    def format_status(self):
        status = self.get_status()
        if status["enabled"]:
            return """👁️ **VISION MODE STATUS:**

🔹 Mode: VISION ACTIVE
🔹 Screen capture: ACTIVE
🔹 Mouse control: ACTIVE
🔹 Keyboard control: ACTIVE

💡 Commands:
/vision on  - Enable vision mode
/vision off - Disable vision mode"""
        else:
            return """👁️ **VISION MODE STATUS:**

🔹 Mode: DISABLED
🔹 Screen capture: OFF
🔹 Mouse control: OFF

💡 Commands:
/vision on  - Enable vision mode (to see screen and control mouse)
/vision off - Disable vision mode"""

# Singleton
_vision_mode_instance = None

def get_vision_mode():
    global _vision_mode_instance
    if _vision_mode_instance is None:
        _vision_mode_instance = VisionMode()
    return _vision_mode_instance

def vision_mode_action(parameters, player=None):
    """Vision mode action handler"""
    vision = get_vision_mode()
    action = parameters.get("action", "").lower() if parameters else ""
    
    if action in ["on", "enable", "acik", "ac"]:
        return vision.enable(player)
    elif action in ["off", "disable", "kapali", "kapa"]:
        return vision.disable(player)
    elif action in ["status", "durum", "info"]:
        return vision.format_status()
    else:
        return vision.format_status()