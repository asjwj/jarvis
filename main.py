import pyaudio
import asyncio
import threading
import json
import re
import sys
import traceback
import os
from pathlib import Path

import pyaudio
from google import genai
from google.genai import types
import time 
from ui import JarvisUI
from memory.memory_manager import load_memory, update_memory, format_memory_for_prompt

from agent.task_queue import get_queue

from actions.flight_finder import flight_finder
from actions.open_app         import open_app
from actions.weather_report   import weather_action
from actions.send_message     import send_message
from actions.reminder         import reminder
from actions.computer_settings import computer_settings
from actions.screen_processor import screen_process
from actions.youtube_video    import youtube_video
from actions.cmd_control      import cmd_control
from actions.desktop          import desktop_control
from actions.browser_control  import browser_control
from actions.file_controller  import file_controller
from actions.code_helper      import code_helper
from actions.dev_agent        import dev_agent
from actions.web_search       import web_search as web_search_action
from actions.computer_control import computer_control
from actions.command_history import save_command, search_history, get_history
from actions.favorites_manager import save_favorite, get_favorites, remove_favorite, list_favorites_formatted
from actions.export_manager import export_chat_txt, export_chat_markdown, list_exports

def get_base_dir():
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent

BASE_DIR        = get_base_dir()
API_CONFIG_PATH = BASE_DIR / "config" / "api_keys.json"
PROMPT_PATH     = BASE_DIR / "core" / "prompt.txt"
LIVE_MODEL          = "models/gemini-2.5-flash-native-audio-preview-12-2025"
FORMAT              = pyaudio.paInt16
CHANNELS            = 1
SEND_SAMPLE_RATE    = 16000
RECEIVE_SAMPLE_RATE = 24000
CHUNK_SIZE          = 1024

pya = pyaudio.PyAudio()

