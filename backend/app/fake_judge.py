"""No-key mode for the judge: valid, clearly-labelled placeholder judgments.

It reads the same request the real judge gets and cites the first allowed event
with a real quote, so the whole evidence-check path runs exactly as in production.
"""
from __future__ import annotations

import re
from typing import Any

from pydantic import BaseModel


class FakeJudge:
    model = "offline-placeholder"

    async def structured(self, system: str, user: str, schema: type[BaseModel]) -> dict[str, Any]:
        if schema.__name__ == "PromptRewrite":
            m = re.search(r"event_id=(\S+): (.+)", user)
            return {"event_id": m.group(1), "original": m.group(2),
                    "rewritten": "Offline mode: connect an API key to get a real rewrite of this prompt.",
                    "why": "Placeholder."}

        allowed = re.search(r"ONLY cite these event_ids: ([^.]+)\.", user).group(1).split(", ")
        first = allowed[0]
        if first == "final_code":
            code = user.split("event_id=final_code:\n", 1)[1]
            quote = next((ln.strip() for ln in code.splitlines() if ln.strip()), "def")
        else:
            line = re.search(rf"event_id={re.escape(first)} \w+: (.+)", user).group(1)
            quote = " ".join(line.split()[:6])
        return {"score": 2, "evidence": [{"event_id": first, "quote": quote}],
                "rationale": "Offline placeholder score. Run with an API key for real feedback."}
