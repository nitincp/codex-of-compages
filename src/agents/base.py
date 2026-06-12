"""
BaseAgent — shared foundation for all Faber agents.

Provides:
  TokenUsage / SessionUsage — usage accounting per call and per session
  BaseAgent — abstract base with build_prompt() and _log_usage()
"""

from __future__ import annotations

import os
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Generic, TypeVar

import anthropic

T = TypeVar("T")


@dataclass
class TokenUsage:
    input_tokens: int = 0
    output_tokens: int = 0
    cache_creation_input_tokens: int = 0
    cache_read_input_tokens: int = 0

    @classmethod
    def from_response(cls, usage: anthropic.types.Usage) -> "TokenUsage":
        return cls(
            input_tokens=usage.input_tokens,
            output_tokens=usage.output_tokens,
            cache_creation_input_tokens=getattr(usage, "cache_creation_input_tokens", 0) or 0,
            cache_read_input_tokens=getattr(usage, "cache_read_input_tokens", 0) or 0,
        )

    @property
    def total_tokens(self) -> int:
        return self.input_tokens + self.output_tokens


@dataclass
class SessionUsage:
    calls: int = 0
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    total_cache_creation_tokens: int = 0
    total_cache_read_tokens: int = 0

    def add(self, usage: TokenUsage) -> None:
        self.calls += 1
        self.total_input_tokens += usage.input_tokens
        self.total_output_tokens += usage.output_tokens
        self.total_cache_creation_tokens += usage.cache_creation_input_tokens
        self.total_cache_read_tokens += usage.cache_read_input_tokens

    @property
    def total_tokens(self) -> int:
        return self.total_input_tokens + self.total_output_tokens


class BaseAgent(ABC, Generic[T]):
    """Abstract base for all Faber agents. T is the return type of run()."""

    def __init__(self) -> None:
        self._client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
        self._model = os.getenv("MODEL_NAME", "claude-sonnet-4-6")
        self.session_usage = SessionUsage()

    def build_prompt(self, layers: list) -> str:
        """Assemble a composed prompt from a list of framework layer instances."""
        from src.frameworks.composed import ComposedPrompt

        return ComposedPrompt(layers=layers).build()

    def _log_usage(self, usage: anthropic.types.Usage) -> TokenUsage:
        token_usage = TokenUsage.from_response(usage)
        self.session_usage.add(token_usage)
        return token_usage

    @abstractmethod
    def run(self, *args: Any, **kwargs: Any) -> T:
        """Execute the agent's primary task."""
