"""
J.A.R.V.I.S Auto Control - Automated repetitive mouse/keyboard control
No AI needed - simple repetitive automation
"""
import threading
import time

try:
    import pyautogui
    pyautogui.FAILSAFE = True
    _PYAUTOGUI = True
except ImportError:
    _PYAUTOGUI = False


class AutoControl:
    """Automated control without AI"""
    
    def __init__(self):
        self.active = False
        self.mode = None  # scroll, click, type, watch
        self.thread = None
        self.stop_event = None
        
    def start(self, mode="scroll", player=None):
        """Start auto control"""
        if self.active:
            return "Auto control is already active."
        
        if not _PYAUTOGUI:
            return "ERROR: pyautogui required. pip install pyautogui"
        
        self.active = True
        self.mode = mode.lower()
        self.stop_event = threading.Event()
        
        # Start the automation loop
        self.thread = threading.Thread(
            target=self._auto_loop,
            args=(player,),
            daemon=True
        )
        self.thread.start()
        
        return f"""⚡ AUTO CONTROL STARTED!

Mode: {mode.upper()}
• scroll: Auto scrolling
• click: Continuous clicking (same spot)
• watch: Mouse movement tracking

To stop: /auto stop"""
    
    def stop(self, player=None):
        """Stop auto control"""
        if not self.active:
            return "Auto control is already off."
        
        self.active = False
        if self.stop_event:
            self.stop_event.set()
        
        return "🔒 Auto control stopped."
    
    def _auto_loop(self, player):
        """Main automation loop"""
        if self.mode == "scroll":
            self._scroll_loop(player)
        elif self.mode == "click":
            self._click_loop(player)
        elif self.mode == "watch":
            self._watch_loop(player)
        
        self.active = False
        if player:
            player.write_log("⚡ Auto control finished.")
    
    def _scroll_loop(self, player):
        """Auto scrolling - keeps scrolling down"""
        scroll_count = 0
        while self.active:
            if self.stop_event and self.stop_event.is_set():
                break
            
            try:
                pyautogui.scroll(-3)  # scroll down
                scroll_count += 1
                
                # Log every 50 scrolls
                if scroll_count % 50 == 0:
                    if player:
                        player.write_log(f"📜 Scrolled {scroll_count} times...")
                
                time.sleep(2)  # wait 2 seconds between scrolls
                
            except Exception as e:
                if player:
                    player.write_log(f"ERR: {e}")
                break
    
    def _click_loop(self, player):
        """Auto clicking - keeps clicking same spot"""
        # First get click position
        try:
            x, y = pyautogui.position()
        except:
            x, y = 960, 540  # default center
        
        click_count = 0
        while self.active:
            if self.stop_event and self.stop_event.is_set():
                break
            
            try:
                pyautogui.click(x, y)
                click_count += 1
                
                if click_count % 10 == 0:
                    if player:
                        player.write_log(f"🖱️ Clicked {click_count} times...")
                
                time.sleep(1)  # wait 1 second between clicks
                
            except Exception as e:
                if player:
                    player.write_log(f"ERR: {e}")
                break
    
    def _watch_loop(self, player):
        """Watch mode - follows mouse and shows position"""
        last_pos = None
        while self.active:
            if self.stop_event and self.stop_event.is_set():
                break
            
            try:
                pos = pyautogui.position()
                
                if pos != last_pos:
                    if player:
                        player.write_log(f"👆 Mouse: {pos}")
                    last_pos = pos
                
                time.sleep(0.5)
                
            except Exception:
                break
    
    def get_status(self):
        return {
            "active": self.active,
            "mode": self.mode.upper() if self.mode else "IDLE"
        }


# Singleton
_auto_instance = None

def get_auto_control():
    global _auto_instance
    if _auto_instance is None:
        _auto_instance = AutoControl()
    return _auto_instance

def auto_control_action(parameters, player=None):
    """Handle auto control mode"""
    control = get_auto_control()
    action = parameters.get("action", "").lower() if parameters else ""
    mode = parameters.get("mode", "").lower() if parameters else "scroll"
    
    if action in ["on", "start", "baslat", "ac"]:
        return control.start(mode=mode, player=player)
    elif action in ["off", "stop", "durdur", "kapa"]:
        return control.stop(player)
    elif action in ["status", "durum"]:
        status = control.get_status()
        if status["active"]:
            return f"⚡ AUTO CONTROL: {status['mode']} ACTIVE"
        return "⚡ AUTO CONTROL OFF"
    else:
        # Toggle
        if control.active:
            return control.stop(player)
        else:
            return control.start(mode="scroll", player=player)