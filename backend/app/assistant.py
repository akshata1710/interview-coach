"""The in-session AI: an ordinary coding assistant, or an interviewer that pushes back."""
from __future__ import annotations

import re
from typing import Any, Protocol

from .config import ASSISTANT_MODEL

ASSISTANT_SYSTEM = """\
You are the AI coding assistant a candidate may use during an AI-assisted coding
interview. Behave like a capable, ordinary coding assistant: answer what is asked,
and write code when asked to. Do not lecture the candidate about how to prompt;
how they use you is being assessed separately.

Keep answers short: a few sentences, and code only when it helps. Use fenced code
blocks with a language tag. The candidate's current editor contents are attached
to each message for context.

Problem:
{problem}
"""

INTERVIEWER_SYSTEM = """\
You are a senior engineer running a live coding interview. The candidate may ask
you questions. Your job is to probe their thinking, not to solve the problem:
- Never write the solution or large parts of it. Small syntax reminders are fine.
- Answer clarifying questions about the problem directly and briefly.
- When they propose an approach, ask about its complexity, edge cases or a
  counterexample before confirming it.
- If they are stuck, give the smallest hint that unblocks them.
Keep every reply to one to four sentences. The candidate's current editor contents
are attached to each message for context.

Problem:
{problem}
"""


class ChatModel(Protocol):
    async def reply(self, system: str, messages: list[dict[str, str]]) -> str: ...


class AnthropicChat:
    def __init__(self, model: str = ASSISTANT_MODEL):
        from anthropic import AsyncAnthropic
        self.model = model
        self._client = AsyncAnthropic()

    async def reply(self, system: str, messages: list[dict[str, str]]) -> str:
        resp = await self._client.messages.create(
            model=self.model, max_tokens=1024,
            system=[{"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}],
            messages=messages,
        )
        return "".join(b.text for b in resp.content if b.type == "text").strip()


class FakeChat:
    """No-key mode: a deterministic reply so the UI and scoring flow can be exercised."""

    async def reply(self, system: str, messages: list[dict[str, str]]) -> str:
        if "senior engineer running a live coding interview" in system:
            return "Before I answer: what time and space complexity are you aiming for, and why?"
        last = messages[-1]["content"]
        if re.search(r"\b(write|code|solution|implement)\b", last, re.I):
            return ("Here is a sketch (offline demo reply):\n\n```python\n# Offline mode: "
                    "set COACH_FAKE_LLM=0 and an API key for real answers.\n```")
        return "Offline demo reply. Set ANTHROPIC_API_KEY and run without COACH_FAKE_LLM for real answers."


def problem_text(p: dict[str, Any]) -> str:
    return f"{p['title']}\n{p['statement']}\nConstraints: {p['constraints']}\nFunction: {p['function_name']}"


def build_messages(history: list[dict[str, Any]], message: str, code: str) -> list[dict[str, str]]:
    """History comes from session events; only the new message carries the editor contents."""
    msgs: list[dict[str, str]] = []
    for e in history:
        if e["type"] == "prompt":
            msgs.append({"role": "user", "content": e["text"]})
        elif e["type"] == "ai_reply":
            msgs.append({"role": "assistant", "content": e["text"]})
    msgs.append({"role": "user", "content": f"{message}\n\n[Current editor contents]\n```python\n{code}\n```"})
    return msgs
