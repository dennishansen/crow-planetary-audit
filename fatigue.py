"""
Fatigue System for Crow
Tracks cognitive fatigue and manages model degradation over time.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple


class FatigueManager:
    """
    Manages Crow's fatigue state and model selection.

    As turns progress, the system degrades from high-capability models
    to lower-capability ones, simulating cognitive fatigue.
    At 100% fatigue, auto-sleep is triggered.
    """

    def __init__(
        self,
        workspace: Path = None,
        config_path: str = ".fatigue_config.json",
        state_path: str = ".fatigue.json"
    ):
        self.workspace = workspace or Path(__file__).parent
        self.config_path = self.workspace / config_path
        self.state_path = self.workspace / state_path

        # Load or create config
        self.config = self._load_config()

        # Load or create state
        self.state = self._load_state()

    def _load_config(self) -> Dict:
        """Load fatigue configuration or create defaults."""
        if self.config_path.exists():
            with open(self.config_path) as f:
                return json.load(f)

        # Default configuration
        default_config = {
            "tiers": [
                {"model": "anthropic/claude-opus-4.5", "turns": 3, "context_tokens": 200000, "chars_per_token": 3},
                {"model": "google/gemini-2.5-flash", "turns": 25, "context_tokens": 1000000, "chars_per_token": 4},
                {"model": "google/gemini-2.0-flash-001", "turns": 5, "context_tokens": 1000000, "chars_per_token": 4}
            ],
            "warning_threshold": 0.80,
            "auto_sleep": True,
            "context_utilization": 0.80,
            "chars_per_token": 4
        }

        # Save default config
        with open(self.config_path, "w") as f:
            json.dump(default_config, f, indent=2)

        return default_config

    def _load_state(self) -> Dict:
        """Load fatigue state or create fresh state."""
        if self.state_path.exists():
            with open(self.state_path) as f:
                return json.load(f)

        return self._create_fresh_state()

    def _create_fresh_state(self) -> Dict:
        """Create a fresh fatigue state (called on wake/reset)."""
        return {
            "current_turn": 0,
            "session_start": datetime.now().isoformat(),
            "last_model": self.config["tiers"][0]["model"]
        }

    def _save_state(self):
        """Persist current state to disk."""
        with open(self.state_path, "w") as f:
            json.dump(self.state, f, indent=2)

    @property
    def total_turns(self) -> int:
        """Total turns before exhaustion."""
        return sum(tier["turns"] for tier in self.config["tiers"])

    @property
    def current_turn(self) -> int:
        """Current turn number (1-indexed for display)."""
        return self.state["current_turn"]

    @property
    def fatigue_percentage(self) -> float:
        """Current fatigue as a percentage (0.0 to 1.0)."""
        return min(1.0, self.state["current_turn"] / self.total_turns)

    @property
    def turns_remaining(self) -> int:
        """Number of turns remaining before exhaustion."""
        return max(0, self.total_turns - self.state["current_turn"])

    def _get_current_tier(self) -> Dict:
        """Get the current tier config based on fatigue level."""
        turn = self.state["current_turn"]
        cumulative = 0

        for tier in self.config["tiers"]:
            cumulative += tier["turns"]
            if turn < cumulative:
                return tier

        # If beyond all tiers, return the last tier
        return self.config["tiers"][-1]

    def get_model(self) -> str:
        """Get the current model based on fatigue level."""
        return self._get_current_tier()["model"]

    def get_context_tokens(self) -> int:
        """Get the context window size (in tokens) for the current model."""
        return self._get_current_tier().get("context_tokens", 1000000)

    def get_context_chars(self) -> int:
        """Get the context window size (in chars) for the current model."""
        tier = self._get_current_tier()
        tokens = tier.get("context_tokens", 1000000)
        # Use per-tier chars_per_token if specified, otherwise global default
        chars_per_token = tier.get("chars_per_token", self.config.get("chars_per_token", 4))
        return tokens * chars_per_token

    def get_context_budget(self) -> int:
        """Get the target context budget (chars) accounting for utilization target."""
        utilization = self.config.get("context_utilization", 0.80)
        return int(self.get_context_chars() * utilization)

    def get_tier_info(self) -> Tuple[str, int, int]:
        """Get current tier info: (model_name, tier_turn, tier_total)."""
        turn = self.state["current_turn"]
        cumulative = 0

        for tier in self.config["tiers"]:
            prev_cumulative = cumulative
            cumulative += tier["turns"]
            if turn < cumulative:
                tier_turn = turn - prev_cumulative + 1
                return (tier["model"], tier_turn, tier["turns"])

        # Beyond all tiers
        last_tier = self.config["tiers"][-1]
        return (last_tier["model"], last_tier["turns"], last_tier["turns"])

    def get_status_level(self) -> str:
        """Get status level based on fatigue."""
        pct = self.fatigue_percentage

        if pct >= 1.0:
            return "EXHAUSTED"
        elif pct >= self.config["warning_threshold"]:
            return "DROWSY"
        else:
            return "ALERT"

    def get_status_message(self) -> str:
        """Get human-readable status message."""
        level = self.get_status_level()

        if level == "EXHAUSTED":
            return "EXHAUSTED (auto-sleep triggered)"
        elif level == "DROWSY":
            return "DROWSY (consider sleeping soon)"
        else:
            return "ALERT (normal operations)"

    def get_status(self) -> Dict:
        """Get complete fatigue status for display/injection."""
        model = self.get_model()
        model_short = model.split("/")[-1] if "/" in model else model
        context_tokens = self.get_context_tokens()

        return {
            "turn": self.current_turn,
            "total_turns": self.total_turns,
            "fatigue_percent": int(self.fatigue_percentage * 100),
            "model": model,
            "model_short": model_short,
            "turns_remaining": self.turns_remaining,
            "status_level": self.get_status_level(),
            "status_message": self.get_status_message(),
            "context_tokens": context_tokens,
            "context_k": f"{context_tokens // 1000}k"
        }

    def format_status_block(self) -> str:
        """Format fatigue status as a block for prompt injection."""
        status = self.get_status()

        return f"""[FATIGUE STATUS]
Turn: {status['turn']}/{status['total_turns']}
Fatigue: {status['fatigue_percent']}%
Model: {status['model_short']} ({status['context_k']} context)
Turns remaining: {status['turns_remaining']}
Status: {status['status_message']}"""

    def increment_turn(self) -> bool:
        """
        Increment turn counter and save state.

        Returns:
            True if should auto-sleep (100% fatigue reached)
        """
        self.state["current_turn"] += 1
        self.state["last_model"] = self.get_model()
        self._save_state()

        if self.config["auto_sleep"] and self.fatigue_percentage >= 1.0:
            return True

        return False

    def should_sleep(self) -> bool:
        """Check if auto-sleep should be triggered."""
        return self.config["auto_sleep"] and self.fatigue_percentage >= 1.0

    def should_warn(self) -> bool:
        """Check if drowsiness warning should be shown."""
        return self.fatigue_percentage >= self.config["warning_threshold"]

    def reset(self):
        """Reset fatigue state (called on wake from DREAM)."""
        self.state = self._create_fresh_state()
        self._save_state()

    def __str__(self) -> str:
        """String representation for debugging."""
        return f"FatigueManager(turn={self.current_turn}/{self.total_turns}, fatigue={int(self.fatigue_percentage*100)}%, model={self.get_model()})"
