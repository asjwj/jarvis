"""
Multi-AI Model Manager
Supports: Gemini, Claude, GPT-4, GPT-4o, Ollama (Llama)
"""
import json
import os
import sys
from pathlib import Path
from typing import Optional, Dict, Any

def get_base_dir():
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent.parent

CONFIG_DIR = get_base_dir() / "config"
MODELS_CONFIG = CONFIG_DIR / "models.json"
API_CONFIG = CONFIG_DIR / "api_keys.json"

class ModelManager:
    """Manages multiple AI models and switching between them."""
    
    def __init__(self):
        self.config = self._load_config()
        self.active_model = self.config.get("active_model", "gemini")
        
    def _load_config(self) -> Dict:
        """Load model configuration."""
        try:
            with open(MODELS_CONFIG, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"[ModelManager] Config load error: {e}")
            return {"active_model": "gemini", "models": {}}
    
    def _save_config(self):
        """Save model configuration."""
        try:
            os.makedirs(CONFIG_DIR, exist_ok=True)
            with open(MODELS_CONFIG, "w", encoding="utf-8") as f:
                json.dump(self.config, f, indent=4, ensure_ascii=False)
        except Exception as e:
            print(f"[ModelManager] Config save error: {e}")
    
    def _load_api_keys(self) -> Dict:
        """Load API keys from config."""
        try:
            with open(API_CONFIG, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return {}
    
    def get_active_model(self) -> str:
        """Get currently active model ID."""
        return self.active_model
    
    def set_active_model(self, model_id: str) -> Dict[str, Any]:
        """Switch to a different AI model."""
        models = self.config.get("models", {})
        
        if model_id not in models:
            return {"success": False, "error": f"Model '{model_id}' not found"}
        
        model_info = models[model_id]
        
        # Check if model is enabled
        if not model_info.get("enabled", False):
            return {"success": False, "error": f"Model '{model_id}' is disabled"}
        
        # Check API key for non-local models
        if model_info.get("provider") != "ollama":
            api_key_config = model_info.get("api_key_config")
            env_key = os.environ.get(model_info.get("api_key_env", ""))
            
            if not env_key:
                api_keys = self._load_api_keys()
                if not api_keys.get(api_key_config):
                    return {
                        "success": False, 
                        "error": f"API key not configured for {model_info.get('name')}"
                    }
        
        self.active_model = model_id
        self._save_config()
        
        return {
            "success": True,
            "model_id": model_id,
            "model_name": model_info.get("name"),
            "features": model_info.get("features", [])
        }
    
    def get_available_models(self) -> list:
        """Get list of all configured models with their status."""
        models = self.config.get("models", {})
        result = []
        
        for model_id, info in models.items():
            result.append({
                "id": model_id,
                "name": info.get("name", model_id),
                "provider": info.get("provider", "unknown"),
                "enabled": info.get("enabled", False),
                "active": model_id == self.active_model,
                "features": info.get("features", []),
                "model_id": info.get("model_id", "")
            })
        
        return result
    
    def enable_model(self, model_id: str, enable: bool = True) -> bool:
        """Enable or disable a model."""
        models = self.config.get("models", {})
        
        if model_id not in models:
            return False
        
        models[model_id]["enabled"] = enable
        self._save_config()
        return True
    
    def configure_api_key(self, model_id: str, api_key: str) -> Dict[str, Any]:
        """Configure API key for a model."""
        models = self.config.get("models", {})
        
        if model_id not in models:
            return {"success": False, "error": "Model not found"}
        
        model_info = models[model_id]
        api_key_config = model_info.get("api_key_config")
        
        if not api_key_config:
            return {"success": False, "error": "API key not applicable for this model"}
        
        # Update API keys config
        api_keys = self._load_api_keys()
        api_keys[api_key_config] = api_key
        
        try:
            os.makedirs(CONFIG_DIR, exist_ok=True)
            with open(API_CONFIG, "w", encoding="utf-8") as f:
                json.dump(api_keys, f, indent=4)
            
            # Enable the model
            models[model_id]["enabled"] = True
            self._save_config()
            
            return {"success": True, "message": f"API key configured for {model_info.get('name')}"}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def get_model_info(self, model_id: str) -> Optional[Dict]:
        """Get detailed information about a specific model."""
        models = self.config.get("models", {})
        return models.get(model_id)
    
    def test_model_connection(self, model_id: str) -> Dict[str, Any]:
        """Test connection to a specific model."""
        model_info = self.get_model_info(model_id)
        
        if not model_info:
            return {"success": False, "error": "Model not found"}
        
        provider = model_info.get("provider")
        
        try:
            if provider == "google":
                api_key = os.environ.get("GEMINI_API_KEY")
                if not api_key:
                    api_keys = self._load_api_keys()
                    api_key = api_keys.get("gemini_api_key")
                
                if not api_key:
                    return {"success": False, "error": "API key not configured"}
                
                # Test with a simple request
                from google import genai
                client = genai.Client(api_key=api_key)
                models_list = client.models.list()
                return {"success": True, "models": [m.name for m in models_list]}
            
            elif provider == "ollama":
                import requests
                response = requests.get(f"{model_info.get('base_url', 'http://localhost:11434')}/api/tags")
                if response.status_code == 200:
                    models = response.json().get("models", [])
                    return {"success": True, "models": [m.get("name") for m in models]}
                return {"success": False, "error": f"Ollama returned {response.status_code}"}
            
            elif provider == "anthropic":
                api_key = os.environ.get("ANTHROPIC_API_KEY")
                if not api_key:
                    api_keys = self._load_api_keys()
                    api_key = api_keys.get("claude_api_key")
                
                if not api_key:
                    return {"success": False, "error": "API key not configured"}
                
                import anthropic
                client = anthropic.Anthropic(api_key=api_key)
                return {"success": True, "message": "Anthropic connection successful"}
            
            elif provider == "openai":
                api_key = os.environ.get("OPENAI_API_KEY")
                if not api_key:
                    api_keys = self._load_api_keys()
                    api_key = api_keys.get("openai_api_key")
                
                if not api_key:
                    return {"success": False, "error": "API key not configured"}
                
                import openai
                client = openai.OpenAI(api_key=api_key)
                models = client.models.list()
                return {"success": True, "models": [m.id for m in models.data]}
            
            else:
                return {"success": False, "error": f"Unknown provider: {provider}"}
        
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def format_models_list(self) -> str:
        """Format available models as a readable string."""
        models = self.get_available_models()
        active = self.get_active_model()
        
        result = "📊 **YAPAY ZEKA MODELLERİ:**\n\n"
        
        for m in models:
            status = "✅" if m["enabled"] else "❌"
            active_mark = " ◄" if m["id"] == active else ""
            
            features = ", ".join(m["features"][:3]) if m["features"] else "Temel"
            
            result += f"{status} **{m['name']}** ({m['id']}){active_mark}\n"
            result += f"   ├─ Sağlayıcı: {m['provider']}\n"
            result += f"   └─ Özellikler: {features}\n\n"
        
        result += f"\n🔄 Aktif model: **{self.get_model_info(active).get('name', active)}**"
        
        return result


# Global instance
_model_manager = None

def get_model_manager() -> ModelManager:
    global _model_manager
    if _model_manager is None:
        _model_manager = ModelManager()
    return _model_manager


def model_action(parameters: dict, player=None) -> str:
    """Handle model management actions."""
    action = parameters.get("action", "list")
    manager = get_model_manager()
    
    if action == "list":
        return manager.format_models_list()
    
    elif action == "switch":
        model_id = parameters.get("model_id", "")
        if not model_id:
            return "❌ Model ID gerekli: /model switch gemini"
        
        result = manager.set_active_model(model_id)
        if result.get("success"):
            return f"✅ Model değiştirildi: {result.get('model_name')}"
        return f"❌ {result.get('error')}"
    
    elif action == "info":
        model_id = parameters.get("model_id", "") or manager.get_active_model()
        info = manager.get_model_info(model_id)
        if info:
            return f"📋 **{info.get('name')}**\n" \
                   f"Model ID: {info.get('model_id')}\n" \
                   f"Özellikler: {', '.join(info.get('features', []))}"
        return "❌ Model bulunamadı"
    
    elif action == "test":
        model_id = parameters.get("model_id", "")
        if not model_id:
            return "❌ Model ID gerekli"
        
        result = manager.test_model_connection(model_id)
        if result.get("success"):
            return f"✅ Bağlantı başarılı!"
        return f"❌ Bağlantı hatası: {result.get('error')}"
    
    elif action == "configure":
        model_id = parameters.get("model_id", "")
        api_key = parameters.get("api_key", "")
        
        if not model_id or not api_key:
            return "❌ Model ID ve API key gerekli"
        
        result = manager.configure_api_key(model_id, api_key)
        if result.get("success"):
            return f"✅ {result.get('message')}"
        return f"❌ {result.get('error')}"
    
    return f"❌ Bilinmeyen işlem: {action}"