def _get_api_key() -> str:
    env_key = os.environ.get("GEMINI_API_KEY")
    if env_key:
        return env_key.strip()

    try:
        with open(API_CONFIG_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
            key = data.get("gemini_api_key") or data.get("api_key")
            if key:
                return key.strip()
    except FileNotFoundError:
        print(f"[JARVIS] ⚠️  API config not found: {API_CONFIG_PATH}")
    except json.JSONDecodeError:
        print("[JARVIS] ⚠️  Invalid JSON in api_keys.json")

    raise RuntimeError(
        "Gemini API key not found. Set GEMINI_API_KEY env var or config/api_keys.json."
    )

def _load_system_prompt() -> str:
    try:
        return PROMPT_PATH.read_text(encoding="utf-8")
    except Exception:
        return (
            "You are JARVIS, Tony Stark's AI assistant. "
            "Be concise, direct, and always use the provided tools to complete tasks. "
            "Never simulate or guess results — always call the appropriate tool."
        )

_memory_turn_counter  = 0
_memory_turn_lock     = threading.Lock()
_MEMORY_EVERY_N_TURNS = 5
_last_memory_input    = ""


def _update_memory_async(user_text: str, jarvis_text: str) -> None:
    global _memory_turn_counter, _last_memory_input

    with _memory_turn_lock:
        _memory_turn_counter += 1
        current_count = _memory_turn_counter

    if current_count % _MEMORY_EVERY_N_TURNS != 0:
        return

    text = user_text.strip()
    if len(text) < 10:
        return
    if text == _last_memory_input:
        return
    _last_memory_input = text

    try:
        import google.generativeai as genai
        genai.configure(api_key=_get_api_key())
        model = genai.GenerativeModel("gemini-2.5-flash-lite")

        check = model.generate_content(
            f"Does this message contain personal facts about the user "
            f"(name, age, city, job, hobby, relationship, birthday, preference)? "
            f"Reply only YES or NO.\n\nMessage: {text[:300]}"
        )
        if "YES" not in check.text.upper():
            return

        raw = model.generate_content(
            f"Extract personal facts from this message. Any language.\n"
            f"Return ONLY valid JSON or {{}} if nothing found.\n"
            f"Extract: name, age, birthday, city, job, hobbies, preferences, relationships, language.\n"
            f"Skip: weather, reminders, search results, commands.\n\n"
            f"Format:\n"
            f'{{"identity":{{"name":{{"value":"..."}}}}}}, '
            f'"preferences":{{"hobby":{{"value":"..."}}}}, '
            f'"notes":{{"job":{{"value":"..."}}}}}}\n\n'
            f"Message: {text[:500]}\n\nJSON:"
        ).text.strip()

        raw = re.sub(r"```(?:json)?", "", raw).strip().rstrip("`").strip()
        if not raw or raw == "{}":
            return

        data = json.loads(raw)
        if data:
            update_memory(data)
            print(f"[Memory] ✅ Updated: {list(data.keys())}")

    except json.JSONDecodeError:
        pass
    except Exception as e:
        if "429" not in str(e):
            print(f"[Memory] ⚠️ {e}")


TOOL_DECLARATIONS = [
    {"name": "open_app", "description": "Opens any application on the Windows computer.", "parameters": {"type": "OBJECT", "properties": {"app_name": {"type": "STRING", "description": "Exact name of the application"}}, "required": ["app_name"]}},
    {"name": "web_search", "description": "Searches the web for any information.", "parameters": {"type": "OBJECT", "properties": {"query": {"type": "STRING"}}, "required": ["query"]}},
    {"name": "weather_report", "description": "Gets real-time weather information.", "parameters": {"type": "OBJECT", "properties": {"city": {"type": "STRING"}}, "required": ["city"]}},
    {"name": "send_message", "description": "Sends a text message.", "parameters": {"type": "OBJECT", "properties": {"receiver": {"type": "STRING"}, "message_text": {"type": "STRING"}, "platform": {"type": "STRING"}}, "required": ["receiver", "message_text", "platform"]}},
    {"name": "reminder", "description": "Sets a timed reminder.", "parameters": {"type": "OBJECT", "properties": {"date": {"type": "STRING"}, "time": {"type": "STRING"}, "message": {"type": "STRING"}}, "required": ["date", "time", "message"]}},
    {"name": "youtube_video", "description": "Controls YouTube.", "parameters": {"type": "OBJECT", "properties": {"action": {"type": "STRING"}, "query": {"type": "STRING"}}, "required": []}},
    {"name": "screen_process", "description": "Captures and analyzes screen.", "parameters": {"type": "OBJECT", "properties": {"text": {"type": "STRING"}}, "required": ["text"]}},
    {"name": "computer_settings", "description": "Controls the computer.", "parameters": {"type": "OBJECT", "properties": {"action": {"type": "STRING"}, "description": {"type": "STRING"}}, "required": []}},
    {"name": "browser_control", "description": "Controls the web browser.", "parameters": {"type": "OBJECT", "properties": {"action": {"type": "STRING"}, "url": {"type": "STRING"}}, "required": ["action"]}},
    {"name": "file_controller", "description": "Manages files and folders.", "parameters": {"type": "OBJECT", "properties": {"action": {"type": "STRING"}, "path": {"type": "STRING"}}, "required": ["action"]}},
    {"name": "cmd_control", "description": "Runs CMD commands.", "parameters": {"type": "OBJECT", "properties": {"task": {"type": "STRING"}}, "required": ["task"]}},
    {"name": "desktop_control", "description": "Controls the desktop.", "parameters": {"type": "OBJECT", "properties": {"action": {"type": "STRING"}}, "required": ["action"]}},
    {"name": "code_helper", "description": "Writes, edits, runs code.", "parameters": {"type": "OBJECT", "properties": {"action": {"type": "STRING"}, "description": {"type": "STRING"}}, "required": ["action"]}},
    {"name": "dev_agent", "description": "Builds complete projects.", "parameters": {"type": "OBJECT", "properties": {"description": {"type": "STRING"}}, "required": ["description"]}},
    {"name": "agent_task", "description": "Executes complex multi-step tasks.", "parameters": {"type": "OBJECT", "properties": {"goal": {"type": "STRING"}, "priority": {"type": "STRING"}}, "required": ["goal"]}},
    {"name": "computer_control", "description": "CONTROLS MOUSE AND KEYBOARD - click (x,y), move (x,y), type (text), smart_type (text), press (key), scroll (direction), hotkey (keys), screenshot, screen_find (description), screen_click (description). ALWAYS use this for mouse/keyboard tasks!", "parameters": {"type": "OBJECT", "properties": {"action": {"type": "STRING", "description": "click|move|type|smart_type|press|scroll|hotkey|screenshot|screen_find|screen_click"}, "x": {"type": "NUMBER"}, "y": {"type": "NUMBER"}, "text": {"type": "STRING"}, "key": {"type": "STRING"}, "direction": {"type": "STRING"}, "keys": {"type": "STRING"}, "description": {"type": "STRING"}}, "required": ["action"]}},
    {"name": "flight_finder", "description": "Searches for flights.", "parameters": {"type": "OBJECT", "properties": {"origin": {"type": "STRING"}, "destination": {"type": "STRING"}, "date": {"type": "STRING"}}, "required": ["origin", "destination", "date"]}}
]

class JarvisLive:

    def __init__(self, ui: JarvisUI):
        self.ui             = ui
        self.session        = None
        self.audio_in_queue = None
        self.out_queue      = None
        self._loop          = None
        self.voice_enabled  = True
        self.ui.on_voice_toggle = self.set_voice_enabled

    def speak(self, text: str):
        if not self._loop or not self.session:
            return
        asyncio.run_coroutine_threadsafe(
            self.session.send_client_content(
                turns={"parts": [{"text": text}]},
                turn_complete=True
            ),
            self._loop
         )

    async def _send_text_async(self, text: str):
        if not self.session:
            raise RuntimeError("Not connected")
        await self.session.send_client_content(
            turns={"parts": [{"text": text}]},
            turn_complete=True
        )

    def send_text(self, text: str):
        if not self._loop or not self.session:
            self.ui.write_log("SYS: Jarvis not connected yet.")
            return
        if not text.startswith('/'):
            save_command(text)
        self.ui.start_speaking()
        future = asyncio.run_coroutine_threadsafe(self._send_text_async(text), self._loop)
        def _done(fut):
            self.ui.stop_speaking()
            if fut.exception():
                self.ui.write_log(f"SYS: Text send failed: {fut.exception()}")
        future.add_done_callback(_done)

    def set_voice_enabled(self, enabled: bool):
        self.voice_enabled = bool(enabled)
        self.ui.write_log(f"SYS: Voice mode {'enabled' if self.voice_enabled else 'disabled'}")

    def handle_text_input(self, text: str):
        cmd = text.strip()
        if not cmd:
            return

        # Existing commands
        if cmd.startswith('/cmd '):
            task = cmd[5:].strip()
            if task:
                result = cmd_control({'task': task, 'visible': False}, self.ui)
                self.ui.write_log(f"AI: {result}")
            return

        if cmd.startswith('/open '):
            app = cmd[6:].strip()
            if app:
                result = open_app({'app_name': app}, self.ui)
                self.ui.write_log(f"AI: {result}")
            return

        if cmd.startswith('/search '):
            query = cmd[8:].strip()
            if query:
                result = web_search_action({'query': query}, self.ui)
                self.ui.write_log(f"AI: {result}")
            return

        if cmd == '/help':
            help_text = """AI: 📋 **ALL COMMANDS:**

🔹 Basic:
/history - Show recent commands
/favorites - Favorite commands
/export txt|md - Download chat
/cmd <command> - Terminal command
/open <app> - Open application
/search <query> - Web search

🔹 Advanced:
/model - Show AI models
/context - Project contexts
/schedule - Scheduled tasks
/stats - Statistics
/database - Database info

🔹 Special Modes:
/agent on - 🚀 FULL ACCESS MODE (all tasks!)
/agent off - Return to standard mode

🔹 Vision Mode:
/vision on - 👁️ Enable screen view and mouse control
/vision off - Disable screen view and mouse control"""
            self.ui.write_log(help_text)
            return

        if cmd == '/history':
            history = get_history()
            if not history:
                self.ui.write_log('AI: Command history is empty.')
                return
            result = "AI: 📜 **RECENT COMMANDS:**\n"
            for h in history[-10:]:
                result += f"• {h['command']}\n"
            self.ui.write_log(result)
            return

        if cmd == '/favorites':
            result = list_favorites_formatted()
            self.ui.write_log(f'AI: {result}')
            return

        if cmd.startswith('/export '):
            export_type = cmd[8:].strip().lower()
            if export_type == 'txt':
                result = export_chat_txt([])
                self.ui.write_log(f'AI: ✅ Chat saved as TXT:\n{result}')
            elif export_type == 'md':
                result = export_chat_markdown([])
                self.ui.write_log(f'AI: ✅ Chat saved as Markdown:\n{result}')
            else:
                self.ui.write_log('AI: ❌ Invalid format. Use /export txt or /export md.')
            return

        if cmd == '/memory':
            self.ui.write_log('AI: Memory summary (coming soon): this feature will be developed later.')
            return

        # NEW COMMANDS
        if cmd.startswith('/model'):
            try:
                from actions.model_manager import model_action
                action = cmd[7:].strip() if len(cmd) > 6 else ""
                params = {"action": "list"}
                if action:
                    parts = action.split()
                    params["action"] = parts[0] if parts else "list"
                result = model_action(params, self.ui)
                self.ui.write_log(f"AI: {result}")
            except Exception as e:
                self.ui.write_log(f"AI: Model error: {e}")
            return

        if cmd.startswith('/context'):
            try:
                from actions.context_manager import context_action
                action = cmd[9:].strip() if len(cmd) > 8 else ""
                params = {"action": "list"}
                if action:
                    parts = action.split(maxsplit=1)
                    params["action"] = parts[0] if parts else "list"
                result = context_action(params, self.ui)
                self.ui.write_log(f"AI: {result}")
            except Exception as e:
                self.ui.write_log(f"AI: Context error: {e}")
            return

        if cmd.startswith('/schedule'):
            try:
                from actions.task_scheduler import scheduler_action
                action = cmd[10:].strip() if len(cmd) > 9 else ""
                params = {"action": "list"}
                if action:
                    parts = action.split(maxsplit=2)
                    params["action"] = parts[0] if parts else "list"
                result = scheduler_action(params, self.ui)
                self.ui.write_log(f"AI: {result}")
            except Exception as e:
                self.ui.write_log(f"AI: Schedule error: {e}")
            return

        if cmd.startswith('/stats') or cmd.startswith('/statistics'):
            try:
                from actions.statistics import stats_action
                action = cmd[7:].strip() if cmd.startswith('/stats') else cmd[12:].strip()
                params = {"action": "dashboard"}
                if action:
                    params["action"] = action
                result = stats_action(params, self.ui)
                self.ui.write_log(f"AI: {result}")
            except Exception as e:
                self.ui.write_log(f"AI: Stats error: {e}")
            return

        if cmd == '/database' or cmd == '/db':
            try:
                from actions.database import database_action
                result = database_action({"action": "stats"}, self.ui)
                self.ui.write_log(f"AI: {result}")
            except Exception as e:
                self.ui.write_log(f"AI: Database error: {e}")
            return

        # AGENT MODE - Full Access
        if cmd.startswith('/agent'):
            try:
                from actions.agent_mode import agent_mode_action
                action = cmd[7:].strip().lower() if len(cmd) > 6 else ""
                params = {"action": action}
                result = agent_mode_action(params, self.ui)
                self.ui.write_log(f"AI: {result}")
            except Exception as e:
                self.ui.write_log(f"AI: Agent error: {e}")
            return

        # VISION MODE - Screen and Mouse Control
        if cmd.startswith('/vision'):
            try:
                from actions.vision_mode import vision_mode_action
                action = cmd[8:].strip().lower() if len(cmd) > 7 else ""
                params = {"action": action}
                result = vision_mode_action(params, self.ui)
                self.ui.write_log(f"AI: {result}")
            except Exception as e:
                self.ui.write_log(f"AI: Vision error: {e}")
            return

        # AUTO CONTROL - Simple automated actions
        if cmd.startswith('/auto'):
            try:
                from actions.auto_control import auto_control_action
                action = cmd[5:].strip().lower() if len(cmd) > 4 else ""
                mode = "scroll"  # default
                if "click" in action:
                    mode = "click"
                elif "watch" in action:
                    mode = "watch"
                params = {"action": action, "mode": mode}
                result = auto_control_action(params, self.ui)
                self.ui.write_log(f"AI: {result}")
            except Exception as e:
                self.ui.write_log(f"AI: Auto error: {e}")
            return

        # Normal assistant routing
        self.send_text(cmd)

    def _build_config(self) -> types.LiveConnectConfig:
        from datetime import datetime 

        memory  = load_memory()
        mem_str = format_memory_for_prompt(memory)

        sys_prompt = _load_system_prompt()

        now      = datetime.now()
        time_str = now.strftime("%A, %B %d, %Y — %I:%M %p")
        time_ctx = (
            f"[CURRENT DATE & TIME]\n"
            f"Right now it is: {time_str}\n"
            f"Use this to calculate exact times for reminders.\n\n"
        )

        if mem_str:
            sys_prompt = time_ctx + mem_str + "\n\n" + sys_prompt
        else:
            sys_prompt = time_ctx + sys_prompt

        return types.LiveConnectConfig(
            response_modalities=["AUDIO"],
            output_audio_transcription={},
            input_audio_transcription={},
            system_instruction=sys_prompt,
            tools=[{"function_declarations": TOOL_DECLARATIONS}],
            session_resumption=types.SessionResumptionConfig(),
            speech_config=types.SpeechConfig(
                voice_config=types.VoiceConfig(
                    prebuilt_voice_config=types.PrebuiltVoiceConfig(
                        voice_name="Charon" 
                    )
                )
            ),
        )

    async def _execute_tool(self, fc) -> types.FunctionResponse:
        name = fc.name
        args = dict(fc.args or {})

        print(f"[JARVIS] 🔧 TOOL: {name}  ARGS: {args}")

        loop   = asyncio.get_event_loop()
        result = "Done."

        try:
            if name == "open_app":
                r = await loop.run_in_executor(
                    None, lambda: open_app(parameters=args, response=None, player=self.ui)
                )
                result = r or f"Opened {args.get('app_name')} successfully."

            elif name == "weather_report":
                r = await loop.run_in_executor(
                    None, lambda: weather_action(parameters=args, player=self.ui)
                )
                result = r or f"Weather report for {args.get('city')} delivered."

            elif name == "browser_control":
                r = await loop.run_in_executor(
                    None, lambda: browser_control(parameters=args, player=self.ui)
                )
                result = r or "Browser action completed."

            elif name == "file_controller":
                r = await loop.run_in_executor(
                    None, lambda: file_controller(parameters=args, player=self.ui)
                )
                result = r or "File operation completed."

            elif name == "send_message":
                r = await loop.run_in_executor(
                    None, lambda: send_message(
                        parameters=args, response=None,
                        player=self.ui, session_memory=None
                    )
                )
                result = r or f"Message sent to {args.get('receiver')}."

            elif name == "reminder":
                r = await loop.run_in_executor(
                    None, lambda: reminder(parameters=args, response=None, player=self.ui)
                )
                result = r or f"Reminder set for {args.get('date')} at {args.get('time')}."

            elif name == "youtube_video":
                r = await loop.run_in_executor(
                    None, lambda: youtube_video(parameters=args, response=None, player=self.ui)
                )
                result = r or "Done."

            elif name == "screen_process":
                threading.Thread(
                    target=screen_process,
                    kwargs={"parameters": args, "response": None,
                            "player": self.ui, "session_memory": None},
                    daemon=True
                ).start()
                result = (
                    "Vision module activated. "
                    "Stay completely silent — vision module will speak directly."
                )

            elif name == "computer_settings":
                r = await loop.run_in_executor(
                    None, lambda: computer_settings(
                        parameters=args, response=None, player=self.ui
                    )
                )
                result = r or "Done."

            elif name == "cmd_control":
                r = await loop.run_in_executor(
                    None, lambda: cmd_control(parameters=args, player=self.ui)
                )
                result = r or "Command executed."

            elif name == "desktop_control":
                r = await loop.run_in_executor(
                    None, lambda: desktop_control(parameters=args, player=self.ui)
                )
                result = r or "Desktop action completed."

            elif name == "code_helper":
                r = await loop.run_in_executor(
                    None, lambda: code_helper(
                        parameters=args,
                        player=self.ui,
                        speak=self.speak 
                    )
                )
                result = r or "Done."

            elif name == "dev_agent":
                r = await loop.run_in_executor(
                    None, lambda: dev_agent(
                        parameters=args,
                        player=self.ui,
                        speak=self.speak
                    )
                )
                result = r or "Done."

            elif name == "agent_task":
                goal         = args.get("goal", "")
                priority_str = args.get("priority", "normal").lower()

                from agent.task_queue import get_queue, TaskPriority
                priority_map = {
                    "low":    TaskPriority.LOW,
                    "normal": TaskPriority.NORMAL,
                    "high":   TaskPriority.HIGH,
                }
                priority = priority_map.get(priority_str, TaskPriority.NORMAL)

                queue   = get_queue()
                task_id = queue.submit(
                    goal=goal,
                    priority=priority,
                    speak=self.speak,
                )
                result = f"Task started (ID: {task_id}). I'll update you as I make progress, sir."

            elif name == "web_search":
                r = await loop.run_in_executor(
                    None, lambda: web_search_action(parameters=args, player=self.ui)
                    )
                result = r or "Search completed."

            elif name == "computer_control":
                r = await loop.run_in_executor(
                    None, lambda: computer_control(parameters=args, player=self.ui)
                )
                result = r or "Done."

            elif name == "flight_finder":
                r = await loop.run_in_executor(
                    None, lambda: flight_finder(parameters=args, player=self.ui)
                )
                result = r or "Done."

            else:
                result = f"Unknown tool: {name}"
            
        except Exception as e:
            result = f"Tool '{name}' failed: {e}"
            traceback.print_exc()

        print(f"[JARVIS] 📤 {name} → {result[:80]}")

        return types.FunctionResponse(
            id=fc.id,
            name=name,
            response={"result": result}
        )

    async def _send_realtime(self):
        while True:
            msg = await self.out_queue.get()
            await self.session.send_realtime_input(media=msg)

    async def _listen_audio(self):
        print("[JARVIS] 🎤 Mic started")
        stream = await asyncio.to_thread(
            pya.open,
            format=FORMAT,
            channels=CHANNELS,
            rate=SEND_SAMPLE_RATE,
            input=True,
            frames_per_buffer=CHUNK_SIZE,
        )
        try:
            while True:
                if not self.voice_enabled:
                    await asyncio.sleep(0.2)
                    continue
                data = await asyncio.to_thread(
                    stream.read, CHUNK_SIZE, exception_on_overflow=False
                )
                await self.out_queue.put({"data": data, "mime_type": "audio/pcm"})
        except Exception as e:
            print(f"[JARVIS] ❌ Mic error: {e}")
            raise
        finally:
            stream.close()

    async def _receive_audio(self):
        print("[JARVIS] 👂 Recv started")
        out_buf = []
        in_buf  = []

        try:
            while True:
                turn = self.session.receive()
                async for response in turn:

                    if response.data:
                        self.audio_in_queue.put_nowait(response.data)

                    if response.server_content:
                        sc = response.server_content

                        if sc.input_transcription and sc.input_transcription.text:
                            txt = sc.input_transcription.text.strip()
                            if txt:
                                in_buf.append(txt)

                        if sc.output_transcription and sc.output_transcription.text:
                            txt = sc.output_transcription.text.strip()
                            if txt:
                                out_buf.append(txt)

                        if sc.turn_complete:
                            full_in  = ""
                            full_out = ""

                            if in_buf:
                                full_in = " ".join(in_buf).strip()
                                if full_in:
                                    self.ui.write_log(f"You: {full_in}")
                            in_buf = []

                            if out_buf:
                                full_out = " ".join(out_buf).strip()
                                if full_out:
                                    self.ui.write_log(f"Jarvis: {full_out}")
                            out_buf = []

                            if full_in and len(full_in) > 5:
                                threading.Thread(
                                    target=_update_memory_async,
                                    args=(full_in, full_out),
                                    daemon=True
                                ).start()

                    if response.tool_call:
                        fn_responses = []
                        for fc in response.tool_call.function_calls:
                            print(f"[JARVIS] 📞 Tool call: {fc.name}")
                            fr = await self._execute_tool(fc)
                            fn_responses.append(fr)
                        await self.session.send_tool_response(
                            function_responses=fn_responses
                        )

        except Exception as e:
            print(f"[JARVIS] ❌ Recv error: {e}")
            traceback.print_exc()
            raise

    async def _play_audio(self):
        print("[JARVIS] 🔊 Play started")
        stream = await asyncio.to_thread(
            pya.open,
            format=FORMAT,
            channels=CHANNELS,
            rate=RECEIVE_SAMPLE_RATE,
            output=True,
        )
        try:
            while True:
                chunk = await self.audio_in_queue.get()
                await asyncio.to_thread(stream.write, chunk)
        except Exception as e:
            print(f"[JARVIS] ❌ Play error: {e}")
            raise
        finally:
            stream.close()

    async def run(self):
        client = genai.Client(
            api_key=_get_api_key(),
            http_options={"api_version": "v1beta"}
        )

        while True:
            try:
                print("[JARVIS] 🔌 Connecting...")
                config = self._build_config()

                async with (
                    client.aio.live.connect(model=LIVE_MODEL, config=config) as session,
                    asyncio.TaskGroup() as tg,
                ):
                    self.session        = session
                    self._loop          = asyncio.get_event_loop() 
                    self.audio_in_queue = asyncio.Queue()
                    self.out_queue      = asyncio.Queue(maxsize=10)

                    print("[JARVIS] ✅ Connected.")
                    self.ui.write_log("JARVIS online.")

                    tg.create_task(self._send_realtime())
                    tg.create_task(self._listen_audio())
                    tg.create_task(self._receive_audio())
                    tg.create_task(self._play_audio())

            except Exception as e:
                print(f"[JARVIS] ⚠️  Error: {e}")
                traceback.print_exc()

            print("[JARVIS] 🔄 Reconnecting in 3s...")
            await asyncio.sleep(3)

def main():
    ui = JarvisUI("face.png")

    def runner():
        ui.wait_for_api_key()
        
        jarvis = JarvisLive(ui)
        ui.on_text_submit = jarvis.handle_text_input
        try:
            asyncio.run(jarvis.run())
        except KeyboardInterrupt:
            print("\n🔴 Shutting down...")

    threading.Thread(target=runner, daemon=True).start()
    ui.root.mainloop()

if __name__ == "__main__":
    main()
