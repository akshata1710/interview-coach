"""The problem bank, loaded once from problems/*.json."""
from __future__ import annotations

import json
from functools import lru_cache
from typing import Any

from .config import PROBLEMS_DIR


@lru_cache
def all_problems() -> dict[str, dict[str, Any]]:
    out = {}
    for path in sorted(PROBLEMS_DIR.glob("*.json")):
        p = json.loads(path.read_text())
        out[p["slug"]] = p
    return out


def get(slug: str) -> dict[str, Any] | None:
    return all_problems().get(slug)


DIFFICULTY_ORDER = {"Easy": 0, "Medium": 1, "Hard": 2}


def summary(p: dict[str, Any]) -> dict[str, Any]:
    return {k: p[k] for k in ("slug", "title", "difficulty", "topics")}


def public(p: dict[str, Any]) -> dict[str, Any]:
    """What the browser may see: no hidden tests, no expected outputs for them."""
    visible = [
        {"name": t["name"], "args": t["args"], "expected": t["expected"]}
        for t in p["tests"] if not t["hidden"]
    ]
    keep = ("slug", "title", "difficulty", "topics", "statement", "constraints",
            "examples", "function_name", "starter_code")
    return {**{k: p[k] for k in keep}, "visible_tests": visible,
            "hidden_test_count": sum(t["hidden"] for t in p["tests"])}
