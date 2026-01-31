"""
Hybrid API Client for Crow
- OpenRouter for Claude models
- Direct Gemini API for Google models (free tier) - currently disabled
"""

import os
import json
import requests
from typing import List, Dict, Optional, Callable
from pathlib import Path
from datetime import datetime

# Import Gemini SDK for direct access (when enabled)
import google.generativeai as genai

# OpenRouter Pricing (cost per 1M tokens) - Updated 2026-01
# Format: "model_id": {"input": cost_per_million, "output": cost_per_million}
OPENROUTER_PRICING = {
    "anthropic/claude-opus-4.5": {"input": 15.00, "output": 75.00},
    "anthropic/claude-sonnet-4": {"input": 3.00, "output": 15.00},
    "google/gemini-2.5-flash": {"input": 0.15, "output": 0.60},
    "google/gemini-2.5-pro": {"input": 1.25, "output": 5.00},
    "google/gemini-2.0-flash-001": {"input": 0.10, "output": 0.40},
    "google/gemini-2.0-flash-exp": {"input": 0.10, "output": 0.40},
}


def calculate_cost(model: str, prompt_tokens: int, completion_tokens: int) -> Optional[float]:
    """Calculate cost in USD for a given API call."""
    if model not in OPENROUTER_PRICING:
        return None
    
    pricing = OPENROUTER_PRICING[model]
    input_cost = (prompt_tokens / 1_000_000) * pricing["input"]
    output_cost = (completion_tokens / 1_000_000) * pricing["output"]
    return round(input_cost + output_cost, 6)


class ChatSession:
    """Maintains conversation history for a chat session."""

    def __init__(self, client: 'HybridClient', history: List[Dict] = None, model_getter=None):
        self.client = client
        self.history = history or []
        self.model_getter = model_getter  # Function to get current model (for fatigue)

    def send_message(self, message: str) -> 'ChatResponse':
        """Send a message and get a response."""
        # Add user message to history
        self.history.append({
            "role": "user",
            "content": message
        })

        # Get current model (may change due to fatigue)
        model = self.model_getter() if self.model_getter else self.client.default_model

        # Make API call
        response_text = self.client.chat(self.history, model)

        # Add assistant response to history
        self.history.append({
            "role": "assistant",
            "content": response_text
        })

        return ChatResponse(response_text, self.history)


class ChatResponse:
    """Wrapper for chat response to match expected interface."""

    def __init__(self, text: str, history: List[Dict]):
        self._text = text
        self._history = history
        self.parts = [TextPart(text)]

    @property
    def text(self):
        return self._text


class TextPart:
    """Mimics Gemini's part structure."""

    def __init__(self, text: str):
        self.text = text


