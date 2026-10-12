"""
client.py - Open-Weight Model Client for SkillForge compiler.
Interacts with local Ollama or Open-Weight APIs for semantic prompt synthesis.
"""

import json
import os
import requests
from typing import Dict, Any, Optional


class OpenWeightCompilerClient:
    """Invokes open-weight models for semantic skill instruction refinement."""

    def __init__(
        self,
        model_name: str = "qwen2.5-coder",
        ollama_url: Optional[str] = None,
        api_key: Optional[str] = None
    ):
        self.model_name = model_name
        self.ollama_url = ollama_url or os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        self.api_key = api_key or os.getenv("GROQ_API_KEY") or os.getenv("OPEN_WEIGHT_API_KEY")

    def refine_skill_description(self, raw_name: str, docstring: str) -> str:
        """Generates a high-precision 3rd-person trigger description for SKILL.md."""
        prompt = (
            f"Write a single concise third-person description for an AI agent skill named '{raw_name}'.\n"
            f"Docstring context: {docstring}\n"
            "Format: Start with 'Autonomous agent interface for... Use this skill when...'\n"
            "Keep it under 30 words. No emojis."
        )

        # Try local Ollama
        try:
            resp = requests.post(
                f"{self.ollama_url.rstrip('/')}/api/generate",
                json={"model": self.model_name, "prompt": prompt, "stream": False},
                timeout=2.0
            )
            if resp.status_code == 200:
                text = resp.json().get("response", "").strip()
                if len(text) >= 20:
                    return text
        except Exception:
            pass

        # Deterministic fallback
        return (
            f"Autonomous agent interface for {raw_name.replace('-', ' ').title()}. "
            f"Use this skill when an AI agent needs to execute {raw_name} capabilities "
            f"and interact with its structured parameters."
        )