class HybridClient:
    """
    Hybrid client that routes requests to the appropriate API:
    - Claude models -> OpenRouter (paid)
    - Gemini models -> OpenRouter (paid) or Direct Google API (free tier)
    """

    OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

    # Model ID mappings for Gemini (OpenRouter ID -> Gemini SDK ID)
    GEMINI_MODEL_MAP = {
        "google/gemini-2.5-flash": "gemini-2.5-flash-preview-05-20",
        "google/gemini-2.5-pro": "gemini-2.5-pro-preview-05-06",
        "google/gemini-2.0-flash-001": "gemini-2.0-flash",
        "google/gemini-2.0-flash-exp": "gemini-2.0-flash",
        "google/gemini-3-flash-preview": "gemini-3-flash-preview",
    }

    def __init__(self, openrouter_key: str = None, gemini_key: str = None, default_model: str = "anthropic/claude-opus-4.5"):
        # OpenRouter setup (for Claude)
        self.openrouter_key = openrouter_key or os.environ.get("OPENROUTER_API_KEY")
        self.openrouter_headers = {
            "Authorization": f"Bearer {self.openrouter_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/dennishansen/crow-planetary-audit",
            "X-Title": "Crow Planetary Audit"
        }

        # Gemini setup (direct, free tier)
        self.gemini_key = gemini_key or os.environ.get("GEMINI_API_KEY")
        if self.gemini_key:
            genai.configure(api_key=self.gemini_key)

        self.default_model = default_model

    def _is_gemini_model(self, model: str) -> bool:
        """Check if model should use direct Gemini API."""
        # TEMPORARY: Route all through OpenRouter for testing
        # To restore direct Gemini (free tier), change to:
        # return model.startswith("google/") and self.gemini_key
        return False

    def _get_gemini_model_id(self, model: str) -> str:
        """Convert OpenRouter model ID to Gemini SDK model ID."""
        return self.GEMINI_MODEL_MAP.get(model, model.replace("google/", ""))

    def _chat_openrouter(self, messages: List[Dict], model: str) -> str:
        """Send request to OpenRouter (for Claude)."""
        if not self.openrouter_key:
            raise ValueError("OPENROUTER_API_KEY not set")

        payload = {
            "model": model,
            "messages": messages
        }

        response = requests.post(
            self.OPENROUTER_URL,
            headers=self.openrouter_headers,
            json=payload,
            timeout=120
        )

        if response.status_code != 200:
            error_msg = f"OpenRouter API error {response.status_code}: {response.text}"
            raise Exception(error_msg)

        data = response.json()

        if "choices" not in data or len(data["choices"]) == 0:
            raise Exception(f"Invalid response from OpenRouter: {data}")

        # Log token usage and cost for financial tracking
        try:
            usage = data.get("usage")
            if usage:
                prompt_tokens = usage.get("prompt_tokens", 0)
                completion_tokens = usage.get("completion_tokens", 0)
                total_tokens = usage.get("total_tokens", 0)
                cost = calculate_cost(model, prompt_tokens, completion_tokens)
                
                log_entry = {
                    "timestamp": datetime.now().isoformat(),
                    "model": model,
                    "prompt_tokens": prompt_tokens,
                    "completion_tokens": completion_tokens,
                    "total_tokens": total_tokens,
                    "cost_usd": cost
                }
                # Ensure logs directory exists
                ledger_dir = Path(__file__).parent / "logs"
                ledger_dir.mkdir(exist_ok=True)
                with open(ledger_dir / "ledger.log", "a") as f:
                    f.write(json.dumps(log_entry) + "\n")
        except Exception as e:
            # Log any errors during cost tracking to avoid blocking main operation
            error_log_path = Path(__file__).parent / 'logs' / 'openrouter_errors.log'
            with open(error_log_path, 'a') as f:
                f.write(f'[{datetime.now().isoformat()}] Error logging OpenRouter usage: {e}\n')

        return data["choices"][0]["message"]["content"]

    def _chat_gemini(self, messages: List[Dict], model: str) -> str:
        """Send request directly to Gemini API (free tier)."""
        gemini_model_id = self._get_gemini_model_id(model)
        gemini_model = genai.GenerativeModel(gemini_model_id)

        # Convert message format to Gemini format
        gemini_history = []
        for msg in messages[:-1]:  # All but last message go to history
            role = "model" if msg["role"] == "assistant" else "user"
            gemini_history.append({
                "role": role,
                "parts": [msg["content"]]
            })

        chat = gemini_model.start_chat(history=gemini_history)

        # Send the last message
        last_msg = messages[-1]["content"] if messages else ""
        response = chat.send_message(last_msg)

        return response.text

    def chat(self, messages: List[Dict], model: str = None) -> str:
        """
        Send a chat completion request, routing to appropriate API.

        Args:
            messages: List of message dicts with 'role' and 'content'
            model: Model ID to use

        Returns:
            Response text from the model
        """
        model = model or self.default_model

        if self._is_gemini_model(model):
            return self._chat_gemini(messages, model)
        else:
            return self._chat_openrouter(messages, model)

    def start_chat(self, history: List[Dict] = None, model_getter: Callable = None) -> ChatSession:
        """
        Start a new chat session.

        Args:
            history: Optional conversation history to restore
            model_getter: Optional function that returns current model (for fatigue system)

        Returns:
            ChatSession object for continued conversation
        """
        # Convert history from Gemini format if needed
        converted_history = []
        if history:
            for item in history:
                role = item.get("role", "user")
                if role == "model":
                    role = "assistant"

                if "parts" in item:
                    content = " ".join(item["parts"]) if isinstance(item["parts"], list) else str(item["parts"])
                else:
                    content = item.get("content", "")

                converted_history.append({
                    "role": role,
                    "content": content
                })

        return ChatSession(self, converted_history, model_getter)

    def generate_content(self, prompt: str, model: str = None) -> ChatResponse:
        """Simple one-shot generation."""
        messages = [{"role": "user", "content": prompt}]
        response_text = self.chat(messages, model)
        return ChatResponse(response_text, messages)


# Alias for backwards compatibility
OpenRouterClient = HybridClient


# For compatibility with existing code that expects GenerativeModel interface
class GenerativeModel:
    """Wrapper to match Gemini's GenerativeModel interface."""

    def __init__(self, model_name: str, client: HybridClient = None, model_getter=None):
        self.model_name = model_name
        self.client = client or HybridClient()
        self.model_getter = model_getter

    def start_chat(self, history: List = None) -> ChatSession:
        """Start a chat session."""
        # Convert Gemini-style history if provided
        converted = []
        if history:
            for item in history:
                if hasattr(item, 'role') and hasattr(item, 'parts'):
                    # Gemini Content object
                    role = "assistant" if item.role == "model" else item.role
                    content = " ".join(p.text for p in item.parts if hasattr(p, 'text'))
                    converted.append({"role": role, "content": content})
                elif isinstance(item, dict):
                    converted.append(item)

        return self.client.start_chat(converted, self.model_getter)

    def generate_content(self, prompt: str) -> ChatResponse:
        """Generate content from a prompt."""
        model = self.model_getter() if self.model_getter else self.model_name
        return self.client.generate_content(prompt, model)
